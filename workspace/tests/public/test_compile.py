#!/usr/bin/env python3
import os
import py_compile
import unittest
from pathlib import Path


class CompileSmokeTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()

    def test_core_python_files_compile(self):
        patterns = [
            "start_project.py",
            "gateway/*.py",
            "voice/voice_assistant_integrated.py",
            "vision/*.py",
            "posture/posture_worker.py",
        ]
        files = []
        for pattern in patterns:
            files.extend(self.project.glob(pattern))
        self.assertTrue(files, "no Python files found to compile")

        errors = []
        for path in files:
            try:
                py_compile.compile(str(path), doraise=True)
            except Exception as exc:
                errors.append(f"{path.relative_to(self.project)}: {exc}")
        self.assertFalse(errors, "\n".join(errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
