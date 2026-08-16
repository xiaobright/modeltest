from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RUNS = [
    {
        "run_id": "P2-20260815-01-anchored",
        "label": "DSH Anchored Standard",
        "preset": "anchored-standard",
        "evaluator_result_id": "20260815_122420",
        "causal_role": "preregistered DSH mechanism ablation",
    },
    {
        "run_id": "P2-20260815-02-standard",
        "label": "DSH Standard",
        "preset": "standard",
        "evaluator_result_id": "20260815_162840",
        "causal_role": "preregistered DSH mechanism ablation",
    },
    {
        "run_id": "P2-20260815-03-minimal-full",
        "label": "DSH Minimal-Full",
        "preset": "minimal-full",
        "evaluator_result_id": "20260815_164240",
        "causal_role": "preregistered DSH mechanism ablation",
    },
    {
        "run_id": "P2-20260815-04b-opencode-replacement",
        "label": "OpenCode replacement",
        "preset": "opencode-direct-deepseek",
        "evaluator_result_id": "20260815_194422",
        "causal_role": "post-preregistered exploratory harness comparison",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluation_counts(evaluator_root: Path, result_id: str) -> dict[str, str]:
    result = evaluator_root / result_id
    hidden = read_json(result / "hidden_summary.json")
    esp = read_json(result / "espidf_static_summary.json")
    return {
        "hidden": f"{hidden.get('passed', 0)}/{hidden.get('tests_run', 0)}",
        "esp_static": f"{esp.get('passed', 0)}/{esp.get('tests_run', 0)}",
    }


def build_run(experiment_root: Path, evaluator_root: Path, spec: dict[str, str]) -> dict[str, Any]:
    artifact = read_json(experiment_root / "artifacts" / "runs" / f"{spec['run_id']}.json")
    benchmark = artifact.get("benchmark_result") or {}
    reconciliation = artifact.get("cost_reconciliation") or {}
    fingerprints = artifact.get("trajectory_fingerprints") or {}
    catalog = artifact.get("first_request_tool_catalog") or {}
    counts = evaluation_counts(evaluator_root, spec["evaluator_result_id"])
    visible_replies = artifact.get("visible_assistant_reply_count")
    if visible_replies is None:
        visible_replies = len(artifact.get("visible_assistant_replies") or [])
    return {
        "run_id": spec["run_id"],
        "label": spec["label"],
        "preset": spec["preset"],
        "causal_role": spec["causal_role"],
        "benchmark": artifact.get("benchmark", "project2-v4.1b"),
        "benchmark_commit": artifact.get("benchmark_commit"),
        "task_id": artifact.get("task_id"),
        "model": artifact.get("model"),
        "provider": artifact.get("provider"),
        "reasoning_effort": artifact.get("reasoning_effort"),
        "resolved_endpoint": artifact.get("resolved_endpoint") or artifact.get("resolved_api_endpoint"),
        "ability": benchmark.get("ability_draft"),
        "ship": benchmark.get("ship_draft"),
        "class": benchmark.get("release_class_hint"),
        "hidden": counts["hidden"],
        "esp_static": counts["esp_static"],
        "f9": benchmark.get("family_draft", {}).get("F9"),
        "f9_mode": benchmark.get("f9_mode"),
        "reasoning_blocks": fingerprints.get("reasoning_blocks"),
        "we": fingerprints.get("we"),
        "let_me": fingerprints.get("let_me"),
        "lets": fingerprints.get("lets"),
        "visible_assistant_replies": visible_replies,
        "tool_calls": artifact.get("tool_call_count"),
        "distinct_tools": artifact.get("distinct_tools_used", []),
        "input_tokens": artifact.get("cache_miss_tokens"),
        "cache_read_tokens": artifact.get("cache_read_tokens"),
        "output_tokens": artifact.get("output_tokens"),
        "reasoning_tokens": artifact.get("reasoning_tokens"),
        "usage_cost_cny": artifact.get("api_cost_cny"),
        "balance_delta_cny": reconciliation.get("account_balance_delta_cny"),
        "balance_cost_difference_cny": reconciliation.get("account_minus_recomputed_cny"),
        "wall_time_seconds": artifact.get("wall_time_seconds"),
        "first_request_tool_count": catalog.get("tool_count", len(catalog.get("tool_names", []))),
        "first_request_tool_names": catalog.get("tool_names", []),
        "catalog_transition": artifact.get("catalog_transition"),
        "raw_evidence_sha256": artifact.get("raw_evidence_sha256"),
        "benchmark_result_sha256": artifact.get("benchmark_result_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--evaluator-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    runs = [build_run(args.experiment_root, args.evaluator_root, spec) for spec in RUNS]
    runs_by_id = {run["run_id"]: run for run in runs}
    partial = read_json(args.experiment_root / "artifacts" / "runs" / "P2-20260815-04-opencode-partial.json")
    infrastructure = read_json(args.experiment_root / "artifacts" / "infrastructure-events.json")
    partial_event = next(
        event
        for event in infrastructure["events"]
        if event["run_id"] == "P2-20260815-04-opencode-partial"
    )
    valid_account_cost = round(sum(float(run["balance_delta_cny"]) for run in runs), 6)
    valid_usage_cost = round(sum(float(run["usage_cost_cny"]) for run in runs), 6)
    partial_account_cost = float(partial["account_balance_delta_cny"])
    partial_usage_cost = float(partial["api_cost_cny"])
    anchored = runs_by_id["P2-20260815-01-anchored"]["ability"]
    standard = runs_by_id["P2-20260815-02-standard"]["ability"]
    minimal_full = runs_by_id["P2-20260815-03-minimal-full"]["ability"]
    opencode = runs_by_id["P2-20260815-04b-opencode-replacement"]["ability"]
    payload = {
        "schema_version": 1,
        "contributor": "@NineThoughts0521",
        "evidence_role": "independent third-party replication; excluded from maintainer formal n",
        "benchmark": "project2-v4.1b",
        "benchmark_commit": "04255b55f16c4439e538239fb9783070c4165081",
        "task_id": "project2-v4-broken-seed",
        "model": "deepseek-v4-pro",
        "reasoning_effort": "max",
        "pricing_policy": "official live CNY rates at each run; no peak/off-peak assumption",
        "runs": runs,
        "preserved_partial": {
            "run_id": partial["run_id"],
            "status": partial["run_status"],
            "benchmark_score_status": partial["benchmark_score_status"],
            "reasoning_blocks": partial["trajectory_fingerprints"]["reasoning_blocks"],
            "we": partial["trajectory_fingerprints"]["we"],
            "let_me": partial["trajectory_fingerprints"]["let_me"],
            "lets": partial["trajectory_fingerprints"]["lets"],
            "visible_assistant_replies": partial["visible_assistant_reply_count"],
            "export_tool_calls": partial["tool_call_count"],
            "event_stream_completed_tool_events": partial_event["completed_tool_events"],
            "final_stop_observed": partial_event["final_stop_observed"],
            "usage_cost_cny": partial_usage_cost,
            "balance_delta_cny": partial_account_cost,
            "raw_evidence_sha256": partial["raw_evidence_sha256"],
            "partial_event_stream_sha256": partial["partial_event_stream_sha256"],
            "valid_for_harness_score_comparison": False,
        },
        "descriptive_contrasts": {
            "standard_minus_minimal_full_ability": round(standard - minimal_full, 6),
            "anchored_minus_minimal_full_ability": round(anchored - minimal_full, 6),
            "anchored_minus_standard_ability": round(anchored - standard, 6),
            "opencode_minus_anchored_ability": round(opencode - anchored, 6),
            "opencode_minus_standard_ability": round(opencode - standard, 6),
        },
        "cost_totals_cny": {
            "four_valid_runs_account_balance": valid_account_cost,
            "four_valid_runs_usage_recomputed": valid_usage_cost,
            "preserved_partial_account": partial_account_cost,
            "preserved_partial_usage_recomputed": partial_usage_cost,
            "all_account_balance_including_partial": round(valid_account_cost + partial_account_cost, 6),
            "all_usage_recomputed_including_partial": round(valid_usage_cost + partial_usage_cost, 6),
            "all_account_minus_usage_recomputed": round(valid_account_cost + partial_account_cost - valid_usage_cost - partial_usage_cost, 6),
        },
        "limitations": [
            "The three DSH rows are single frozen-task observations; no significance test or new score is introduced.",
            "OpenCode is exploratory and excluded from the DSH mechanism-ablation contrasts.",
            "F9 is 3/6 skipped_env because the preregistered optional real ESP-IDF build was not run.",
            "Trajectory wording is a fingerprint only, not a capability metric or causal evidence.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runs": len(runs), "output": str(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
