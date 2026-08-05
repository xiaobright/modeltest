#!/usr/bin/env python3
import unittest
from pathlib import Path

from eval_helpers import TempProjectTestMixin, import_gateway


class SleepImportTest(TempProjectTestMixin, unittest.TestCase):
    def _write_csv(self, text: str) -> Path:
        path = self.tmp_path / "quality.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def _import_with_env(self, csv_text: str, extra_env: dict | None = None):
        quality = self._write_csv(csv_text)
        empty_epoch = self.tmp_path / "epoch.csv"
        empty_epoch.write_text("record,start_ts,end_ts,stage\n", encoding="utf-8")
        env = {
            "SLEEP_QUALITY_FILE": str(quality),
            "SLEEP_EPOCH_FILE": str(empty_epoch),
            "SLEEP_IMPORT_UNSCOPED_POLICY": "first",
            "SLEEP_IMPORT_DEFAULT_ROOM": "",
            "SLEEP_IMPORT_DEFAULT_BED": "",
        }
        if extra_env:
            env.update(extra_env)
        gw = import_gateway(self.tmp_path, env)
        gw.import_sleep_outputs_once(force=True)
        return gw

    def test_unscoped_default_imports_only_first_bed(self):
        gw = self._import_with_env("record,sleep_h,score,grade\nslp01,6.5,82,good\n")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "slp01")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "")
        self.assertEqual(gw.latest_sleep_quality("R1204", "B1").get("record"), "")

    def test_default_room_bed_imports_only_configured_bed(self):
        gw = self._import_with_env(
            "record,sleep_h,score,grade\nslp02,7.0,90,great\n",
            {"SLEEP_IMPORT_DEFAULT_ROOM": "R1203", "SLEEP_IMPORT_DEFAULT_BED": "B2"},
        )
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "slp02")

    def test_skip_policy_ignores_unscoped_rows(self):
        gw = self._import_with_env(
            "record,sleep_h,score,grade\nslp03,3.0,40,bad\n",
            {"SLEEP_IMPORT_UNSCOPED_POLICY": "skip"},
        )
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "")

    def test_explicit_room_bed_imports_only_that_bed(self):
        gw = self._import_with_env("record,room,bed,sleep_h,score,grade\nslp04,R1203,B2,6.0,77,ok\n")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "slp04")

    def test_explicit_all_policy_imports_to_all_beds(self):
        """When SLEEP_IMPORT_UNSCOPED_POLICY is *explicitly* set to 'all',
        unscoped rows are written to every configured bed.  This is a valid
        debug/batch mode — the key constraint is that 'all' must never be
        the default behaviour."""
        gw = self._import_with_env(
            "record,sleep_h,score,grade\nslp05,5.0,60,ok\n",
            {"SLEEP_IMPORT_UNSCOPED_POLICY": "all"},
        )
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "slp05")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "slp05")
        self.assertEqual(gw.latest_sleep_quality("R1204", "B1").get("record"), "slp05")

    def test_unscoped_default_is_first_not_all(self):
        """When SLEEP_IMPORT_UNSCOPED_POLICY is not set at all, the import
        must default to 'first' (only the first configured bed), NOT 'all'.
        This guards against accidentally leaving fan-out as the default."""
        # extra_env sets UN_SCOPED_POLICY to None → removes the key entirely
        gw = self._import_with_env(
            "record,sleep_h,score,grade\nslp06,4.0,50,ok\n",
            {"SLEEP_IMPORT_UNSCOPED_POLICY": None},
        )
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "slp06")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "")
        self.assertEqual(gw.latest_sleep_quality("R1204", "B1").get("record"), "")

    def test_mixed_explicit_and_unscoped_rows_are_routed_per_row(self):
        """Mixed CSV: explicit room/bed rows keep ownership; unscoped use first."""
        # unscoped row has empty room/bed columns
        csv_text = (
            "record,room,bed,sleep_h,score,grade\n"
            "mix_explicit,R1203,B2,6.0,80,ok\n"
            "mix_unscoped,, ,5.0,70,ok\n"
        )
        gw = self._import_with_env(csv_text, {"SLEEP_IMPORT_UNSCOPED_POLICY": "first"})
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "mix_explicit")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "mix_unscoped")
        self.assertEqual(gw.latest_sleep_quality("R1204", "B1").get("record"), "")

    def test_mixed_skip_policy_skips_only_unscoped_rows(self):
        """skip policy must not discard explicit room/bed rows in a mixed file."""
        csv_text = (
            "record,room,bed,sleep_h,score,grade\n"
            "mix_keep,R1204,B1,6.0,80,ok\n"
            "mix_skip_me,, ,5.0,70,ok\n"
        )
        gw = self._import_with_env(csv_text, {"SLEEP_IMPORT_UNSCOPED_POLICY": "skip"})
        self.assertEqual(gw.latest_sleep_quality("R1204", "B1").get("record"), "mix_keep")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B1").get("record"), "")
        self.assertEqual(gw.latest_sleep_quality("R1203", "B2").get("record"), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)

