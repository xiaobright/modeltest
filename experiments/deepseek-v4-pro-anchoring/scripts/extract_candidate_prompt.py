from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.read_text(encoding="utf-8")
    matches = re.findall(r"```text\s*\n(.*?)\n```", source, flags=re.DOTALL)
    if len(matches) != 1:
        raise RuntimeError(f"候选正文代码块数量应为 1，实际为 {len(matches)}")
    prompt = matches[0].replace("\r\n", "\n").rstrip() + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(prompt, encoding="utf-8", newline="\n")
    print(hashlib.sha256(prompt.encode("utf-8")).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
