#!/usr/bin/env python3
"""Visible Project2 diagnostic probe for local development self-check.

This is a pre-flight self-check tool. It runs local diagnostics to help developers
identify issues in database APIs, session management, and auth configurations before PR submission.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


ADMIN_PASSWORD = "DebugProbe-Pass-2026"


def configure_env(tmp: Path) -> None:
    os.environ["PROJECT2_DB_FILE"] = str(tmp / "project2_debug_probe.db")
    os.environ["PROJECT2_DATA_DIR"] = str(tmp)
    os.environ["BEDS_CONFIG"] = '{"beds":[["R1203","B1"],["R1203","B2"],["R1204","B1"]]}'
    os.environ["SLEEP_IMPORT_ENABLED"] = "0"
    os.environ["SLEEP_IMPORT_UNSCOPED_POLICY"] = "first"
    os.environ.pop("SLEEP_IMPORT_DEFAULT_ROOM", None)
    os.environ.pop("SLEEP_IMPORT_DEFAULT_BED", None)
    os.environ["BEMFA_UID"] = ""
    os.environ["ADMIN_AUTH_ENABLED"] = "1"
    os.environ["SESSION_TTL_MS"] = "120000"
    os.environ["ADMIN_SESSION_TTL_MS"] = str(8 * 60 * 60 * 1000)


def reset_modules() -> None:
    for name in [
        "config",
        "bed_config",
        "utils",
        "db",
        "auth",
        "subjects",
        "sensor_store",
        "esp_store",
        "sleep_importer",
        "care_events",
        "gateway",
    ]:
        sys.modules.pop(name, None)


def request_json(base_url: str, method: str, path: str, body=None, cookie: str = ""):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read()
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
            return resp.status, parsed, resp.headers
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            parsed = {"raw": raw.decode("utf-8", errors="replace")}
        return exc.code, parsed, exc.headers


def cookie_from(headers) -> str:
    cookie = headers.get("Set-Cookie", "")
    return cookie.split(";", 1)[0] if cookie else ""


class Probe:
    def __init__(self, project: Path):
        self.project = project.resolve()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self.tmpdir.name)
        configure_env(self.tmp)
        gateway_dir = str(self.project / "gateway")
        if gateway_dir not in sys.path:
            sys.path.insert(0, gateway_dir)
        reset_modules()
        self.gw = importlib.import_module("gateway")
        self.gw.init_management_db()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.gw.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        self.failures: list[str] = []

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)
        self.tmpdir.cleanup()

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            print(f"[probe:ok] {name}")
        else:
            print(f"[probe:FAIL] {name} {detail}".rstrip())
            self.failures.append(name)

    def setup_admin(self) -> str:
        status, data, headers = request_json(
            self.base_url,
            "POST",
            "/api/v3/admin/setup",
            {
                "username": "admin",
                "display_name": "Admin",
                "password": ADMIN_PASSWORD,
                "password_confirm": ADMIN_PASSWORD,
            },
        )
        self.check("admin setup returns 200", status == 200, f"status={status} data={data}")
        return cookie_from(headers)

    def run_auth_probe(self) -> None:
        cookie = self.setup_admin()
        cookie_name = cookie.split("=", 1)[0] if cookie else "project2_admin_session"
        status, data, _ = request_json(self.base_url, "GET", "/api/v3/subjects")
        self.check("management API rejects missing cookie", status == 401, f"status={status} data={data}")
        status, data, _ = request_json(
            self.base_url,
            "GET",
            "/api/v3/subjects",
            cookie=f"{cookie_name}=not-a-real-token",
        )
        self.check("management API rejects forged cookie", status == 401, f"status={status} data={data}")
        status, data, _ = request_json(self.base_url, "GET", "/api/v3/subjects", cookie=cookie)
        self.check("management API accepts valid cookie", status == 200, f"status={status} data={data}")

    def run_context_probe(self) -> None:
        now_ms = self.gw.now_ms
        self.gw.create_subject({"subject_id": "sub_staff_probe", "name": "Probe Staff", "role": "staff"})
        self.gw.create_subject({"subject_id": "sub_patient_probe", "name": "Probe Patient", "role": "patient"})
        self.gw.create_assignment({
            "assignment_id": "assign_probe",
            "subject_id": "sub_patient_probe",
            "room": "R1203",
            "bed": "B1",
        })
        self.gw.create_memory({
            "memory_id": "mem_probe",
            "subject_id": "sub_patient_probe",
            "kind": "care_preference",
            "content_compressed": "Probe Patient needs quiet night rounds.",
        })
        self.gw.upsert_session({
            "session_id": "sess_unknown_probe",
            "actor_subject_id": "sub_staff_probe",
            "identity_state": "unknown",
            "assurance_level": "medium",
            "auth_methods": [],
            "expires_ts": now_ms() + 60000,
        })
        ctx = self.gw.build_chat_context_v3({
            "session_id": ["sess_unknown_probe"],
            "target_subject_id": ["sub_patient_probe"],
        })
        self.check(
            "unknown identity session is denied",
            not ctx.get("policy", {}).get("allowed"),
            f"policy={ctx.get('policy')}",
        )

        self.gw.upsert_session({
            "session_id": "sess_expired_probe",
            "actor_subject_id": "sub_staff_probe",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() - 1000,
        })
        ctx = self.gw.build_chat_context_v3({
            "session_id": ["sess_expired_probe"],
            "target_subject_id": ["sub_patient_probe"],
        })
        self.check(
            "expired session is denied",
            not ctx.get("policy", {}).get("allowed"),
            f"policy={ctx.get('policy')}",
        )

    def run_care_event_probe(self) -> None:
        status, data, _ = request_json(self.base_url, "POST", "/api/v3/care/events", {
            "event_id": "care_probe_noauth",
            "subject_id": "sub_patient_probe",
            "room": "R1203",
            "bed": "B1",
            "kind": "turning_assist",
            "title": "probe",
            "content": "probe care event",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_probe",
            "ts": self.gw.now_ms(),
        })
        self.check("care_event write rejects missing admin cookie", status == 401, f"status={status} data={data}")

        # Direct module probe keeps this independent from HTTP auth fixes.
        care_events = importlib.import_module("care_events")
        try:
            result = care_events.create_care_event({
                "event_id": "care_probe_case",
                "subject_id": "sub_patient_probe",
                "room": "r1203",
                "bed": "b1",
                "kind": "note",
                "title": "case probe",
                "content": "case normalization probe",
                "severity": "info",
                "source": "manual",
                "created_by": "sub_staff_probe",
                "ts": self.gw.now_ms(),
            })
            rows = care_events.list_care_events(room="R1203", bed="B1")
            ok = bool(result.get("ok")) and any(r.get("event_id") == "care_probe_case" for r in rows)
            self.check("care_event normalizes room/bed for create and query", ok, f"result={result} rows={rows}")
        except Exception as exc:
            self.check("care_event normalizes room/bed for create and query", False, f"error={exc}")

    def run_voice_bridge_hint(self):
        """Warning-only: tightening context may break voice ambient session use."""
        voice = self.project / "voice" / "voice_assistant_integrated.py"
        if not voice.is_file():
            print("[probe:info] voice module not present; skip voice path hint")
            return
        text = voice.read_text(encoding="utf-8", errors="replace")
        has_current = ("session/current" in text) or ("fetch_current_session" in text)
        if not has_current:
            print(
                "[probe:Warning] Voice/assistant path: sensitive context may be denied without "
                "session_id; if the local assistant still relies on ambient/current session, "
                "sync can break. Consider obtaining the current session before requesting "
                "sensitive chat context."
            )
        else:
            print("[probe:info] voice module appears to reference current-session fetch")

    def run(self) -> int:
        try:
            self.run_auth_probe()
            self.run_context_probe()
            self.run_care_event_probe()
            self.run_voice_bridge_hint()
            print("[probe:info] ESP32-S3: run tools/run_espidf_build.py after firmware changes.")
            if self.failures:
                print(f"[probe] failures={len(self.failures)}: {', '.join(self.failures)}")
                return 1
            print("[probe] all visible diagnostic checks passed")
            return 0
        finally:
            try:
                self.close()
            except Exception:
                pass


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    project = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else root / "project2_task"
    if not project.exists():
        print(f"[probe] project not found: {project}")
        return 2
    return Probe(project).run()


if __name__ == "__main__":
    raise SystemExit(main())
