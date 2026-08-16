from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def redact_text(text: str, workspace: str | None) -> str:
    values = [
        (workspace, "<WORKSPACE>"),
        (str(Path(workspace).parent) if workspace else None, "<REPOSITORY>"),
        (str(Path.home()), "<HOME>"),
    ]
    for value, label in sorted((item for item in values if item[0]), key=lambda item: len(item[0]), reverse=True):
        text = re.sub(re.escape(value), label, text, flags=re.IGNORECASE)
        text = re.sub(re.escape(value.replace("\\", "/")), label, text, flags=re.IGNORECASE)
    return text


def redact_object(value: Any, workspace: str | None) -> Any:
    if isinstance(value, str):
        return redact_text(value, workspace)
    if isinstance(value, list):
        return [redact_object(item, workspace) for item in value]
    if isinstance(value, dict):
        return {key: redact_object(item, workspace) for key, item in value.items()}
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
    parser.add_argument("--run-meta", type=Path, required=True)
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--price", type=Path, required=True)
    parser.add_argument("--balance", type=Path)
    parser.add_argument("--t0-balance", type=Path)
    parser.add_argument("--t1-balance", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--benchmark-commit", required=True)
    args = parser.parse_args()

    root = json.loads(args.session.read_text(encoding="utf-8"))
    meta = json.loads(args.run_meta.read_text(encoding="utf-8"))
    gate = json.loads(args.gate.read_text(encoding="utf-8"))
    price = json.loads(args.price.read_text(encoding="utf-8"))
    balance = json.loads(args.balance.read_text(encoding="utf-8")) if args.balance else None
    info = root.get("info", {})
    reasoning: list[str] = []
    visible: list[str] = []
    tools: Counter[str] = Counter()
    assistant_messages: list[dict[str, Any]] = []
    system_hashes: list[str] = []

    for message in root.get("messages", []):
        message_info = message.get("info", {})
        if message_info.get("role") == "user" and isinstance(message_info.get("system"), str):
            system_hashes.append(hashlib.sha256(message_info["system"].encode("utf-8")).hexdigest())
        if message_info.get("role") != "assistant":
            continue
        assistant_messages.append(message_info)
        for part in message.get("parts", []):
            part_type = part.get("type")
            if part_type == "reasoning":
                reasoning.append(str(part.get("text", "")))
            elif part_type == "text" and part.get("text"):
                visible.append(str(part["text"]))
            elif part_type == "tool":
                tools[str(part.get("tool", "<unknown>"))] += 1

    first_assistant = assistant_messages[0] if assistant_messages else {}
    tokens = info.get("tokens", {}) if isinstance(info.get("tokens"), dict) else {}
    cache = tokens.get("cache", {}) if isinstance(tokens.get("cache"), dict) else {}
    cache_miss = int(tokens.get("input", 0) or 0)
    cache_read = int(cache.get("read", 0) or 0)
    output = int(tokens.get("output", 0) or 0)
    reasoning_tokens = int(tokens.get("reasoning", 0) or 0)
    rates = price["applicable_cny_per_million"]
    recomputed_cost = round(
        (
            cache_miss * rates["cache_miss"]
            + cache_read * rates["cache_hit"]
            + (output + reasoning_tokens) * rates["output"]
        )
        / 1_000_000,
        6,
    )

    benchmark_result = None
    result_hash = None
    if args.result:
        result_hash = sha256_file(args.result)
        benchmark_result = redact_object(
            json.loads(args.result.read_text(encoding="utf-8")),
            meta.get("workspace"),
        )

    cost_reconciliation = None
    if balance is not None:
        account_delta = float(balance["balance_delta_cny"])
        t0_hash = sha256_file(args.t0_balance) if args.t0_balance else None
        t1_hash = sha256_file(args.t1_balance) if args.t1_balance else None
        cost_reconciliation = {
            "balance_generation": balance.get("balance_generation"),
            "t0_raw_sha256": t0_hash,
            "t1_raw_sha256": t1_hash,
            "account_balance_delta_cny": account_delta,
            "official_rate_recomputed_agent_usage_cny": recomputed_cost,
            "account_minus_recomputed_cny": round(account_delta - recomputed_cost, 6),
            "crosses_recharge_event": bool(balance.get("crosses_recharge_event", False)),
            "notes": "Stable account T0/T1 delta and OpenCode disjoint-token recomputation are reported independently.",
        }

    payload = {
        "schema_version": 1,
        "experimental_status": "post-preregistered exploratory harness comparison",
        "excluded_from_dsh_mechanism_ablation": True,
        "benchmark": "project2-v4.1b",
        "benchmark_commit": args.benchmark_commit,
        "task_id": "project2-v4-broken-seed",
        "run_id": args.run_id,
        "model": first_assistant.get("modelID", "deepseek-v4-pro"),
        "provider": first_assistant.get("providerID", "deepseek"),
        "resolved_endpoint": meta.get("resolved_endpoint"),
        "reasoning_effort": meta.get("reasoning_variant"),
        "opencode_version": gate["opencode_version"],
        "opencode_commit": gate["opencode_commit"],
        "agent": first_assistant.get("agent", meta.get("agent")),
        "agent_mode": gate["agent_mode"],
        "models_catalog_sha256": gate["models_catalog_sha256"],
        "system_instruction_source": gate["system_instruction_source"],
        "os_environment": "Windows 10 / PowerShell / OpenCode native Windows",
        "started_at_utc": meta["started_at_utc"],
        "ended_at_utc": meta["ended_at_utc"],
        "wall_time_seconds": meta["wall_time_seconds"],
        "opencode_exit_code": meta["opencode_exit_code"],
        "stop_reason": meta.get("stop_reason"),
        "benchmark_result": benchmark_result,
        "benchmark_result_sha256": result_hash,
        "usage": tokens,
        "cache_miss_tokens": cache_miss,
        "cache_read_tokens": cache_read,
        "output_tokens": output,
        "reasoning_tokens": reasoning_tokens,
        "billable_output_tokens": output + reasoning_tokens,
        "api_cost_cny": recomputed_cost,
        "opencode_catalog_cost": info.get("cost"),
        "api_cost_scope": "OpenCode session usage recomputed at official live CNY rates",
        "usage_semantics": "OpenCode v1.18.17 stores cache-miss input, cache-read input, non-reasoning output, and reasoning output as disjoint counts",
        "assistant_message_count": len(assistant_messages),
        "visible_assistant_replies": [redact_text(text, meta.get("workspace")) for text in visible],
        "visible_assistant_reply_count": len(visible),
        "tool_call_count": sum(tools.values()),
        "distinct_tools_used": sorted(tools),
        "tool_breakdown": dict(sorted(tools.items())),
        "first_request_tool_catalog": {
            "evidence_source": "zero-cost static resolution via `opencode debug agent build --pure`; not a wire request capture",
            "tool_names": gate["tool_names"],
            "tool_count": len(gate["tool_names"]),
        },
        "catalog_transition": "OpenCode comparison has no anchoring transition; static-resolved full catalog applies from request 1",
        "system_prompt_sha256_by_user_message": system_hashes,
        "trajectory_fingerprints": marker_stats(reasoning),
        "trajectory_comparison": "available" if reasoning else "unavailable_or_incomplete",
        "raw_evidence_sha256": sha256_file(args.session),
        "cost_reconciliation": cost_reconciliation,
        "run_status": "completed" if meta.get("opencode_exit_code") == 0 and meta.get("export_exit_code") == 0 else "infrastructure_failed",
        "benchmark_score_status": "evaluator_result_recorded" if benchmark_result is not None else "evaluation_pending",
        "valid_for_harness_score_comparison": benchmark_result is not None,
        "valid_for_dsh_mechanism_ablation": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "reasoning_effort": payload["reasoning_effort"],
                "api_cost_cny": recomputed_cost,
                "raw_evidence_sha256": payload["raw_evidence_sha256"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
