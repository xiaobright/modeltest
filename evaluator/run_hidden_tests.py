#!/usr/bin/env python3
import argparse
import importlib.util
import json
import os
import sys
import traceback
import unittest
from pathlib import Path


FAMILY_BY_FILE = {
    "test_pr_template_contract.py": "process_reporting",
    "test_api_regression.py": "regression",
    "test_auth_boundary.py": "admin_auth",
    "test_care_event.py": "care_event",
    "test_context_policy.py": "context_policy",
    "test_sleep_import.py": "sleep_import",
    "test_db_migration.py": "db_migration",
    "test_process_contract.py": "process_reporting",
    "test_voice_bridge.py": "voice_bridge",
}


def load_registry() -> dict:
    path = Path(__file__).resolve().parent / "scoring" / "item_registry.json"
    if not path.is_file():
        return {"items": []}
    return json.loads(path.read_text(encoding="utf-8"))


def registry_by_method(registry: dict) -> dict:
    out = {}
    for item in registry.get("items") or []:
        method = item.get("test_method")
        if method:
            out.setdefault(method, []).append(item)
    return out


class RecordingTextResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    @staticmethod
    def _short_message(text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in reversed(lines):
            if line.startswith((
                "AssertionError:",
                "AttributeError:",
                "ImportError:",
                "KeyError:",
                "ModuleNotFoundError:",
                "RuntimeError:",
                "TypeError:",
                "ValueError:",
            )):
                return line
        return lines[-1] if lines else ""

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"test": test.id(), "status": "passed"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({
            "test": test.id(),
            "status": "failed",
            "message": self._short_message(self._exc_info_to_string(err, test)),
        })

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({
            "test": test.id(),
            "status": "error",
            "message": self._short_message(self._exc_info_to_string(err, test)),
        })

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"test": test.id(), "status": "skipped", "message": reason})


def annotate_records(records: list, by_method: dict) -> list:
    annotated = []
    for rec in records:
        method = rec.get("test", "").rsplit(".", 1)[-1]
        items = by_method.get(method) or []
        entry = dict(rec)
        if items:
            entry["items"] = [
                {
                    "item_id": it["item_id"],
                    "family": it.get("family"),
                    "scenario_id": it.get("scenario_id"),
                    "points": it.get("points"),
                    "semantic_only": bool(it.get("semantic_only")),
                    "blocker": it.get("blocker") if not it.get("semantic_only") else None,
                }
                for it in items
            ]
            # primary mapping for convenience
            primary = items[0]
            entry["item_id"] = primary.get("item_id")
            entry["family"] = primary.get("family")
            entry["scenario_id"] = primary.get("scenario_id")
            entry["points"] = primary.get("points")
            entry["semantic_only"] = bool(primary.get("semantic_only"))
            if rec.get("status") in ("failed", "error") and not primary.get("semantic_only"):
                entry["blocker"] = primary.get("blocker")
            else:
                entry["blocker"] = None
        annotated.append(entry)
    return annotated


def run_test_file(test_file: Path, index: int, by_method: dict) -> dict:
    module_name = f"_project2_hidden_{index}_{test_file.stem}"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, test_file)
    if spec is None or spec.loader is None:
        return {
            "file": test_file.name,
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "records": [{"test": test_file.name, "status": "error", "message": "unable to load spec"}],
        }
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        return {
            "file": test_file.name,
            "tests_run": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "skipped": 0,
            "records": [{
                "test": test_file.name,
                "status": "error",
                "message": RecordingTextResult._short_message(traceback.format_exc()),
            }],
        }
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=2, resultclass=RecordingTextResult)
    result = runner.run(suite)
    records = annotate_records(result.records, by_method)
    return {
        "file": test_file.name,
        "tests_run": result.testsRun,
        "passed": sum(1 for r in records if r["status"] == "passed"),
        "failed": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", nargs="?", default="")
    parser.add_argument("--summary-json", type=Path, default=None)
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    project = Path(args.project).resolve() if args.project else here.parent / "workspace" / "project2_task"
    if not project.exists():
        print(f"[hidden] project not found: {project}")
        return 2

    os.environ["PROJECT_DIR"] = str(project)
    os.environ["PYTHONWARNINGS"] = "ignore::ResourceWarning"

    registry = load_registry()
    by_method = registry_by_method(registry)

    hidden_dir = here / "tests" / "hidden"
    if str(hidden_dir) not in sys.path:
        sys.path.insert(0, str(hidden_dir))

    summary = {
        "kind": "hidden",
        "benchmark": "project2-v4.1b",
        "project": str(project),
        "files": [],
        "tests_run": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
    }

    for index, test_file in enumerate(sorted(hidden_dir.glob("test_*.py")), start=1):
        print(f"\n[hidden] running {test_file.name}")
        file_summary = run_test_file(test_file, index, by_method)
        file_summary["family"] = FAMILY_BY_FILE.get(test_file.name, test_file.stem)
        summary["files"].append(file_summary)
        for key in ("tests_run", "passed", "failed", "errors", "skipped"):
            summary[key] += file_summary[key]

    families = {}
    for file_summary in summary["files"]:
        family = file_summary.get("family", "unknown")
        bucket = families.setdefault(
            family,
            {"tests_run": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0},
        )
        for key in ("tests_run", "passed", "failed", "errors", "skipped"):
            bucket[key] += file_summary[key]
    summary["families"] = families

    # effective blockers (behavior only)
    blockers = []
    for file_summary in summary["files"]:
        for rec in file_summary.get("records") or []:
            if rec.get("status") in ("failed", "error") and rec.get("blocker"):
                if rec["blocker"] not in blockers:
                    blockers.append(rec["blocker"])
    summary["blockers"] = blockers
    summary["ship_gates"] = {
        "S-ambient_present": "S-ambient" in blockers,
        "note": "S-ambient does not set a numeric ship ceiling in V4",
    }

    if args.summary_json is not None:
        args.summary_json.parent.mkdir(parents=True, exist_ok=True)
        args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[hidden] summary={args.summary_json}")

    if summary["failed"] or summary["errors"]:
        print(f"\n[hidden] failed={summary['failed']} errors={summary['errors']} passed={summary['passed']}/{summary['tests_run']}")
        return 1
    print(f"\n[hidden] all hidden tests passed ({summary['passed']}/{summary['tests_run']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
