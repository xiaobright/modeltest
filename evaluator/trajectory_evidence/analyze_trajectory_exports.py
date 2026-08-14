#!/usr/bin/env python3
"""Aggregate DSH JSONL and OpenCode JSON exports without publishing raw reasoning."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)
FIRST_TOKEN_RE = re.compile(r"^[^\w']*([\w']+)", re.UNICODE)
MARKER_RE = re.compile(r"^(good|great|excellent)\.(?:\s|$)", re.IGNORECASE)
EXACT_MARKER_RE = re.compile(r"^(good|great|excellent)\.?$", re.IGNORECASE)
TOOL_SYNTAX_RE = re.compile(r"tools\.[A-Za-z_][A-Za-z0-9_]*\(")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[math.floor((len(ordered) - 1) * fraction)]


def count_phrase(texts: Iterable[str], pattern: str) -> int:
    regex = re.compile(pattern, re.IGNORECASE)
    return sum(len(regex.findall(text)) for text in texts)


def text_stats(texts: list[str]) -> dict[str, Any]:
    texts = [text for text in texts if text]
    lengths = [len(text) for text in texts]
    words = [len(WORD_RE.findall(text)) for text in texts]
    first_tokens: Counter[str] = Counter()
    marker_starts = 0
    exact_marker_first_lines = 0
    for text in texts:
        match = FIRST_TOKEN_RE.match(text)
        if match:
            first_tokens[match.group(1).lower()] += 1
        first_line = text.splitlines()[0].strip() if text.splitlines() else ""
        marker_starts += bool(MARKER_RE.match(text))
        exact_marker_first_lines += bool(EXACT_MARKER_RE.fullmatch(first_line))
    return {
        "blocks": len(texts),
        "chars": sum(lengths),
        "words": sum(words),
        "p50_chars": percentile(lengths, 0.5),
        "p90_chars": percentile(lengths, 0.9),
        "marker_starts": marker_starts,
        "exact_marker_first_lines": exact_marker_first_lines,
        "we": count_phrase(texts, r"\bwe\b"),
        "let_me": count_phrase(texts, r"\blet me\b"),
        "i": count_phrase(texts, r"\bi\b"),
        "top_first_tokens": dict(first_tokens.most_common(12)),
    }


def tool_result_error_code(event: dict[str, Any]) -> str | None:
    error = event.get("data", {}).get("error")
    return error.get("code") if isinstance(error, dict) else None


def analyze_dsh(path: Path) -> dict[str, Any]:
    reasoning: list[str] = []
    visible: list[str] = []
    tools: Counter[str] = Counter()
    usage: Counter[str] = Counter()
    header: dict[str, Any] = {}
    start: int | None = None
    end: int | None = None
    assistant_messages = 0
    outer_args: dict[str, dict[str, Any] | None] = {}
    outer_errors: Counter[str] = Counter()
    subcalls_by_root: Counter[str] = Counter()
    subcall_tools: Counter[str] = Counter()
    subcall_errors = 0

    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            event_type = event.get("type")
            data = event.get("data", {})
            if event_type == "request/header":
                header = data.get("header", {})
            elif event_type == "turn/start":
                start = event.get("time")
            elif event_type == "turn/end":
                end = event.get("time")
            elif event_type == "assistant/message":
                assistant_messages += 1
                for key, value in data.get("usage", {}).items():
                    if isinstance(value, int):
                        usage[key] += value
                for block in data.get("message", {}).get("content", []):
                    block_type = block.get("type")
                    if block_type == "reasoning":
                        reasoning.append(block.get("text", ""))
                    elif block_type == "text":
                        visible.append(block.get("text", ""))
                    elif block_type == "tool-call":
                        tools[block.get("name", "<unknown>")] += 1
            elif event_type == "tool/call":
                call_id = str(data.get("callId", ""))
                arguments = data.get("arguments")
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = None
                outer_args[call_id] = arguments if isinstance(arguments, dict) else None
            elif event_type == "tool/result":
                code = tool_result_error_code(event)
                if code:
                    outer_errors[code] += 1
            elif event_type == "tool/code-dispatch":
                root_id = str(data.get("rootCallId", ""))
                subcalls_by_root[root_id] += 1
                subcall_tools[data.get("name", "<unknown>")] += 1
                subcall_errors += bool(data.get("isError"))

    config = header.get("config", {})
    wire_tools = [tool.get("name") for tool in header.get("tools", [])]
    result: dict[str, Any] = {
        "format": "dsh-jsonl",
        "model": config.get("model"),
        "reasoning_effort": config.get("reasoningEffort"),
        "system_prompt_sha256": hashlib.sha256(
            header.get("system", "").encode("utf-8")
        ).hexdigest(),
        "wire_tools": wire_tools,
        "assistant_messages": assistant_messages,
        "tool_calls": sum(tools.values()),
        "tool_breakdown": dict(sorted(tools.items())),
        "visible_blocks": len(visible),
        "visible_chars": sum(map(len, visible)),
        "reasoning": text_stats(reasoning),
        "usage": dict(sorted(usage.items())),
        "duration_minutes": (
            round((end - start) / 60_000, 2)
            if isinstance(start, int) and isinstance(end, int)
            else None
        ),
    }
    if wire_tools == ["run_code"]:
        distribution = Counter(subcalls_by_root.get(call_id, 0) for call_id in outer_args)
        missing_description = 0
        promise_all = 0
        multi_tool_syntax = 0
        for arguments in outer_args.values():
            if not arguments or not str(arguments.get("description", "")).strip():
                missing_description += 1
            code = str(arguments.get("code", "")) if arguments else ""
            promise_all += "Promise.all" in code
            multi_tool_syntax += len(TOOL_SYNTAX_RE.findall(code)) > 1
        result["ptc"] = {
            "outer_calls": len(outer_args),
            "missing_description": missing_description,
            "outer_errors": dict(sorted(outer_errors.items())),
            "subcalls": sum(subcalls_by_root.values()),
            "subcall_breakdown": dict(sorted(subcall_tools.items())),
            "subcall_errors": subcall_errors,
            "subcall_distribution": {
                str(key): value for key, value in sorted(distribution.items())
            },
            "programs_with_promise_all": promise_all,
            "programs_with_multiple_tool_syntax": multi_tool_syntax,
        }
    return result


def analyze_opencode(path: Path) -> dict[str, Any]:
    root = json.loads(path.read_text(encoding="utf-8"))
    reasoning: list[str] = []
    visible: list[str] = []
    tools: Counter[str] = Counter()
    assistant_messages = 0
    for message in root.get("messages", []):
        if message.get("info", {}).get("role") != "assistant":
            continue
        assistant_messages += 1
        for part in message.get("parts", []):
            part_type = part.get("type")
            if part_type == "reasoning":
                reasoning.append(part.get("text", ""))
            elif part_type == "text" and part.get("text"):
                visible.append(part["text"])
            elif part_type == "tool":
                tools[part.get("tool", "<unknown>")] += 1
    info = root.get("info", {})
    timing = info.get("time", {})
    created = timing.get("created")
    updated = timing.get("updated")
    model = info.get("model")
    if isinstance(model, dict):
        model = model.get("id")
    return {
        "format": "opencode-json",
        "model": model,
        "agent": info.get("agent"),
        "assistant_messages": assistant_messages,
        "tool_calls": sum(tools.values()),
        "tool_breakdown": dict(sorted(tools.items())),
        "visible_blocks": len(visible),
        "visible_chars": sum(map(len, visible)),
        "reasoning": text_stats(reasoning),
        "usage": info.get("tokens", {}),
        "cost": info.get("cost"),
        "duration_minutes": (
            round((updated - created) / 60_000, 2)
            if isinstance(created, int) and isinstance(updated, int)
            else None
        ),
    }


def csv_row(item: dict[str, Any]) -> dict[str, Any]:
    reasoning = item["reasoning"]
    usage = item.get("usage", {})
    cache = usage.get("cache", {}) if isinstance(usage.get("cache"), dict) else {}
    ptc = item.get("ptc", {})
    return {
        "label": item["label"],
        "model": item.get("model"),
        "score": item.get("score"),
        "configuration": item.get("configuration"),
        "format": item.get("format"),
        "reasoning_blocks": reasoning["blocks"],
        "reasoning_chars": reasoning["chars"],
        "reasoning_words": reasoning["words"],
        "reasoning_p50_chars": reasoning["p50_chars"],
        "reasoning_p90_chars": reasoning["p90_chars"],
        "marker_first_lines": reasoning["exact_marker_first_lines"],
        "we": reasoning["we"],
        "let_me": reasoning["let_me"],
        "i": reasoning["i"],
        "visible_blocks": item["visible_blocks"],
        "tool_calls": item["tool_calls"],
        "ptc_subcalls": ptc.get("subcalls"),
        "ptc_invalid_args": ptc.get("outer_errors", {}).get("INVALID_ARGS"),
        "ptc_code_failures": ptc.get("outer_errors", {}).get("CODE_RUN_FAILED"),
        "output_tokens": usage.get("outputTokens", usage.get("output")),
        "reasoning_tokens": usage.get("reasoningTokens", usage.get("reasoning")),
        "cache_read_tokens": usage.get("cacheReadTokens", cache.get("read")),
        "duration_minutes": item.get("duration_minutes"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--csv-output", type=Path, required=True)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        path = (args.manifest.parent / source["path"]).resolve()
        expected_hash = source.get("sha256")
        actual_hash = sha256(path)
        if expected_hash and expected_hash != actual_hash:
            raise SystemExit(f"SHA-256 mismatch for {path}")
        if source["format"] == "dsh-jsonl":
            record = analyze_dsh(path)
        elif source["format"] == "opencode-json":
            record = analyze_opencode(path)
        else:
            raise SystemExit(f"Unsupported format: {source['format']}")
        record.update({key: value for key, value in source.items() if key != "path"})
        record["source_sha256"] = actual_hash
        records.append(record)

    payload = {
        "schema_version": 1,
        "method": "Completed assistant messages only; raw streaming chunks excluded.",
        "records": records,
    }
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = [csv_row(record) for record in records]
    args.csv_output.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
