from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


URL = "https://api.deepseek.com/user/balance"


def credential() -> str:
    value = os.environ.get("DEEPSEEK_API_KEY")
    if value:
        return value
    path = Path(os.environ.get("DSH_HOME", Path.home() / ".dsh")) / ".credentials.yaml"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DEEPSEEK_API_KEY:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    raise RuntimeError("未找到 DSH DeepSeek credential")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--required-cny", type=float, default=50.0)
    args = parser.parse_args()
    request = urllib.request.Request(URL, headers={"Authorization": f"Bearer {credential()}", "User-Agent": "modeltest-anchoring-prereg/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8"))
    cny_total = sum(float(item["total_balance"]) for item in payload.get("balance_infos", []) if item.get("currency") == "CNY")
    result = {
        "schema_version": 1,
        "source_url": URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "is_available": bool(payload.get("is_available")),
        "cny_balance_at_least_required": cny_total >= args.required_cny,
        "required_cny": args.required_cny,
    }
    args.private_json.parent.mkdir(parents=True, exist_ok=True)
    args.private_json.write_bytes(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if not result["is_available"] or not result["cny_balance_at_least_required"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
