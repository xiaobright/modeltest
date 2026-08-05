#!/usr/bin/env python3
"""Compatibility wrapper for the old optional-test entrypoint.

ESP32 static contract checks are now a required part of full evaluation.
This file remains only so older evaluator commands keep working.
"""
import subprocess
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve().parent
    script = here / "run_espidf_static_tests.py"
    return subprocess.run([sys.executable, str(script), *sys.argv[1:]]).returncode


if __name__ == "__main__":
    raise SystemExit(main())
