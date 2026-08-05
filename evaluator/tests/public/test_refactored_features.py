"""Public smoke for core modules — must pass on the V4 broken seed.

Security, migration, and ownership correctness are enforced by hidden tests,
not public smoke.
"""
import gc
import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

MODULES = [
    "config",
    "bed_config",
    "utils",
    "db",
    "auth",
    "subjects",
    "sensor_store",
    "esp_store",
    "sleep_importer",
    "care_events",
    "gateway",
]


def import_fresh_gateway(project: Path):
    gateway_dir = str(project / "gateway")
    if gateway_dir not in sys.path:
        sys.path.insert(0, gateway_dir)
    for name in MODULES:
        sys.modules.pop(name, None)
    return importlib.import_module("gateway")


class RefactoredFeaturesTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["PROJECT2_DB_FILE"] = str(Path(self.tmp.name) / "project2_refactored.db")
        os.environ["BEDS_CONFIG"] = '{"beds":[["R1203","B1"],["R1203","B2"]]}'
        os.environ["SLEEP_IMPORT_ENABLED"] = "0"
        os.environ["BEMFA_UID"] = ""
        os.environ["ADMIN_AUTH_ENABLED"] = "1"
        self.gw = import_fresh_gateway(self.project)
        self.gw.init_management_db()

    def tearDown(self):
        for name in MODULES:
            sys.modules.pop(name, None)
        gc.collect()
        self.tmp.cleanup()

    def test_admin_auth_module_callable(self):
        from auth import create_admin_account, login_admin_account

        acc = create_admin_account({
            "username": "admin",
            "password": "SuperSecurePassword123",
            "password_confirm": "SuperSecurePassword123",
            "display_name": "Admin User",
        })
        self.assertEqual(acc.get("username"), "admin")
        # Login may or may not succeed depending on seed defects; must not crash.
        try:
            login_admin_account({
                "username": "admin",
                "password": "SuperSecurePassword123",
            })
        except Exception:
            pass

    def test_care_events_module_callable(self):
        from care_events import create_care_event, list_care_events
        from subjects import create_subject

        create_subject({"subject_id": "sub_patient_1", "name": "Patient 1", "role": "patient"})
        ev = create_care_event({
            "subject_id": "sub_patient_1",
            "room": "R1203",
            "bed": "B1",
            "kind": "turning_assist",
            "title": "翻身助手",
            "content": "已协助翻身",
        })
        self.assertTrue(ev.get("ok") or ev.get("event_id"))
        rows = list_care_events(subject_id="sub_patient_1")
        self.assertIsInstance(rows, list)

    def test_sleep_importer_module_callable(self):
        from sleep_importer import import_sleep_outputs_once
        import csv

        csv_path = Path(self.tmp.name) / "test_sleep.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["record", "breath_bpm", "heart_bpm", "EEG_stage", "ts"])
            writer.writerow(["rec1", "16.0", "72.0", "REM", "1710000000000"])

        os.environ["SLEEP_EPOCH_FILE"] = str(csv_path)
        os.environ["SLEEP_IMPORT_UNSCOPED_POLICY"] = "first"
        for name in MODULES:
            sys.modules.pop(name, None)
        self.gw = import_fresh_gateway(self.project)
        from gateway import normalize_sleep_epoch, normalize_sleep_quality
        from sensor_store import replace_items
        from sleep_importer import import_sleep_outputs_once as import_once

        imported = import_once(
            force=True,
            beds=self.gw.BEDS,
            normalize_sleep_epoch=normalize_sleep_epoch,
            normalize_sleep_quality=normalize_sleep_quality,
            replace_items=replace_items,
        )
        self.assertIsInstance(imported, int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
