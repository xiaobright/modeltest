from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        data = path.read_bytes()
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def command(*args: str, cwd: Path | None = None) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True, encoding="utf-8").strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repository = args.repository.resolve()
    dsh_home = Path(os.environ.get("DSH_HOME", Path.home() / ".dsh"))
    dsh_package = dsh_home / "profiles" / "node_modules" / "@deepseek-ai" / "dsh"
    package = json.loads((dsh_package / "package.json").read_text(encoding="utf-8"))
    preset_roots = {
        "standard": dsh_package / "config" / "agent-presets" / "standard",
        "minimal-full": repository / "tools" / "deepseek-harness-presets" / "minimal-full",
        "anchored-standard": repository / "tools" / "deepseek-harness-presets" / "anchored-standard",
    }
    status_paths = []
    for line in command("git", "status", "--porcelain=v1", cwd=repository).splitlines():
        if line:
            status_paths.append(line[3:].replace("\\", "/"))
    payload = {
        "schema_version": 1,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "modeltest_head": command("git", "rev-parse", "HEAD", cwd=repository),
        "modeltest_status_paths": status_paths,
        "dsh_package": package.get("name"),
        "dsh_version": package.get("version"),
        "dsh_source_commit_preregistered": "47f943859bef60e4160492346772ded9b24f765a",
        "preset_hash_algorithm": "SHA-256 over sorted (UTF-8 relative path length/path, file length/bytes)",
        "preset_hashes": {name: tree_hash(root) for name, root in preset_roots.items()},
        "environment": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "node": command("node", "--version"),
            "powershell": os.environ.get("POWERSHELL_DISTRIBUTION_CHANNEL", "Windows PowerShell host"),
            "processor_architecture": platform.machine(),
        },
    }
    if payload["dsh_version"] != "0.1.0-rc.6":
        raise RuntimeError(f"DSH 版本漂移：{payload['dsh_version']}")
    if payload["modeltest_head"] != "04255b55f16c4439e538239fb9783070c4165081":
        raise RuntimeError(f"modeltest HEAD 漂移：{payload['modeltest_head']}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dsh_version": payload["dsh_version"], "preset_hashes": payload["preset_hashes"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
