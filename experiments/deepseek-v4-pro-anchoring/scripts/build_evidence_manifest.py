from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PUBLIC_ARTIFACTS = [
    "README.md",
    "RESULTS.md",
    "mock-prompt.txt",
    "preregistration.json",
    "run-matrix.json",
    "artifacts/environment-baseline.json",
    "artifacts/schema-gate.json",
    "artifacts/opencode-gate.json",
    "artifacts/deepswe-gate.json",
    "artifacts/balance-events.json",
    "artifacts/infrastructure-events.json",
    "artifacts/metadata-corrections.json",
    "artifacts/comparison.json",
    "artifacts/price-snapshot.json",
    "artifacts/price-P2-20260815-01-anchored.json",
    "artifacts/price-P2-20260815-02-standard.json",
    "artifacts/price-P2-20260815-03-minimal-full.json",
    "artifacts/price-P2-20260815-04-opencode.json",
    "artifacts/price-P2-20260815-04b-opencode-replacement.json",
    "artifacts/runs/P2-20260815-01-anchored-balance.json",
    "artifacts/runs/P2-20260815-01-anchored.json",
    "artifacts/runs/P2-20260815-02-standard-balance.json",
    "artifacts/runs/P2-20260815-02-standard.json",
    "artifacts/runs/P2-20260815-03-minimal-full-balance.json",
    "artifacts/runs/P2-20260815-03-minimal-full.json",
    "artifacts/runs/P2-20260815-04-opencode-partial-balance.json",
    "artifacts/runs/P2-20260815-04-opencode-partial.json",
    "artifacts/runs/P2-20260815-04b-opencode-replacement-balance.json",
    "artifacts/runs/P2-20260815-04b-opencode-replacement.json",
]

PRIVATE_EVIDENCE = [
    ("P2-20260815-01-anchored", "dsh_session_jsonl", "private/project2/P2-20260815-01-anchored/session.jsonl"),
    ("P2-20260815-02-standard", "dsh_session_jsonl", "private/project2/P2-20260815-02-standard/session.jsonl"),
    ("P2-20260815-03-minimal-full", "dsh_session_jsonl", "private/project2/P2-20260815-03-minimal-full/session.jsonl"),
    ("P2-20260815-04-opencode-partial", "opencode_partial_session_export", "private/project2/P2-20260815-04-opencode/interrupted-session-export.json"),
    ("P2-20260815-04-opencode-partial", "opencode_partial_event_stream", "private/project2/P2-20260815-04-opencode/events.jsonl"),
    ("P2-20260815-04b-opencode-replacement", "opencode_session_export", "private/project2/P2-20260815-04b-opencode-replacement/session-export.json"),
    ("P2-20260815-04b-opencode-replacement", "opencode_event_stream", "private/project2/P2-20260815-04b-opencode-replacement/events.jsonl"),
    ("P2-20260815-04b-opencode-replacement", "opencode_run_meta", "private/project2/P2-20260815-04b-opencode-replacement/run-meta.json"),
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def public_entry(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    return {"path": relative.replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def private_entry(root: Path, run_id: str, kind: str, relative: str) -> dict[str, Any]:
    path = root / relative
    return {"run_id": run_id, "evidence_kind": kind, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.experiment_root.resolve()
    payload = {
        "schema_version": 1,
        "contributor": "@NineThoughts0521",
        "evidence_role": "independent third-party replication; excluded from maintainer formal n",
        "candidate_prompt_sha256": "576103f9a5a7a619c0669674cf384a975b89390bb034c368a53a148251f2df84",
        "public_artifacts": [public_entry(root, relative) for relative in PUBLIC_ARTIFACTS],
        "private_raw_evidence": [private_entry(root, run_id, kind, relative) for run_id, kind, relative in PRIVATE_EVIDENCE],
        "privacy": {
            "private_paths_published": False,
            "raw_reasoning_or_session_published": False,
            "credentials_published": False,
            "recalculation": "Recompute each listed SHA-256 from the ignored local raw file and compare it with this manifest and the corresponding public run artifact.",
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"public": len(payload["public_artifacts"]), "private": len(payload["private_raw_evidence"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
