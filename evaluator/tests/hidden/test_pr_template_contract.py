#!/usr/bin/env python3
import os
import re
import unittest
from pathlib import Path


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.lower() in text for token in tokens)


class PrTemplateContractTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()
        self.pr_template_path = self.project / "PULL_REQUEST_TEMPLATE.md"

    def read_pr_template(self) -> str:
        self.assertTrue(
            self.pr_template_path.is_file(),
            "developer must write final PR details to project2_task/PULL_REQUEST_TEMPLATE.md",
        )
        return self.pr_template_path.read_text(encoding="utf-8", errors="replace")

    def test_pr_template_exists_and_is_nontrivial(self):
        text = self.read_pr_template()
        compact = normalize(text)
        self.assertGreaterEqual(
            len(compact),
            500,
            "PULL_REQUEST_TEMPLATE.md is too short to support consistent PR review; include changed files, design, tests, and risks",
        )
        placeholders = ("待填写", "todo: fill", "<fill", "tbd")
        self.assertFalse(
            contains_any(compact, placeholders),
            "PULL_REQUEST_TEMPLATE.md still appears to contain placeholder text",
        )

    def test_pr_template_covers_required_review_topics(self):
        text = normalize(self.read_pr_template())
        required_groups = {
            "changed files": ("修改", "changed file", "modified file", "文件"),
            "architecture": ("架构", "architecture", "模块", "module"),
            "security": ("安全", "security", "鉴权", "auth", "权限", "privacy"),
            "sleep import": ("sleep", "睡眠", "csv", "room/bed"),
            "care_event": ("care_event", "care event", "护理事件"),
            "esp32": ("esp32", "esp-idf", "固件", "mqtt"),
            "verification": ("测试", "verification", "test", "run_public_tests", "run_debug_probe"),
            "risks": ("风险", "risk", "未验证", "残留", "技术债"),
        }
        missing = [name for name, tokens in required_groups.items() if not contains_any(text, tokens)]
        self.assertFalse(missing, f"PULL_REQUEST_TEMPLATE.md missing required review topics: {', '.join(missing)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
