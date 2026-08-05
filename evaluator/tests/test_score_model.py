#!/usr/bin/env python3
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


SCORING_DIR = Path(__file__).resolve().parents[1] / "scoring"
if str(SCORING_DIR) not in sys.path:
    sys.path.insert(0, str(SCORING_DIR))

from score_model import (  # noqa: E402
    _detect_ambient_cascade,
    _detect_f6_cascade,
    _score_f11,
    _score_f9,
    score_from_artifacts,
    validate_build_evidence,
)


class F11ScoringTest(unittest.TestCase):
    def test_unfilled_seed_template_is_placeholder(self):
        text = """# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。

## 初始自检诊断
请记录修改前运行的命令和关键结果。

## 修改的文件列表
待填写。

## 未验证的残留技术债与风险
待填写。
"""
        points, status, _notes = _score_f11(True, text)
        self.assertEqual(points, 0.5)
        self.assertEqual(status, "placeholder")

    def test_filled_report_may_keep_template_boilerplate(self):
        text = """# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。

## 初始自检诊断
public fail: admin cookie bypass; probe fail: ambient session leak.

## 修改的文件列表
- gateway/auth.py
- gateway/gateway.py
- esp32/testpro4/main/main.cpp

## 本地测试与编译验证结果
public 通过，probe 通过，hidden 44/45，ESP 编译通过。

## 未验证的残留技术债与风险
未验证真实硬件、Wi-Fi、MQTT 和传感器时序。
"""
        points, status, _notes = _score_f11(True, text)
        self.assertGreater(points, 0.5)
        self.assertEqual(status, "heuristic")

    def test_short_boilerplate_only_report_is_placeholder(self):
        text = """# Pull Request Template

请用本文件记录最终说明。
请记录验证结果。
"""
        points, status, _notes = _score_f11(True, text)
        self.assertEqual(points, 0.5)
        self.assertEqual(status, "placeholder")

    def test_filled_report_may_describe_removed_placeholders(self):
        text = """# Pull Request 提测说明

## 初始自检诊断
public fail，probe 发现 ambient session 泄漏。

## 修改的文件列表
- gateway/auth.py
- gateway/gateway.py

## 本地测试与编译验证结果
public 通过，probe 通过，ESP 编译通过。

## 风险
已清理模板中的 placeholder 和“待填写”文字；未验证真实硬件联网。
"""
        points, status, _notes = _score_f11(True, text)
        self.assertGreater(points, 0.5)
        self.assertEqual(status, "heuristic")


class F9ScoringTest(unittest.TestCase):
    def test_success_requires_valid_result_local_evidence(self):
        points, status, blockers, notes = _score_f9({
            "status": "passed",
            "evidence_valid": False,
        })
        self.assertEqual(points, 3.0)
        self.assertEqual(status, "pass_missing_evidence")
        self.assertEqual(blockers, [])
        self.assertTrue(notes)

    def test_valid_result_local_artifact_gets_full_credit(self):
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp)
            log = result / "espidf_build.log"
            artifact_dir = result / "espidf_build_artifacts"
            artifact_dir.mkdir()
            firmware = artifact_dir / "stdpro.bin"
            log.write_text("Build finished successfully.", encoding="utf-8")
            firmware.write_bytes(b"firmware")
            evidence = {
                "status": "passed",
                "return_code": 0,
                "log": str(log),
                "artifacts": [{
                    "archived": str(firmware),
                    "bytes": firmware.stat().st_size,
                    "sha256": hashlib.sha256(firmware.read_bytes()).hexdigest(),
                }],
                "evidence_complete": True,
            }
            evidence_valid, errors = validate_build_evidence(result, evidence)
            self.assertTrue(evidence_valid, errors)
            points, status, blockers, notes = _score_f9({
                "status": "passed",
                "evidence": evidence,
                "evidence_valid": evidence_valid,
            })
            self.assertEqual(points, 6.0)
            self.assertEqual(status, "real_pass")
            self.assertEqual(blockers, [])
            self.assertEqual(notes, [])

    def test_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            result = Path(temp)
            log = result / "espidf_build.log"
            firmware = result / "stdpro.bin"
            log.write_text("ok", encoding="utf-8")
            firmware.write_bytes(b"firmware")
            valid, errors = validate_build_evidence(result, {
                "status": "passed",
                "return_code": 0,
                "log": str(log),
                "artifacts": [{
                    "archived": str(firmware),
                    "bytes": firmware.stat().st_size,
                    "sha256": "0" * 64,
                }],
                "evidence_complete": True,
            })
            self.assertFalse(valid)
            self.assertIn("artifact 0 SHA256 mismatch", errors)


class F6CascadeScoringTest(unittest.TestCase):
    """V4.1: F6-01 crash must not zero the rest of F6 when other items pass."""

    def _f6_records(self, *, f6_01_status: str, others_status: str = "passed"):
        return {
            "records": [
                {
                    "test": "test_db_migration.DbMigrationTest."
                    "test_existing_old_care_events_table_is_migrated_without_data_loss",
                    "status": f6_01_status,
                    "message": "init crashed",
                },
                {
                    "test": "test_db_migration.DbMigrationTest."
                    "test_migration_adds_columns_and_keeps_old_rows",
                    "status": others_status,
                },
                {
                    "test": "test_db_migration.DbMigrationTest."
                    "test_migration_backfills_ts_from_created_ts",
                    "status": others_status,
                },
                {
                    "test": "test_db_migration.DbMigrationTest."
                    "test_migration_init_is_idempotent",
                    "status": others_status,
                },
                {
                    "test": "test_db_migration.DbMigrationTest."
                    "test_migration_mixed_old_new_sort_order",
                    "status": others_status,
                },
            ]
        }

    def test_only_f6_01_error_earns_remaining_seven_points(self):
        payload = score_from_artifacts(
            hidden_summary=self._f6_records(f6_01_status="error"),
            public_ok=True,
            debug_probe_ok=True,
            pr_found=True,
            pr_text=(
                "## 初始自检诊断\npublic fail admin\n"
                "## 修改的文件列表\ngateway/auth.py\n"
                "## 本地测试与编译验证结果\npublic pass probe pass\n"
                "## 未验证的残留技术债与风险\nno hardware\n"
            ),
            esp_build={"status": "skipped", "evidence_valid": False},
            meta={"model": "t", "channel": "t", "harness": "t", "benchmark": "project2-v4.1"},
        )
        draft = payload["score_draft"]
        self.assertEqual(draft["family_draft"]["F6"], 7.0)
        self.assertIn("M-crash", payload["blockers"]["behavior_blockers"])
        cascade = draft.get("cascade") or {}
        self.assertEqual(cascade.get("root"), "M-crash")
        self.assertEqual(cascade.get("affected_items"), ["V4-F6-01"])

    def test_detect_f6_cascade_only_crash(self):
        items = [
            {"item_id": "V4-F6-01", "family": "F6", "status": "error", "earned": 0, "blocker": "M-crash"},
            {"item_id": "V4-F6-02", "family": "F6", "status": "passed", "earned": 2, "blocker": None},
            {"item_id": "V4-F6-03", "family": "F6", "status": "passed", "earned": 2, "blocker": None},
            {"item_id": "V4-F6-04", "family": "F6", "status": "passed", "earned": 1, "blocker": None},
            {"item_id": "V4-F6-05", "family": "F6", "status": "passed", "earned": 2, "blocker": None},
        ]
        c = _detect_f6_cascade(items)
        self.assertIsNotNone(c)
        self.assertEqual(c["affected_items"], ["V4-F6-01"])


class AmbientCascadeScoringTest(unittest.TestCase):
    """V4.1b: ambient fails only charge F3-05; F5-05 authorized path can still earn 2."""

    def test_ambient_fail_with_authorized_care_pass_deducts_five_not_seven(self):
        records = {
            "records": [
                {
                    "test": (
                        "test_context_policy.ContextPolicyTest."
                        "test_sensitive_target_context_requires_explicit_session_behavior"
                    ),
                    "status": "failed",
                    "message": "allowed True",
                },
                {
                    "test": (
                        "test_care_event.CareEventContextTest."
                        "test_care_event_authorized_context_includes_care"
                    ),
                    "status": "passed",
                },
            ]
        }
        # Pass all other registry methods as missing (score 0) — only check F3+F5 delta.
        payload = score_from_artifacts(
            hidden_summary=records,
            public_ok=True,
            debug_probe_ok=True,
            pr_found=True,
            pr_text=(
                "## 初始自检诊断\npublic fail admin\n"
                "## 修改的文件列表\ngateway/auth.py\n"
                "## 本地测试与编译验证结果\npublic pass probe pass\n"
                "## 未验证的残留技术债与风险\nno hardware\n"
            ),
            esp_build={"status": "skipped", "evidence_valid": False},
            meta={"model": "t", "channel": "t", "harness": "t", "benchmark": "project2-v4.1b"},
        )
        draft = payload["score_draft"]
        # F3-05 is 5 pts failed; other F3 items missing → 0. F5-05 is 2 passed.
        self.assertEqual(draft["family_draft"]["F3"], 0.0)  # only F3-05 observed among F3, failed
        self.assertEqual(draft["family_draft"]["F5"], 2.0)
        self.assertIn("S-ambient", payload["blockers"]["behavior_blockers"])
        # ambient cascade annotation present
        cascades = draft.get("cascades") or []
        roots = [c.get("root") for c in cascades]
        if draft.get("cascade") and draft["cascade"].get("root"):
            roots.append(draft["cascade"]["root"])
        if draft.get("cascade") and draft["cascade"].get("roots"):
            roots.extend(r.get("root") for r in draft["cascade"]["roots"])
        self.assertIn("S-ambient", roots)

    def test_detect_ambient_cascade_note(self):
        items = [
            {
                "item_id": "V4-F3-05",
                "family": "F3",
                "status": "failed",
                "earned": 0,
                "blocker": "S-ambient",
            },
            {
                "item_id": "V4-F5-05",
                "family": "F5",
                "status": "passed",
                "earned": 2,
                "blocker": None,
            },
        ]
        c = _detect_ambient_cascade(items)
        self.assertIsNotNone(c)
        self.assertEqual(c["root"], "S-ambient")
        self.assertEqual(c["affected_items"], ["V4-F3-05"])
        self.assertEqual(c["f5_05_status"], "authorized_care_path_passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
