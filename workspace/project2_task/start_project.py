#!/usr/bin/env python3
import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="One-click starter for gateway + voice + posture worker + vision worker")
    p.add_argument("--target", choices=["all", "gateway", "voice"], default="all", help="Which services to run")
    p.add_argument("--voice-input", choices=["mic", "text"], default="text", help="Voice input mode")
    p.add_argument("--with-posture", action="store_true", help="Start posture classification worker (multi-bed)")
    p.add_argument("--posture-poll-interval", type=float, default=2.0, help="Posture worker poll interval in seconds")
    p.add_argument("--with-vision", action="store_true", help="Start vision/emotion worker")
    p.add_argument("--vision-source", choices=["mock", "camera", "auto"], default="mock", help="Vision source mode")
    p.add_argument("--vision-interval", type=float, default=1.0, help="Vision worker poll interval in seconds")
    p.add_argument("--vision-camera-index", type=int, default=0, help="Camera index for vision worker")
    p.add_argument("--vision-mock-label", default="自然", help="Default mock emotion label when no camera is used")
    p.add_argument("--vision-identity", choices=["on", "off"], default="on", help="Enable vision face identity session updates")
    p.add_argument("--vision-mock-subject-id", default="", help="Subject ID used by mock vision identity")
    p.add_argument("--voice-room", type=str, default="R1203", help="Voice assistant room ID")
    p.add_argument("--voice-bed", type=str, default="B1", help="Voice assistant bed ID")
    p.add_argument("--voice-session-id", type=str, default="", help="Optional gateway session ID for voice context")
    p.add_argument("--voice-subject-id", type=str, default="", help="Optional target subject ID for voice context")
    return p.parse_args()


def run_once(cmd, cwd, env):
    print(f"[BOOT] run once: {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=str(cwd), env=env, check=False)


def start_proc(name, cmd, cwd, env, procs):
    print(f"[BOOT] start {name}: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, cwd=str(cwd), env=env)
    procs.append((name, proc))


def stop_all(procs):
    for name, proc in procs:
        if proc.poll() is None:
            print(f"[BOOT] stopping {name} (pid={proc.pid})")
            proc.terminate()
    deadline = time.time() + 5
    for _, proc in procs:
        if proc.poll() is None:
            try:
                proc.wait(timeout=max(0.1, deadline - time.time()))
            except subprocess.TimeoutExpired:
                proc.kill()


def main():
    args = parse_args()
    base = Path(__file__).resolve().parent
    py = sys.executable

    gateway_py = base / "gateway" / "gateway.py"
    voice_py = base / "voice" / "voice_assistant_integrated.py"
    posture_py = base / "posture" / "posture_worker.py"
    vision_py = base / "vision" / "vision_worker.py"

    env = os.environ.copy()
    env["VOICE_INPUT_MODE"] = args.voice_input
    env["VOICE_ROOM"] = args.voice_room
    env["VOICE_BED"] = args.voice_bed
    if args.voice_session_id:
        env["VOICE_SESSION_ID"] = args.voice_session_id
    if args.voice_subject_id:
        env["VOICE_TARGET_SUBJECT_ID"] = args.voice_subject_id
    if args.with_posture:
        env["POSTURE_POLL_INTERVAL_S"] = str(args.posture_poll_interval)
    if args.with_vision:
        env["VISION_SOURCE"] = args.vision_source
        env["VISION_INTERVAL_S"] = str(args.vision_interval)
        env["VISION_CAMERA_INDEX"] = str(args.vision_camera_index)
        env["VISION_MOCK_LABEL"] = args.vision_mock_label
        env["VISION_IDENTITY_ENABLED"] = "1" if args.vision_identity == "on" else "0"
        if args.vision_mock_subject_id:
            env["VISION_MOCK_SUBJECT_ID"] = args.vision_mock_subject_id

    procs = []

    if args.target in ("all", "gateway"):
        start_proc("gateway", [py, str(gateway_py)], cwd=base, env=env, procs=procs)

    if args.target in ("all", "voice"):
        start_proc("voice", [py, str(voice_py)], cwd=base, env=env, procs=procs)

    if args.with_posture:
        start_proc("posture", [py, str(posture_py)], cwd=base, env=env, procs=procs)

    if args.with_vision:
        start_proc("vision", [py, str(vision_py)], cwd=base, env=env, procs=procs)

    if not procs:
        print("[BOOT] no long-running process started")
        return 0

    print("[BOOT] services running, press Ctrl+C to stop")

    def _sig_handler(signum, frame):
        del signum, frame
        raise KeyboardInterrupt()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    try:
        while True:
            for name, proc in procs:
                code = proc.poll()
                if code is not None:
                    print(f"[BOOT] {name} exited with code={code}, stopping others")
                    stop_all(procs)
                    return code
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[BOOT] interrupt received")
        stop_all(procs)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
