#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def run_and_capture(cmd, cwd: Path, env: dict, log_path: Path):
    print(f"[eval] running: {' '.join(map(str, cmd))}")
    with log_path.open("w", encoding="utf-8", errors="replace") as f:
        proc = subprocess.run(
            [str(x) for x in cmd],
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
        )
        f.write(proc.stdout)
    print(f"[eval] exit={proc.returncode} log={log_path}")
    return proc.returncode


def collect_git_artifacts(project: Path, results_dir: Path):
    """Save git diff, status, and log from the candidate workspace."""
    git_dir = project / ".git"
    if not git_dir.is_dir():
        print("[eval] no git repo in workspace — skipping diff collection")
        return {}

    info = {}

    baseline = "HEAD"
    for tag in ("project2-v4-broken-seed", "project2-v2-broken-seed"):
        tag_check = subprocess.run(
            ["git", "rev-parse", "--verify", tag],
            cwd=str(project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=30,
        )
        if tag_check.returncode == 0:
            baseline = tag
            break
    info["baseline"] = baseline

    diff_path = results_dir / "candidate_diff.patch"
    proc = subprocess.run(
        ["git", "diff", baseline],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=60,
    )
    if proc.returncode == 0:
        diff_path.write_text(proc.stdout, encoding="utf-8")
        info["diff"] = str(diff_path)
        info["diff_lines"] = proc.stdout.count("\n")
        # churn
        short = subprocess.run(
            ["git", "diff", "--shortstat", baseline],
            cwd=str(project),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=30,
        )
        if short.returncode == 0:
            info["shortstat"] = short.stdout.strip()
    else:
        print(f"[eval] WARNING: git diff failed: {proc.stderr.strip()}")

    proc = subprocess.run(
        ["git", "status", "--short"],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=30,
    )
    if proc.returncode == 0:
        status_path = results_dir / "candidate_status.txt"
        status_path.write_text(proc.stdout, encoding="utf-8")
        info["status"] = str(status_path)
        changed_files = [l for l in proc.stdout.splitlines() if l.strip()]
        info["changed_file_count"] = len(changed_files)

    proc = subprocess.run(
        ["git", "log", "--oneline", "-20"],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=30,
    )
    if proc.returncode == 0:
        log_path = results_dir / "candidate_log.txt"
        log_path.write_text(proc.stdout, encoding="utf-8")
        info["log"] = str(log_path)

    # duration from first/last commit if any
    log_full = subprocess.run(
        ["git", "log", "--format=%ct", baseline + "..HEAD"],
        cwd=str(project),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
        timeout=30,
    )
    if log_full.returncode == 0 and log_full.stdout.strip():
        times = [int(x) for x in log_full.stdout.splitlines() if x.strip().isdigit()]
        if len(times) >= 2:
            info["duration_sec"] = max(times) - min(times)
            info["duration_source"] = "git"
        elif len(times) == 1:
            info["duration_sec"] = 0
            info["duration_source"] = "git_single_commit"
    else:
        info["duration_source"] = "unknown"

    print(f"[eval] git artifacts saved: {info.get('changed_file_count', '?')} files changed")
    return info


def collect_pr_template_artifact(project: Path, results_dir: Path):
    """Copy the developer's required PULL_REQUEST_TEMPLATE.md into the results directory."""
    info = {"expected": str(project / "PULL_REQUEST_TEMPLATE.md")}
    pr_path = None
    for name in ("PULL_REQUEST_TEMPLATE.md", "pull_request_template.md"):
        candidate = project / name
        if candidate.is_file():
            pr_path = candidate
            break

    if pr_path is None:
        print(f"[eval] WARNING: required PULL_REQUEST_TEMPLATE.md not found under {project}")
        info["found"] = False
        return info

    dst = results_dir / "pull_request_template.md"
    shutil.copyfile(pr_path, dst)
    info.update({
        "found": True,
        "source": str(pr_path),
        "artifact": str(dst),
        "bytes": dst.stat().st_size,
    })
    print(f"[eval] PR template artifact saved: {dst}")
    return info


def collect_espidf_build_evidence(
    project: Path,
    results_dir: Path,
    log_path: Path,
    return_code: int,
) -> dict:
    """Archive ESP-IDF build outputs so later builds cannot overwrite F9 evidence."""
    artifact_dir = results_dir / "espidf_build_artifacts"
    manifest = {
        "status": "passed" if return_code == 0 else "failed",
        "return_code": return_code,
        "project": str(project),
        "log": str(log_path),
        "artifacts": [],
        "evidence_complete": False,
    }
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    output_paths = []
    for match in re.finditer(r"^\[espidf\]\s+output_bin\s*=\s*(.+?)\s*$", text, re.MULTILINE):
        candidate = Path(match.group(1).strip())
        if candidate.is_file() and candidate not in output_paths:
            output_paths.append(candidate)

    if output_paths:
        artifact_dir.mkdir(parents=True, exist_ok=True)
    for source in output_paths:
        destination = artifact_dir / source.name
        shutil.copy2(source, destination)
        stat = destination.stat()
        manifest["artifacts"].append({
            "name": destination.name,
            "source": str(source),
            "archived": str(destination),
            "bytes": stat.st_size,
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
            "mtime_utc": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
        })

    manifest["evidence_complete"] = return_code == 0 and bool(manifest["artifacts"])
    manifest_path = results_dir / "espidf_build_evidence.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"[eval] ESP-IDF build evidence status={manifest['status']} "
        f"artifacts={len(manifest['artifacts'])} manifest={manifest_path}"
    )
    return {
        "manifest": str(manifest_path),
        "artifact_dir": str(artifact_dir) if artifact_dir.is_dir() else "",
        "evidence_complete": manifest["evidence_complete"],
        "artifact_count": len(manifest["artifacts"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", nargs="?", default="")
    parser.add_argument("--reset", action="store_true", help="run make_broken_project.py before evaluating")
    parser.add_argument(
        "--include-espidf-static",
        action="store_true",
        help="legacy no-op: ESP-IDF static checks are now required and run by default",
    )
    parser.add_argument(
        "--skip-espidf-static",
        action="store_true",
        help="debug only: skip required ESP-IDF static checks",
    )
    parser.add_argument("--include-espidf-build", action="store_true")
    parser.add_argument("--no-diff", action="store_true", help="skip git diff collection")
    parser.add_argument("--meta", type=Path, default=None, help="optional meta.json path to copy into results")
    parser.add_argument("--model", default="", help="model id for meta.json")
    parser.add_argument("--channel", default="", help="channel id for meta.json")
    parser.add_argument("--harness", default="", help="harness id for meta.json")
    parser.add_argument(
        "--require-meta",
        action="store_true",
        help="fail before evaluation unless model/channel/harness are all non-empty",
    )
    parser.add_argument(
        "--run-group-id",
        default="",
        help="multi-run group id (same model+channel+harness+thinking)",
    )
    parser.add_argument("--run-index", type=int, default=0, help="1-based run index within run_group_id")
    parser.add_argument("--thinking-level", default="", help="medium/high/xhigh/...")
    parser.add_argument("--provider", default="", help="provider identity for calibration")
    parser.add_argument("--endpoint-product", default="", help="endpoint product name")
    parser.add_argument("--billing-tier", default="", help="subscription/paygo/...")
    parser.add_argument(
        "--meta-extra",
        type=Path,
        default=None,
        help="optional JSON file merged into meta (tokens/cost/efficiency fields)",
    )
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    model_eval = here.parent
    root = model_eval.parent
    project = Path(args.project).resolve() if args.project else model_eval / "workspace" / "project2_task"

    meta = {
        "model": args.model or os.environ.get("EVAL_MODEL", ""),
        "channel": args.channel or os.environ.get("EVAL_CHANNEL", ""),
        "harness": args.harness or os.environ.get("EVAL_HARNESS", ""),
        "benchmark": "project2-v4.1b",
        "seed_tag": "project2-v4-broken-seed",
        "registry_version": "v4.1b",
    }
    if args.meta and args.meta.is_file():
        try:
            meta.update(json.loads(args.meta.read_text(encoding="utf-8")))
        except Exception as exc:
            print(f"[eval] WARNING: meta load failed: {exc}")
    if args.meta_extra and args.meta_extra.is_file():
        try:
            extra = json.loads(args.meta_extra.read_text(encoding="utf-8"))
            if isinstance(extra, dict):
                meta.update(extra)
            else:
                print("[eval] WARNING: --meta-extra must be a JSON object")
        except Exception as exc:
            print(f"[eval] WARNING: meta-extra load failed: {exc}")
    # CLI multi-run / calibration fields override empty meta slots
    for key, value in (
        ("run_group_id", args.run_group_id or os.environ.get("EVAL_RUN_GROUP_ID", "")),
        ("thinking_level", args.thinking_level or os.environ.get("EVAL_THINKING_LEVEL", "")),
        ("provider", args.provider or os.environ.get("EVAL_PROVIDER", "")),
        ("endpoint_product", args.endpoint_product or os.environ.get("EVAL_ENDPOINT_PRODUCT", "")),
        ("billing_tier", args.billing_tier or os.environ.get("EVAL_BILLING_TIER", "")),
    ):
        if value and not meta.get(key):
            meta[key] = value
    if args.run_index and not meta.get("run_index"):
        meta["run_index"] = int(args.run_index)
    elif os.environ.get("EVAL_RUN_INDEX") and not meta.get("run_index"):
        try:
            meta["run_index"] = int(os.environ["EVAL_RUN_INDEX"])
        except ValueError:
            pass
    meta_missing = [key for key in ("model", "channel", "harness") if not meta.get(key)]
    meta["complete"] = not meta_missing
    meta["meta_partial"] = not all(
        meta.get(k) for k in ("run_group_id", "run_index", "thinking_level")
    )
    if args.require_meta and meta_missing:
        parser.error("formal evaluation requires non-empty: " + ", ".join(meta_missing))

    results_dir = here / "results" / time.strftime("%Y%m%d_%H%M%S")
    results_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    env = os.environ.copy()
    env["PROJECT_DIR"] = str(project)
    env["PYTHONWARNINGS"] = "ignore::ResourceWarning"

    summary = {
        "project": str(project),
        "results_dir": str(results_dir),
        "benchmark": meta.get("benchmark") or "project2-v4.1b",
        "steps": {},
        "details": {},
        "meta": meta,
        "meta_complete": meta["complete"],
    }

    if args.reset:
        summary["steps"]["reset"] = run_and_capture(
            [sys.executable, here / "make_broken_project.py"],
            root,
            env,
            results_dir / "reset.log",
        )

    summary["steps"]["public"] = run_and_capture(
        [sys.executable, here / "tests" / "run_public_tests.py", project],
        root,
        env,
        results_dir / "public.log",
    )
    summary["steps"]["debug_probe"] = run_and_capture(
        [sys.executable, here / "tools" / "run_debug_probe.py", project],
        root,
        env,
        results_dir / "debug_probe.log",
    )
    hidden_summary = results_dir / "hidden_summary.json"
    summary["details"]["hidden_summary"] = str(hidden_summary)
    summary["steps"]["hidden"] = run_and_capture(
        [sys.executable, here / "run_hidden_tests.py", project, "--summary-json", hidden_summary],
        root,
        env,
        results_dir / "hidden.log",
    )

    if not args.skip_espidf_static:
        espidf_static_summary = results_dir / "espidf_static_summary.json"
        summary["details"]["espidf_static_summary"] = str(espidf_static_summary)
        summary["steps"]["espidf_static"] = run_and_capture(
            [sys.executable, here / "run_espidf_static_tests.py", project, "--summary-json", espidf_static_summary],
            root,
            env,
            results_dir / "espidf_static.log",
        )

    if args.include_espidf_build:
        build_script = here / "run_espidf_build.py"
        build_log = results_dir / "espidf_build.log"
        build_code = run_and_capture(
            [sys.executable, build_script, project],
            root,
            env,
            build_log,
        )
        summary["steps"]["espidf_build"] = build_code
        build_evidence_info = collect_espidf_build_evidence(
            project, results_dir, build_log, build_code
        )
        summary["details"]["espidf_build_evidence"] = build_evidence_info
        summary["steps"]["espidf_build_evidence"] = (
            0 if build_code != 0 or build_evidence_info["evidence_complete"] else 1
        )

    summary["details"]["pr_template"] = collect_pr_template_artifact(project, results_dir)

    if not args.no_diff:
        git_info = collect_git_artifacts(project, results_dir)
        summary["details"]["git"] = git_info
        if git_info.get("duration_sec") is not None:
            summary["duration_sec"] = git_info["duration_sec"]
            summary["duration_source"] = git_info.get("duration_source")
        else:
            summary["duration_sec"] = int(time.time() - t0)
            summary["duration_source"] = "eval_wall"

    # V4 score draft artifacts
    try:
        sys.path.insert(0, str(here / "scoring"))
        from score_model import draft_from_results_dir, write_score_artifacts  # type: ignore

        # write summary first so draft_from_results_dir can read steps
        summary_path = results_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        (results_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        payload = draft_from_results_dir(results_dir, meta=meta)
        write_score_artifacts(results_dir, payload)
        draft = payload["score_draft"]
        blockers = payload["blockers"]
        # Keep summary.json in lockstep with score_draft / blockers (never leave stale drafts).
        summary["ability_draft"] = draft.get("ability_draft")
        summary["ship_draft"] = draft.get("ship_draft")
        summary["release_class_hint"] = draft.get("release_class_hint")
        summary["blockers"] = blockers.get("final")
        summary["behavior_blockers"] = blockers.get("behavior_blockers")
        summary["semantic_only_codes"] = blockers.get("semantic_only_codes")
        summary["f9_mode"] = draft.get("f9_mode")
        summary["f11_status"] = draft.get("f11_status")
        summary["family_draft"] = draft.get("family_draft")
        summary["dimensions"] = draft.get("dimensions") or payload.get("dimensions")
        summary["details"]["score_draft"] = str(results_dir / "score_draft.json")
        summary["details"]["blockers"] = str(results_dir / "blockers.json")
        summary["details"]["score_draft_confidence"] = str(results_dir / "score_draft_confidence.json")
        summary["details"]["dimensions"] = str(results_dir / "dimensions.json")
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"[eval] V4 draft ability={summary.get('ability_draft')} "
            f"ship={summary.get('ship_draft')} class={summary.get('release_class_hint')} "
            f"f11={summary.get('f11_status')} blockers={summary.get('blockers')}"
        )
    except Exception as exc:
        print(f"[eval] WARNING: score draft failed: {exc}")
        summary_path = results_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    failed = [name for name, code in summary["steps"].items() if code != 0]
    # hidden/public failures are expected for broken candidates — still return 1 if any step failed
    if failed:
        print(f"[eval] failed steps: {failed}")
        return 1
    print(f"[eval] all enabled steps passed. summary={results_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
