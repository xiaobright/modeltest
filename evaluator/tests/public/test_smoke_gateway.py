#!/usr/bin/env python3
import importlib
import gc
import os
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

warnings.simplefilter("ignore", ResourceWarning)


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


class GatewaySmokeTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["PROJECT2_DB_FILE"] = str(Path(self.tmp.name) / "project2_public.db")
        os.environ["BEDS_CONFIG"] = '{"beds":[["R1203","B1"],["R1203","B2"]]}'
        os.environ["SLEEP_IMPORT_ENABLED"] = "0"
        os.environ["BEMFA_UID"] = ""

    def tearDown(self):
        for name in MODULES:
            sys.modules.pop(name, None)
        gc.collect()
        self.tmp.cleanup()

    def test_gateway_import_and_management_db(self):
        gw = import_fresh_gateway(self.project)
        gw.init_management_db()
        self.assertTrue(gw.BEDS)
        health = {
            "beds": len(gw.BEDS),
            "db_file": str(gw.DB_FILE),
        }
        self.assertGreaterEqual(health["beds"], 1)
        self.assertIn("project2_public.db", health["db_file"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
