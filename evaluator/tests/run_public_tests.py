#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    here = Path(__file__).resolve().parent
    project = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (here.parents[1] / "project2_task")
    if not project.exists():
        print(f"[public] project not found: {project}")
        return 2

    env = os.environ.copy()
    env["PROJECT_DIR"] = str(project)
    env["PYTHONWARNINGS"] = "ignore::ResourceWarning"

    failures = 0
    for test_file in sorted((here / "public").glob("test_*.py")):
        print(f"\n[public] running {test_file.name}")
        proc = subprocess.run([sys.executable, str(test_file)], env=env)
        if proc.returncode != 0:
            failures += 1

    if failures:
        print(f"\n[public] failed files: {failures}")
        return 1
    print("\n[public] all public tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
