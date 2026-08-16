from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def request_fingerprint(request: dict) -> dict:
    tools = request.get("tools", [])
    return {
        "system_sha256": hashlib.sha256(canonical(request.get("messages", [])[0])).hexdigest(),
        "tool_names": [item.get("function", {}).get("name") for item in tools],
        "tools_sha256": hashlib.sha256(canonical(tools)).hexdigest(),
        "non_tools_sha256": hashlib.sha256(canonical({key: value for key, value in request.items() if key != "tools"})).hexdigest(),
    }


def load(path: Path) -> list[dict]:
    value = json.loads(path.read_text(encoding="utf-8"))
    agent_requests = [item for item in value if item.get("tools")]
    if not isinstance(value, list) or len(agent_requests) < 2:
        raise ValueError(f"{path} 至少需要两次携带工具目录的 mock agent request")
    return agent_requests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standard", type=Path, required=True)
    parser.add_argument("--minimal-full", type=Path, required=True)
    parser.add_argument("--anchored", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    standard = load(args.standard)
    minimal = load(args.minimal_full)
    anchored = load(args.anchored)
    snapshots = {
        "standard": [request_fingerprint(item) for item in standard],
        "minimal-full": [request_fingerprint(item) for item in minimal],
        "anchored-standard": [request_fingerprint(item) for item in anchored],
    }
    full_names = snapshots["standard"][0]["tool_names"]
    assertions = {
        "standard_first_is_full": len(full_names) > 2,
        "minimal_first_equals_anchored_second_tools": snapshots["minimal-full"][0]["tools_sha256"] == snapshots["anchored-standard"][1]["tools_sha256"],
        "minimal_first_equals_standard_first_tools": snapshots["minimal-full"][0]["tools_sha256"] == snapshots["standard"][0]["tools_sha256"],
        "minimal_and_anchored_system_equal": snapshots["minimal-full"][0]["system_sha256"] == snapshots["anchored-standard"][0]["system_sha256"],
        "minimal_and_anchored_first_non_tools_equal": snapshots["minimal-full"][0]["non_tools_sha256"] == snapshots["anchored-standard"][0]["non_tools_sha256"],
        "anchored_first_is_shell_read": set(snapshots["anchored-standard"][0]["tool_names"]) in ({"pwsh", "read"}, {"bash", "read"}),
        "anchored_second_is_full": snapshots["anchored-standard"][1]["tool_names"] == full_names,
    }
    result = {"schema_version": 1, "passed": all(assertions.values()), "assertions": assertions, "snapshots": snapshots}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "assertions": assertions}, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
