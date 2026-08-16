from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_visible(text: str, cwd: str | None, home: str | None) -> str:
    repository = str(Path(cwd).parent) if cwd else None
    replacements = sorted(
        ((value, label) for value, label in ((cwd, "<WORKSPACE>"), (repository, "<REPOSITORY>"), (home, "<HOME>")) if value),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for value, label in replacements:
        text = re.sub(re.escape(value), label, text, flags=re.IGNORECASE)
        text = re.sub(re.escape(value.replace("\\", "/")), label, text, flags=re.IGNORECASE)
    return text


def redact_object(value: Any, cwd: str | None, home: str | None) -> Any:
    if isinstance(value, str):
        return redact_visible(value, cwd, home)
    if isinstance(value, list):
        return [redact_object(item, cwd, home) for item in value]
    if isinstance(value, dict):
        return {key: redact_object(item, cwd, home) for key, item in value.items()}
    return value


def marker_stats(texts: list[str]) -> dict[str, int]:
    joined = "\n".join(texts)
    return {
        "reasoning_blocks": len(texts),
        "reasoning_chars": sum(map(len, texts)),
        "reasoning_words": len(WORD_RE.findall(joined)),
        "we": len(re.findall(r"\bwe\b", joined, flags=re.IGNORECASE)),
        "let_me": len(re.findall(r"\blet me\b", joined, flags=re.IGNORECASE)),
        "lets": len(re.findall(r"\blet's\b", joined, flags=re.IGNORECASE)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--session-meta", type=Path, required=True)
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dsh-version", required=True)
    parser.add_argument("--dsh-commit", required=True)
    parser.add_argument("--preset-hash", required=True)
    parser.add_argument("--benchmark-commit", required=True)
    parser.add_argument("--price", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    meta = json.loads(args.session_meta.read_text(encoding="utf-8"))
    reasoning: list[str] = []
    visible: list[str] = []
    usage: Counter[str] = Counter()
    tools: Counter[str] = Counter()
    catalogs: list[dict[str, Any]] = []
    system_hashes: list[str] = []
    request_index = 0
    turn_start: int | None = None
    turn_end: int | None = None

    for raw_line in args.session.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        event = json.loads(raw_line)
        event_type = event.get("type")
        data = event.get("data", {})
        if event_type == "request/header":
            request_index += 1
            header = data.get("header", {})
            catalog = header.get("tools", [])
            fingerprint = hashlib.sha256(canonical(catalog)).hexdigest()
            if not catalogs or catalogs[-1]["tools_sha256"] != fingerprint:
                catalogs.append({
                    "request_index": request_index,
                    "tool_names": [item.get("name") for item in catalog],
                    "tools_sha256": fingerprint,
                    "tools": catalog,
                })
            system_hashes.append(hashlib.sha256(str(header.get("system", "")).encode("utf-8")).hexdigest())
        elif event_type == "turn/start":
            turn_start = event.get("time")
        elif event_type == "turn/end":
            turn_end = event.get("time")
        elif event_type == "assistant/message":
            for key, value in data.get("usage", {}).items():
                if isinstance(value, int):
                    usage[key] += value
            for block in data.get("message", {}).get("content", []):
                block_type = block.get("type")
                if block_type == "reasoning":
                    reasoning.append(str(block.get("text", "")))
                elif block_type == "text" and block.get("text"):
                    visible.append(str(block["text"]))
                elif block_type == "tool-call":
                    tools[str(block.get("name", "<unknown>"))] += 1

    price_data = json.loads(args.price.read_text(encoding="utf-8")) if args.price else None
    cache_read = usage.get("cacheReadTokens", 0)
    input_tokens = usage.get("inputTokens", 0)
    output_tokens = usage.get("outputTokens", 0)
    # DSH TokenUsage is disjoint: the DeepSeek adapter already subtracts cache
    # hits from wire prompt_tokens before publishing inputTokens.
    miss_tokens = input_tokens
    cost = None
    if price_data:
        rates = price_data["applicable_cny_per_million"]
        cost = round((cache_read * rates["cache_hit"] + miss_tokens * rates["cache_miss"] + output_tokens * rates["output"]) / 1_000_000, 6)

    benchmark_result = None
    result_sha256 = None
    if args.result:
        result_sha256 = sha256_file(args.result)
        benchmark_result = redact_object(json.loads(args.result.read_text(encoding="utf-8")), meta.get("cwd"), str(Path.home()))

    started = datetime.fromisoformat(meta["startedAt"].replace("Z", "+00:00"))
    ended = datetime.fromisoformat(meta["endedAt"].replace("Z", "+00:00"))
    public_visible = [redact_visible(text, meta.get("cwd"), str(Path.home())) for text in visible]
    payload = {
        "schema_version": 1,
        "benchmark": args.benchmark,
        "benchmark_commit": args.benchmark_commit,
        "task_id": args.task_id,
        "run_id": args.run_id,
        "model": meta.get("model"),
        "provider": meta.get("provider"),
        "reasoning_effort": meta.get("reasoningEffort"),
        "dsh_version": args.dsh_version,
        "dsh_commit": args.dsh_commit,
        "preset": meta.get("preset"),
        "preset_hash": args.preset_hash,
        "os_environment": "Windows 10 / PowerShell / DSH native Windows",
        "started_at_utc": meta["startedAt"],
        "ended_at_utc": meta["endedAt"],
        "wall_time_seconds": round((ended - started).total_seconds(), 3),
        "turn_duration_seconds": round((turn_end - turn_start) / 1000, 3) if isinstance(turn_start, int) and isinstance(turn_end, int) else None,
        "benchmark_result": benchmark_result,
        "benchmark_result_sha256": result_sha256,
        "usage": dict(sorted(usage.items())),
        "input_tokens": input_tokens,
        "cache_read_tokens": cache_read,
        "cache_miss_tokens": miss_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": usage.get("reasoningTokens", 0),
        "api_cost_cny": cost,
        "api_cost_scope": "DSH completed agent assistant/message usage; official runtime rates; auxiliary title traffic excluded",
        "usage_semantics": "input_tokens and cache_read_tokens are disjoint DSH counts",
        "tool_call_count": sum(tools.values()),
        "distinct_tools_used": sorted(tools),
        "tool_breakdown": dict(sorted(tools.items())),
        "visible_assistant_replies": public_visible,
        "first_request_tool_catalog": catalogs[0] if catalogs else None,
        "catalog_transition": catalogs,
        "system_prompt_sha256_by_request": system_hashes,
        "trajectory_fingerprints": marker_stats(reasoning),
        "raw_evidence_sha256": sha256_file(args.session),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": args.run_id, "api_cost_cny": cost, "raw_evidence_sha256": payload["raw_evidence_sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
