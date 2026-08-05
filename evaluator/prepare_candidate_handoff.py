#!/usr/bin/env python3
"""Create an allowlisted candidate workspace outside the evaluator tree."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


MODEL_EVAL = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = MODEL_EVAL / "workspace"
ALLOWED_ENTRIES = (
    "ONBOARDING_TODO.md",
    "reference",
    "tests",
    "tools",
    "project2_task",
)
FORBIDDEN_TOP_LEVEL = {
    "archives",
    "docs",
    "evaluator",
    "mcps",
    "terminals",
}


def default_output() -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return MODEL_EVAL.parent / f"{MODEL_EVAL.name}_candidate_handoffs" / stamp / "workspace"


def git_value(project: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=30,
    )
    return proc.stdout.strip() if proc.returncode == 0 else ""


def git_history_audit(project: Path) -> dict:
    head = git_value(project, "rev-parse", "HEAD")
    tree = git_value(project, "rev-parse", "HEAD^{tree}")
    count_text = git_value(project, "rev-list", "--all", "--count")
    commit_count = int(count_text) if count_text.isdigit() else 0
    refs = [
        line.split(" ", 1)
        for line in git_value(
            project,
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            "refs/heads",
            "refs/tags",
        ).splitlines()
        if " " in line
    ]
    reflog_heads = sorted({
        line.strip()
        for line in git_value(project, "reflog", "--all", "--format=%H").splitlines()
        if line.strip()
    })
    fsck = subprocess.run(
        ["git", "fsck", "--no-reflogs", "--unreachable", "--no-progress"],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=60,
    )
    unreachable = [line.strip() for line in fsck.stdout.splitlines() if line.strip()]
    refs_at_head = bool(refs) and all(target == head for _, target in refs)
    reflog_only_head = bool(reflog_heads) and reflog_heads == [head]
    safe = bool(
        head
        and tree
        and commit_count == 1
        and refs_at_head
        and reflog_only_head
        and fsck.returncode == 0
        and not unreachable
    )
    return {
        "safe": safe,
        "head": head,
        "tree": tree,
        "commit_count": commit_count,
        "refs": [{"name": name, "target": target} for name, target in refs],
        "refs_at_head": refs_at_head,
        "reflog_heads": reflog_heads,
        "reflog_only_head": reflog_only_head,
        "unreachable_objects": unreachable,
        "fsck_return_code": fsck.returncode,
    }


def validate_handoff(workspace: Path) -> dict:
    names = {p.name for p in workspace.iterdir()}
    missing = [name for name in ALLOWED_ENTRIES if name not in names]
    unexpected = sorted(names.difference(ALLOWED_ENTRIES))
    forbidden = sorted(names.intersection(FORBIDDEN_TOP_LEVEL))
    project = workspace / "project2_task"
    git_audit = git_history_audit(project) if (project / ".git").is_dir() else {
        "safe": False,
        "reason": "candidate project has no .git directory",
    }
    return {
        "valid": (
            not missing
            and not unexpected
            and not forbidden
            and project.is_dir()
            and git_audit["safe"]
        ),
        "entries": sorted(names),
        "missing": missing,
        "unexpected": unexpected,
        "forbidden": forbidden,
        "project_exists": project.is_dir(),
        "project_head": git_audit.get("head", ""),
        "project_tree": git_audit.get("tree", ""),
        "git_history": git_audit,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy only candidate-visible files into a fresh external handoff workspace."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    source = args.source.resolve()
    output = (args.output or default_output()).resolve()
    if not source.is_dir():
        parser.error(f"source workspace not found: {source}")
    missing_sources = [name for name in ALLOWED_ENTRIES if not (source / name).exists()]
    if missing_sources:
        parser.error("required candidate entries missing: " + ", ".join(missing_sources))
    source_project = source / "project2_task"
    source_git_audit = (
        git_history_audit(source_project)
        if (source_project / ".git").is_dir()
        else {"safe": False, "reason": "candidate project has no .git directory"}
    )
    if not source_git_audit["safe"]:
        parser.error(
            "source project Git history is not a single clean broken-seed history; "
            "refusing to create handoff"
        )
    if output.exists():
        parser.error(f"output already exists; choose a fresh path: {output}")
    if output == MODEL_EVAL or MODEL_EVAL in output.parents:
        parser.error("handoff output must be outside the evaluator project tree")

    output.mkdir(parents=True)
    for name in ALLOWED_ENTRIES:
        src = source / name
        dst = output / name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    validation = validate_handoff(output)
    manifest = {
        "benchmark": "project2-v4.1b",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_workspace": str(source),
        "candidate_workspace": str(output),
        "allowlist": list(ALLOWED_ENTRIES),
        "validation": validation,
    }
    manifest_path = output.parent / "HANDOFF_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not validation["valid"]:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 1

    print(f"[handoff] candidate_workspace={output}")
    print(f"[handoff] candidate_project={output / 'project2_task'}")
    print(f"[handoff] manifest={manifest_path}")
    print(f"[handoff] entries={', '.join(validation['entries'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
