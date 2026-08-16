from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--stdout-log", type=Path, required=True)
    parser.add_argument("--stderr-log", type=Path, required=True)
    args, runner_args = parser.parse_known_args()
    args.stdout_log.parent.mkdir(parents=True, exist_ok=True)
    args.stderr_log.parent.mkdir(parents=True, exist_ok=True)
    with args.stdout_log.open("wb") as stdout, args.stderr_log.open("wb") as stderr:
        process = subprocess.Popen(
            [sys.executable, str(args.runner), *runner_args],
            stdout=stdout,
            stderr=stderr,
            close_fds=True,
        )
        return process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
