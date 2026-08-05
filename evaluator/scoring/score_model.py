#!/usr/bin/env python3
"""V4 automatic Ability / Ship / blockers draft from eval artifacts."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REGISTRY_PATH = HERE / "item_registry.json"

FAMILY_MAX = {
    "F1": 8,
    "F2": 12,
    "F3": 16,
    "F4": 4,
    "F5": 12,
    "F6": 10,
    "F7": 8,
    "F8": 8,
    "F9": 6,
    "F10": 8,
    "F11": 4,
    "F12": 4,
}

# Hard placeholder markers: any remaining marker means the template is unfinished.
_PR_HARD_PLACEHOLDER_PATTERNS = [
    r"(?m)^\s*(?:[-*]\s*)?待填写[。.!！]?\s*$",
    r"(?m)^\s*(?:[-*]\s*)?TODO:\s*fill(?:\s+.*)?$",
    r"(?m)^\s*(?:[-*]\s*)?TBD[。.!！]?\s*$",
    r"(?m)^\s*(?:[-*]\s*)?(?:placeholder|<\s*placeholder\s*>|\[\s*placeholder\s*\])[。.!！]?\s*$",
]

_PR_BOILERPLATE_PATTERNS = [
    r"请记录",
    r"请用本文件记录",
    r"Pull Request Template",
    r"PULL_REQUEST_TEMPLATE",
]


def load_registry(path: Path | None = None) -> dict:
    p = path or REGISTRY_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def _method_name(test_id: str) -> str:
    return test_id.rsplit(".", 1)[-1]


def _index_records(hidden_summary: dict | None, static_summary: dict | None) -> dict[str, dict]:
    by_method: dict[str, dict] = {}
    for summary in (hidden_summary, static_summary):
        if not summary:
            continue
        for file_summary in summary.get("files") or []:
            for rec in file_summary.get("records") or []:
                method = _method_name(rec.get("test", ""))
                if method:
                    by_method[method] = rec
        for rec in summary.get("records") or []:
            method = _method_name(rec.get("test", ""))
            if method:
                by_method[method] = rec
    return by_method


def _is_placeholder_pr(pr_text: str) -> bool:
    if not pr_text or len(pr_text.strip()) < 80:
        return True

    if any(re.search(pat, pr_text, re.I) for pat in _PR_HARD_PLACEHOLDER_PATTERNS):
        return True

    filled_markers = (
        r"初始自检诊断[\s\S]{20,}(?!待填写)",
        r"修改的文件[\s\S]{10,}\.(py|cpp|md|h)",
        r"(验证|public|probe|hidden).{0,40}(通过|fail|ok|pass)",
        r"(未验证|残留|风险)[\s\S]{20,}",
    )
    substantive = sum(1 for p in filled_markers if re.search(p, pr_text, re.I))
    if substantive >= 2 and len(pr_text.strip()) >= 240:
        return False

    boilerplate_hits = sum(
        1 for pat in _PR_BOILERPLATE_PATTERNS if re.search(pat, pr_text, re.I)
    )
    return substantive == 0 or boilerplate_hits >= 2


def _score_f11(pr_found: bool | None, pr_text: str | None) -> tuple[float, str, list[str]]:
    """Returns (points, status, overestimate_notes)."""
    notes: list[str] = []
    if pr_found is False or not pr_text:
        notes.append("F11: PR missing or empty")
        return 0.5, "missing", notes
    if _is_placeholder_pr(pr_text):
        notes.append("F11: PR still looks like unfilled template (待填写/请记录/boilerplate)")
        return 0.5, "placeholder", notes
    hits = 0
    for token in ("初始", "验证", "ESP", "风险", "public", "probe", "debug", "care_event", "迁移"):
        if token.lower() in pr_text.lower():
            hits += 1
    # Require real content length beyond template
    score = min(4.0, 1.0 + hits * 0.4)
    if len(pr_text) > 800:
        score = min(4.0, score + 0.5)
    return round(score, 2), "heuristic", notes


def _score_f9(esp_build: dict | None) -> tuple[float, str, list[str], list[str]]:
    """Returns (points, f9_mode, blockers, notes)."""
    blockers: list[str] = []
    notes: list[str] = []
    build = esp_build or {}
    build_status = (build.get("status") or "").lower()
    claimed_success = bool(build.get("claimed_success"))
    if build_status in ("passed", "success", "ok"):
        if build.get("evidence_valid") is True:
            return 6.0, "real_pass", blockers, notes
        notes.append(
            "F9: build returned success but result-local log/bin/hash evidence is incomplete; "
            "fixed 3/6 pending valid evidence"
        )
        return 3.0, "pass_missing_evidence", blockers, notes
    if build_status in ("failed", "error"):
        if claimed_success:
            blockers.extend(["E-build", "P-report"])
            return 0.0, "overclaim_fail", blockers, notes
        blockers.append("E-build")
        return 3.5, "real_fail_honest", blockers, notes
    if build_status in ("skipped", "skipped_env", ""):
        notes.append("F9: toolchain skipped; fixed 3/6 (not full credit)")
        return 3.0, "skipped_env", blockers, notes
    notes.append("F9: build status unknown; partial credit 3/6")
    return 3.0, "unknown_default_partial", blockers, notes


def score_from_artifacts(
    *,
    hidden_summary: dict | None = None,
    espidf_static_summary: dict | None = None,
    public_ok: bool | None = None,
    debug_probe_ok: bool | None = None,
    pr_found: bool | None = None,
    pr_text: str | None = None,
    esp_build: dict | None = None,
    git_info: dict | None = None,
    meta: dict | None = None,
    registry: dict | None = None,
) -> dict[str, Any]:
    reg = registry or load_registry()
    items = reg.get("items") or []
    family_max = dict(reg.get("family_max") or FAMILY_MAX)
    by_method = _index_records(hidden_summary, espidf_static_summary)

    family_earned = {k: 0.0 for k in family_max}
    item_results = []
    behavior_blockers: list[str] = []
    semantic_failures: list[dict] = []
    unscored: list[str] = []
    overestimate_risks: list[str] = []

    # Process registry items that map to tests (skip pure heuristics handled below if no method)
    for item in items:
        item_id = item["item_id"]
        family = item["family"]
        points = float(item.get("points") or 0)
        method = item.get("test_method") or ""
        semantic_only = bool(item.get("semantic_only"))
        blocker = item.get("blocker")
        source = item.get("source") or "hidden"

        # Heuristic-only items (F9/F11 synthetic) scored later
        if source in ("build_heuristic", "report_heuristic") and not method:
            continue

        if points <= 0 and not method:
            continue

        rec = by_method.get(method) if method else None

        if method and rec is None:
            unscored.append(item_id)
            status = "missing"
            earned = 0.0
            overestimate_risks.append(f"{item_id}: test missing -> scored 0 (may under-estimate)")
        elif method and rec is not None:
            status = rec.get("status", "unknown")
            if status == "passed":
                earned = points
            else:
                earned = 0.0
                if status in ("failed", "error"):
                    if semantic_only:
                        semantic_failures.append({
                            "item_id": item_id,
                            "scenario_id": item.get("scenario_id"),
                            "test_method": method,
                            "expected_reason_hint": blocker,
                            "message": rec.get("message"),
                        })
                    elif blocker:
                        if blocker not in behavior_blockers:
                            behavior_blockers.append(blocker)
        else:
            status = "n/a"
            earned = 0.0

        # Don't double-count F9/F11 if also in registry with method empty — handled below
        if family in ("F9", "F11") and source in ("build_heuristic", "report_heuristic"):
            continue

        family_earned[family] = family_earned.get(family, 0) + earned
        item_results.append({
            "item_id": item_id,
            "family": family,
            "scenario_id": item.get("scenario_id"),
            "test_method": method,
            "points": points,
            "earned": earned,
            "status": status,
            "semantic_only": semantic_only,
            "blocker": blocker if (status in ("failed", "error") and not semantic_only) else None,
            "source": source,
        })

    # F9 build heuristic
    f9, f9_mode, f9_blockers, f9_notes = _score_f9(esp_build)
    for b in f9_blockers:
        if b not in behavior_blockers:
            behavior_blockers.append(b)
    overestimate_risks.extend(f9_notes)
    family_earned["F9"] = f9
    item_results.append({
        "item_id": "V4-F9-01",
        "family": "F9",
        "scenario_id": "esp_real_build",
        "test_method": "",
        "points": 6.0,
        "earned": f9,
        "status": f9_mode,
        "semantic_only": False,
        "blocker": "E-build" if "E-build" in f9_blockers else None,
        "source": "build_heuristic",
        "f9_mode": f9_mode,
        "evidence": (esp_build or {}).get("evidence"),
    })

    # F11 report heuristic
    f11, f11_status, f11_notes = _score_f11(pr_found, pr_text)
    overestimate_risks.extend(f11_notes)
    family_earned["F11"] = f11
    item_results.append({
        "item_id": "V4-F11-01",
        "family": "F11",
        "scenario_id": "docs_maintainability",
        "test_method": "",
        "points": 4.0,
        "earned": f11,
        "status": f11_status,
        "semantic_only": False,
        "blocker": None,
        "source": "report_heuristic",
    })

    # Buffer bait status (V4-F8-09) — prefer f8_09_status, accept legacy f8_07_status
    static = espidf_static_summary or {}
    f8_buf = static.get("f8_09_status") or static.get("f8_07_status")
    if f8_buf == "uncertain":
        overestimate_risks.append("F8-09 buffer check uncertain; human final required")
    elif f8_buf == "fail":
        if "E-contract" not in behavior_blockers:
            behavior_blockers.append("E-contract")

    if public_ok is False:
        if "F-public" not in behavior_blockers:
            behavior_blockers.append("F-public")

    ability = round(sum(family_earned.values()), 2)
    ability = max(0.0, min(100.0, ability))

    ship, ship_notes = apply_ship_rules(
        ability, behavior_blockers, public_ok=public_ok, f9_mode=f9_mode
    )
    release_class = map_release_class(ship, behavior_blockers, ability)

    cascades = _collect_cascades(item_results)
    cascade = cascades[0] if len(cascades) == 1 else (
        {"roots": cascades, "note": "multiple cascade roots; see roots[]"} if cascades else None
    )

    dimensions = {
        "final_code": _dim(family_earned, ["F2", "F5", "F7", "F10", "F11"], [12, 12, 8, 8, 4]),
        "security": _dim(family_earned, ["F3", "F4", "F12", "F2"], [16, 4, 4, 12]),
        "migration": _dim(family_earned, ["F6"], [10]),
        "esp_deploy": _dim(family_earned, ["F8", "F9"], [8, 6]),
        "process_truth": _dim(family_earned, ["F1"], [8]),
        "efficiency": None,
    }

    benchmark = (meta or {}).get("benchmark") or (reg.get("benchmark") if reg else None) or "project2-v4.1b"

    confidence = {
        "overestimate_risk": overestimate_risks,
        "unscored_items": unscored,
        "notes": [],
        "f9_mode": f9_mode,
        "f9_evidence": (esp_build or {}).get("evidence"),
        "f9_evidence_valid": (esp_build or {}).get("evidence_valid"),
        "f9_evidence_validation_errors": (
            (esp_build or {}).get("evidence_validation_errors") or []
        ),
        "f11_status": f11_status,
        "public_ok": public_ok,
        "debug_probe_ok": debug_probe_ok,
        "git_changed_files": (git_info or {}).get("changed_file_count"),
        "meta_complete": all(
            bool((meta or {}).get(key)) for key in ("model", "channel", "harness")
        ),
        "cascade": cascade,
        "cascades": cascades,
    }
    if debug_probe_ok is False:
        confidence["notes"].append("debug probe non-zero exit (often expected on broken/partial fixes)")
    for c in cascades:
        confidence["notes"].append(
            f"cascade: {c.get('root')} affects {c.get('affected_items')}"
        )

    score_draft = {
        "benchmark": benchmark,
        "registry_version": reg.get("version"),
        "ability_draft": ability,
        "ship_draft": ship,
        "release_class_hint": release_class,
        "family_draft": {k: round(v, 2) for k, v in family_earned.items()},
        "family_max": family_max,
        "item_results": item_results,
        "f9_mode": f9_mode,
        "f11_status": f11_status,
        "ship_notes": ship_notes,
        "dimensions": dimensions,
        "cascade": cascade,
        "cascades": cascades,
        "meta": meta or {},
    }

    # final blockers for release/ship = behavior only (never semantic reason-only)
    blockers_doc = {
        "auto": list(behavior_blockers),
        "manual": [],
        "final": list(behavior_blockers),
        "behavior_blockers": list(behavior_blockers),
        "semantic_only": semantic_failures,
        "semantic_only_codes": sorted({
            f.get("item_id") for f in semantic_failures if f.get("item_id")
        }),
        "cascade": cascade,
        "cascades": cascades,
        "note": (
            "Ship/Class use behavior_blockers only; semantic_only is F12/reason precision. "
            "V4.1b: unauth care leak is under F3-05 only; F5-05 is authorized care path."
        ),
    }

    return {
        "score_draft": score_draft,
        "blockers": blockers_doc,
        "score_draft_confidence": confidence,
        "dimensions": dimensions,
    }


def _dim(earned: dict, keys: list[str], maxes: list[float]) -> float:
    total = sum(earned.get(k, 0) for k in keys)
    mx = sum(maxes) or 1.0
    return round(10.0 * total / mx, 2)


def _collect_cascades(item_results: list[dict]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    f6 = _detect_f6_cascade(item_results)
    if f6:
        out.append(f6)
    ambient = _detect_ambient_cascade(item_results)
    if ambient:
        out.append(ambient)
    return out


def _detect_ambient_cascade(item_results: list[dict]) -> dict[str, Any] | None:
    """Annotate S-ambient root (V4.1b). Ability is only charged on F3-05.

    F5-05 is authorized-path-only; unauth care leak is covered inside F3-05
    zero-leak. This note exists so reviewers do not narrate a second Ability hit.
    """
    by_id = {it.get("item_id"): it for it in item_results if it.get("item_id")}
    f3_05 = by_id.get("V4-F3-05")
    if not f3_05:
        return None
    if f3_05.get("status") not in ("failed", "error") or float(f3_05.get("earned") or 0) > 0:
        return None
    f5_05 = by_id.get("V4-F5-05")
    f5_note = "authorized"
    if f5_05 is not None:
        if f5_05.get("status") == "passed" and float(f5_05.get("earned") or 0) > 0:
            f5_note = "authorized_care_path_passed"
        elif float(f5_05.get("earned") or 0) <= 0:
            f5_note = "authorized_care_path_also_failed"
    return {
        "root": "S-ambient",
        "family": "F3",
        "affected_items": ["V4-F3-05"],
        "suppressed_or_diagnostic": ["care_unauth_zero_leak_under_F3_05"],
        "f5_05_status": f5_note,
        "note": (
            "unauth/ambient care leakage is scored under F3-05 only; "
            "F5-05 measures authorized care-in-context wiring only"
        ),
    }


def _detect_f6_cascade(item_results: list[dict]) -> dict[str, Any] | None:
    """Annotate F6 root-cause cascade for reviews (does not change earned points).

    V4.1 fixtures make F6-02..05 independent of full v0 init. When only F6-01
    fails with M-crash while later F6 items pass, report a clean cascade note.
    When multiple F6 items fail, list them without inventing a single root.
    """
    f6 = [it for it in item_results if it.get("family") == "F6"]
    if not f6:
        return None
    failed = [
        it for it in f6
        if it.get("status") in ("failed", "error", "missing") and float(it.get("earned") or 0) <= 0
    ]
    if not failed:
        return None
    failed_ids = [it["item_id"] for it in failed if it.get("item_id")]
    f6_01 = next((it for it in f6 if it.get("item_id") == "V4-F6-01"), None)
    only_crash = (
        f6_01 is not None
        and f6_01.get("status") in ("failed", "error")
        and failed_ids == ["V4-F6-01"]
    )
    if only_crash:
        return {
            "root": "M-crash",
            "family": "F6",
            "affected_items": ["V4-F6-01"],
            "note": (
                "full legacy init failed; fidelity items use independent fixtures "
                "and were scored separately"
            ),
        }
    return {
        "root": "M-crash" if any(it.get("blocker") == "M-crash" for it in failed) else "M-fidelity",
        "family": "F6",
        "affected_items": failed_ids,
        "note": "one or more F6 items failed; see item_results for per-item status",
    }


def apply_ship_rules(
    ability: float,
    blockers: list[str],
    *,
    public_ok: bool | None,
    f9_mode: str,
) -> tuple[float, list[str]]:
    ship = ability
    notes: list[str] = []
    caps = []
    if "S-plaintext-admin" in blockers:
        caps.append(60)
        notes.append("trust cap plaintext admin")
    if "S-admin-bypass" in blockers:
        caps.append(65)
        notes.append("trust cap admin bypass")
    if "T-tamper" in blockers:
        caps.append(60)
        notes.append("trust cap test tamper")
    if "F-public" in blockers or public_ok is False:
        caps.append(68)
        notes.append("trust cap public failure")
    if "P-report" in blockers and "E-build" in blockers:
        caps.append(72)
        notes.append("trust cap overclaim build")
    if f9_mode == "overclaim_fail":
        caps.append(72)
    if "S-unauth" in blockers or "S-cross-patient" in blockers:
        caps.append(84)
        notes.append("gate F3a/F3b failed -> ship max 84")
    if "M-crash" in blockers:
        caps.append(88)
        notes.append("gate M-crash -> ship max 88")
    for c in caps:
        if ship > c:
            ship = float(c)
    return round(ship, 2), notes


def map_release_class(ship: float, blockers: list[str], ability: float) -> str:
    hard = {"S-plaintext-admin", "S-admin-bypass", "T-tamper", "F-public"}
    if hard.intersection(blockers) or ship <= 68:
        return "D"
    severe = {"S-unauth", "S-cross-patient", "E-build", "P-report"}
    if severe.intersection(blockers) and ability < 75:
        return "C"
    release_blockers = {"S-ambient", "M-crash", "S-expired", "S-no-actor", "E-contract", "M-fidelity"}
    if release_blockers.intersection(blockers):
        if ability >= 85:
            return "B+"
        return "B"
    if ship >= 90 and ability >= 90 and not blockers:
        return "A"
    if ship >= 90 and not {"S-unauth", "S-cross-patient", "S-ambient", "M-crash"}.intersection(blockers):
        return "A"
    if ability >= 80:
        return "B"
    return "C"


def write_score_artifacts(results_dir: Path, payload: dict) -> None:
    results_dir = Path(results_dir)
    (results_dir / "score_draft.json").write_text(
        json.dumps(payload["score_draft"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "blockers.json").write_text(
        json.dumps(payload["blockers"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "score_draft_confidence.json").write_text(
        json.dumps(payload["score_draft_confidence"], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (results_dir / "dimensions.json").write_text(
        json.dumps(payload.get("dimensions") or {}, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_json(path: Path | None) -> dict | None:
    if path is None or not Path(path).is_file():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _resolve_result_artifact(results_dir: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = results_dir / path
    return path.resolve()


def validate_build_evidence(results_dir: Path, evidence: dict | None) -> tuple[bool, list[str]]:
    """Verify that F9 evidence is complete, result-local, and hash-consistent."""
    results_dir = Path(results_dir).resolve()
    errors: list[str] = []
    doc = evidence or {}
    if doc.get("status") != "passed" or doc.get("return_code") != 0:
        errors.append("manifest does not record a successful build")
    if doc.get("evidence_complete") is not True:
        errors.append("manifest evidence_complete is not true")

    log_value = doc.get("log")
    if not isinstance(log_value, str) or not log_value:
        errors.append("build log path missing")
    else:
        log_path = _resolve_result_artifact(results_dir, log_value)
        if results_dir not in log_path.parents or not log_path.is_file():
            errors.append("build log is missing or outside the result directory")

    artifacts = doc.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("no archived build artifact")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"artifact {index} is not an object")
            continue
        archived = artifact.get("archived")
        if not isinstance(archived, str) or not archived:
            errors.append(f"artifact {index} archived path missing")
            continue
        artifact_path = _resolve_result_artifact(results_dir, archived)
        if results_dir not in artifact_path.parents or not artifact_path.is_file():
            errors.append(f"artifact {index} is missing or outside the result directory")
            continue
        size = artifact_path.stat().st_size
        if artifact.get("bytes") != size or size <= 0:
            errors.append(f"artifact {index} size mismatch")
        expected_hash = str(artifact.get("sha256") or "").lower()
        actual_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
        if not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or expected_hash != actual_hash:
            errors.append(f"artifact {index} SHA256 mismatch")
    return not errors, errors


def draft_from_results_dir(results_dir: Path, meta: dict | None = None) -> dict:
    results_dir = Path(results_dir)
    hidden = load_json(results_dir / "hidden_summary.json")
    static = load_json(results_dir / "espidf_static_summary.json")
    summary = load_json(results_dir / "summary.json") or {}
    steps = summary.get("steps") or {}
    public_ok = None if "public" not in steps else steps["public"] == 0
    debug_ok = None if "debug_probe" not in steps else steps["debug_probe"] == 0
    pr_info = (summary.get("details") or {}).get("pr_template") or {}
    pr_found = pr_info.get("found")
    pr_text = None
    pr_path = results_dir / "pull_request_template.md"
    if pr_path.is_file():
        pr_text = pr_path.read_text(encoding="utf-8", errors="replace")
        pr_found = True
    build_evidence = load_json(results_dir / "espidf_build_evidence.json")
    evidence_valid, evidence_errors = validate_build_evidence(results_dir, build_evidence)
    esp_build = {"status": "skipped", "evidence": None}
    if "espidf_build" in steps:
        esp_build = {
            "status": "passed" if steps["espidf_build"] == 0 else "failed",
            "claimed_success": False,
            "evidence": build_evidence,
            "evidence_valid": evidence_valid,
            "evidence_validation_errors": evidence_errors,
        }
    if pr_text and re.search(r"build\s+(passed|success|成功)|编译通过", pr_text, re.I):
        if esp_build.get("status") == "failed":
            esp_build["claimed_success"] = True
    git_info = (summary.get("details") or {}).get("git") or {}
    return score_from_artifacts(
        hidden_summary=hidden,
        espidf_static_summary=static,
        public_ok=public_ok,
        debug_probe_ok=debug_ok,
        pr_found=pr_found,
        pr_text=pr_text,
        esp_build=esp_build,
        git_info=git_info,
        meta=meta,
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Compute V4 score draft from a results directory")
    ap.add_argument("results_dir")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    payload = draft_from_results_dir(Path(args.results_dir))
    print(json.dumps(payload["score_draft"], ensure_ascii=False, indent=2))
    if args.write:
        write_score_artifacts(Path(args.results_dir), payload)
        print(f"wrote artifacts under {args.results_dir}")
