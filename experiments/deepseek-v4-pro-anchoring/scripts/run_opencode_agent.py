from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BALANCE_URL = "https://api.deepseek.com/user/balance"
MODEL_ID = "deepseek/deepseek-v4-pro"
ENDPOINT = "https://api.deepseek.com"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def credential() -> str:
    value = os.environ.get("DEEPSEEK_API_KEY")
    if value:
        return value
    path = Path(os.environ.get("DSH_HOME", Path.home() / ".dsh")) / ".credentials.yaml"
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DEEPSEEK_API_KEY:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    raise RuntimeError("未找到 DSH DeepSeek credential")


def cny_balance(api_key: str) -> tuple[float, bytes]:
    request = urllib.request.Request(
        BALANCE_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "modeltest-opencode-project2/1",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8"))
    if not payload.get("is_available"):
        raise RuntimeError("DeepSeek balance endpoint 报告账户不可用")
    total = sum(
        float(item["total_balance"])
        for item in payload.get("balance_infos", [])
        if item.get("currency") == "CNY"
    )
    return total, raw


def total_from_snapshot(path: Path) -> float:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return sum(
        float(item["total_balance"])
        for item in payload.get("balance_infos", [])
        if item.get("currency") == "CNY"
    )


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        process.kill()


def parse_session_id(events: Path) -> str:
    for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = event.get("sessionID")
        if isinstance(session_id, str) and session_id:
            return session_id
    raise RuntimeError("OpenCode JSON event stream 中缺少 sessionID")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--private-run", type=Path, required=True)
    parser.add_argument("--models-catalog", type=Path, required=True)
    parser.add_argument("--t0-balance", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=4500)
    parser.add_argument("--cost-stop-cny", type=float, default=3.75)
    parser.add_argument("--balance-poll-seconds", type=int, default=60)
    args = parser.parse_args()

    args.workspace = args.workspace.resolve()
    args.prompt = args.prompt.resolve()
    args.private_run = args.private_run.resolve()
    args.models_catalog = args.models_catalog.resolve()
    args.t0_balance = args.t0_balance.resolve()
    args.private_run.mkdir(parents=True, exist_ok=False)

    api_key = credential()
    t0 = total_from_snapshot(args.t0_balance)
    isolation = args.private_run / "isolation"
    isolation.mkdir(parents=True)
    events_path = args.private_run / "events.jsonl"
    stderr_path = args.private_run / "stderr.log"
    export_path = args.private_run / "session-export.json"
    balance_log_path = args.private_run / "balance-monitor.json"
    meta_path = args.private_run / "run-meta.json"

    executable = shutil.which("opencode.exe") or shutil.which("opencode.cmd") or shutil.which("opencode")
    if not executable:
        raise RuntimeError("PATH 中未找到 OpenCode executable")

    env = os.environ.copy()
    env.update(
        {
            "DEEPSEEK_API_KEY": api_key,
            "OPENCODE_TEST_HOME": str(isolation / "home"),
            "XDG_CONFIG_HOME": str(isolation / "config"),
            "XDG_DATA_HOME": str(isolation / "data"),
            "XDG_STATE_HOME": str(isolation / "state"),
            "XDG_CACHE_HOME": str(isolation / "cache"),
            "OPENCODE_AUTH_CONTENT": "{}",
            "OPENCODE_CONFIG_CONTENT": json.dumps(
                {
                    "share": "disabled",
                    "autoupdate": False,
                    "provider": {"deepseek": {"options": {"baseURL": ENDPOINT}}},
                },
                separators=(",", ":"),
            ),
            "OPENCODE_MODELS_PATH": str(args.models_catalog),
            "OPENCODE_DISABLE_MODELS_FETCH": "1",
            "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
            "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
            "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
            "OPENCODE_DISABLE_CLAUDE_CODE": "1",
            "OPENCODE_PURE": "1",
        }
    )

    command = [
        executable,
        "run",
        "--pure",
        "--model",
        MODEL_ID,
        "--variant",
        "max",
        "--thinking",
        "--format",
        "json",
        "--dir",
        str(args.workspace),
        "--agent",
        "build",
        "--auto",
        "--title",
        args.run_id,
    ]
    started = utc_now()
    started_monotonic = time.monotonic()
    observations: list[dict[str, Any]] = []
    stop_reason: str | None = None
    last_balance_poll = -float("inf")
    last_progress = -float("inf")

    print(
        json.dumps(
            {
                "stage": "opencode_agent_start",
                "run_id": args.run_id,
                "model": MODEL_ID,
                "reasoning_variant": "max",
                "endpoint": ENDPOINT,
                "timeout_seconds": args.timeout_seconds,
                "cost_stop_cny": args.cost_stop_cny,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    with (
        args.prompt.open("rb") as prompt_stream,
        events_path.open("wb") as events_stream,
        stderr_path.open("wb") as stderr_stream,
    ):
        process = subprocess.Popen(
            command,
            cwd=args.workspace,
            env=env,
            stdin=prompt_stream,
            stdout=events_stream,
            stderr=stderr_stream,
        )
        while process.poll() is None:
            elapsed = time.monotonic() - started_monotonic
            if elapsed >= args.timeout_seconds:
                stop_reason = "wall_timeout"
                terminate_tree(process)
                break
            if elapsed - last_balance_poll >= args.balance_poll_seconds:
                last_balance_poll = elapsed
                try:
                    current, raw = cny_balance(api_key)
                    observation_path = args.private_run / f"balance-{len(observations):03d}.json"
                    observation_path.write_bytes(raw)
                    delta = round(t0 - current, 6)
                    observations.append(
                        {
                            "retrieved_at_utc": utc_now(),
                            "observed_delta_cny": delta,
                            "private_snapshot": observation_path.name,
                        }
                    )
                    if delta >= args.cost_stop_cny:
                        stop_reason = "observed_cost_stop"
                        terminate_tree(process)
                        break
                except Exception as error:
                    observations.append(
                        {
                            "retrieved_at_utc": utc_now(),
                            "balance_poll_error": type(error).__name__,
                        }
                    )
            if elapsed - last_progress >= 30:
                last_progress = elapsed
                recent_delta = observations[-1].get("observed_delta_cny") if observations else None
                print(
                    json.dumps(
                        {
                            "stage": "opencode_agent_running",
                            "elapsed_seconds": round(elapsed, 1),
                            "latest_observed_delta_cny": recent_delta,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
            time.sleep(5)
        exit_code = process.wait()

    ended = utc_now()
    duration = round(time.monotonic() - started_monotonic, 3)
    balance_log_path.write_text(json.dumps(observations, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    session_id = parse_session_id(events_path)

    export_command = [executable, "export", session_id]
    with export_path.open("wb") as export_stream, stderr_path.open("ab") as stderr_stream:
        export_result = subprocess.run(
            export_command,
            cwd=args.workspace,
            env=env,
            stdout=export_stream,
            stderr=stderr_stream,
            timeout=120,
            check=False,
        )

    meta = {
        "schema_version": 1,
        "run_id": args.run_id,
        "started_at_utc": started,
        "ended_at_utc": ended,
        "wall_time_seconds": duration,
        "opencode_exit_code": exit_code,
        "export_exit_code": export_result.returncode,
        "session_id": session_id,
        "model": MODEL_ID,
        "provider": "deepseek",
        "resolved_endpoint": ENDPOINT,
        "reasoning_variant": "max",
        "thinking_export_enabled": True,
        "agent": "build",
        "pure": True,
        "auto_approve": True,
        "cost_stop_cny": args.cost_stop_cny,
        "stop_reason": stop_reason,
        "workspace": str(args.workspace),
        "models_catalog": str(args.models_catalog),
        "events": str(events_path),
        "session_export": str(export_path),
        "balance_monitor": str(balance_log_path),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "stage": "opencode_agent_complete",
                "run_id": args.run_id,
                "exit_code": exit_code,
                "export_exit_code": export_result.returncode,
                "wall_time_seconds": duration,
                "stop_reason": stop_reason,
                "session_id_recorded_private": True,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    if export_result.returncode != 0:
        return 3
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
