#!/usr/bin/env python3
import os
import re
import subprocess
import unittest
from pathlib import Path


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


class ProcessContractTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()
        self.pr_template_path = self.project / "PULL_REQUEST_TEMPLATE.md"

    def read_pr_template(self) -> str:
        self.assertTrue(self.pr_template_path.is_file(), "PULL_REQUEST_TEMPLATE.md is required")
        return self.pr_template_path.read_text(encoding="utf-8", errors="replace")

    def git_changed_paths(self) -> set[str]:
        baseline = "HEAD"
        tag_check = subprocess.run(
            ["git", "rev-parse", "--verify", "project2-v2-broken-seed"],
            cwd=str(self.project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=30,
        )
        if tag_check.returncode == 0:
            baseline = "project2-v2-broken-seed"
        diff_proc = subprocess.run(
            ["git", "diff", "--name-only", baseline],
            cwd=str(self.project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=30,
        )
        self.assertEqual(diff_proc.returncode, 0, diff_proc.stderr)
        paths = {line.strip().replace("\\", "/") for line in diff_proc.stdout.splitlines() if line.strip()}

        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(self.project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            paths.add(line[3:].replace("\\", "/"))
        return paths

    def test_pr_template_records_required_debug_commands(self):
        text = normalize(self.read_pr_template())
        for token in (
            "run_public_tests.py",
            "run_debug_probe.py",
            "run_espidf_build.py",
        ):
            self.assertIn(token, text, f"PULL_REQUEST_TEMPLATE.md must record {token} result or explicit failure reason")
        self.assertTrue(
            any(token in text for token in ("初始", "before", "修改前", "diagnostic", "probe")),
            "PULL_REQUEST_TEMPLATE.md must distinguish initial diagnosis from final verification",
        )
        self.assertTrue(
            any(token in text for token in ("最终", "after", "修复后", "final", "verification")),
            "PULL_REQUEST_TEMPLATE.md must record final verification after fixes",
        )

    def test_pr_template_does_not_claim_missing_esp_helper_files(self):
        text = normalize(self.read_pr_template())
        helper_names = {
            "protocol_packet": "esp32/testpro4/main/protocol_packet",
            "maixsense_parser": "esp32/testpro4/main/maixsense_parser",
            "device_config": "esp32/testpro4/main/device_config",
            "mqtt_payload": "esp32/testpro4/main/mqtt_payload",
        }
        changed = self.git_changed_paths()
        existing = {p.replace("\\", "/") for p in changed}
        for name, path_prefix in helper_names.items():
            if name in text:
                has_file = any(p.startswith(path_prefix) for p in existing)
                self.assertTrue(has_file, f"PULL_REQUEST_TEMPLATE.md claims {name}, but no matching changed file exists")

    def test_candidate_did_not_modify_visible_test_or_probe_scripts(self):
        changed = self.git_changed_paths()
        forbidden_prefixes = (
            "tests/",
            "tools/run_debug_probe.py",
            "tools/run_espidf_build.py",
            "tools/run_espidf_windows_build.ps1",
            "tools/run_espidf_wsl_build.ps1",
        )
        touched = sorted(
            path for path in changed
            if any(path.startswith(prefix) for prefix in forbidden_prefixes)
        )
        self.assertFalse(
            touched,
            "candidate-visible tests/tools should be used as diagnostics, not modified for scoring: "
            + ", ".join(touched),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
