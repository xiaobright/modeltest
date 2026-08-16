from __future__ import annotations

import argparse
import json
from pathlib import Path


def cny_total(path: Path) -> float:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return sum(float(item["total_balance"]) for item in payload.get("balance_infos", []) if item.get("currency") == "CNY")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--t0", type=Path, required=True)
    parser.add_argument("--t1", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--generation", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    delta = round(cny_total(args.t0) - cny_total(args.t1), 6)
    if delta < 0:
        raise RuntimeError("T1 balance 高于 T0；该区间包含充值或余额调整，不作为单枪费用差")
    result = {
        "schema_version": 1,
        "run_id": args.run_id,
        "balance_generation": args.generation,
        "balance_delta_cny": delta,
        "crosses_recharge_event": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
