from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


URL = "https://api-docs.deepseek.com/zh-cn/quick_start/pricing"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request = urllib.request.Request(URL, headers={"User-Agent": "modeltest-anchoring-prereg/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    text = raw.decode("utf-8")
    compact = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    required = ["0.025", "3元", "6元"]
    missing = [item for item in required if item not in compact]
    if missing:
        raise RuntimeError(f"官方页面缺少预期当前价格字段：{missing}")
    future = all(item in compact for item in ["0.15元", "4.5元", "13.5元", "0.30元", "9.0元", "27.0元"])
    args.private_html.parent.mkdir(parents=True, exist_ok=True)
    args.private_html.write_bytes(raw)
    retrieved_at = datetime.now(timezone.utc)
    future_effective_at = datetime(2026, 8, 17, 0, 0, tzinfo=ZoneInfo("Asia/Shanghai"))
    current_rates = {"cache_hit": 0.025, "cache_miss": 3.0, "output": 6.0}
    future_rates = {
        "off_peak": {"cache_hit": 0.15, "cache_miss": 4.5, "output": 13.5},
        "peak": {"cache_hit": 0.30, "cache_miss": 9.0, "output": 27.0},
    }
    if retrieved_at >= future_effective_at.astimezone(timezone.utc):
        raise RuntimeError("官方页面的未来价格已生效；需按页面实时峰谷时段重建适用价格后再发起付费请求")
    result = {
        "schema_version": 1,
        "source_url": URL,
        "retrieved_at_utc": retrieved_at.isoformat(),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "current_cny_per_million": current_rates,
        "applicable_cny_per_million": current_rates,
        "applicable_window": "before_2026-08-17T00:00:00+08:00",
        "documented_future_effective_at": future_effective_at.isoformat(),
        "documented_future_cny_per_million": future_rates if future else None,
        "documented_future_peak_offpeak_present": future,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
