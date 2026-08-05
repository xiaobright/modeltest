import importlib
import gc
import json
import os
import secrets
import sqlite3
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import warnings
from http.server import ThreadingHTTPServer
from pathlib import Path

warnings.simplefilter("ignore", ResourceWarning)


PROJECT_MODULES = [
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
]

ADMIN_TEST_PASSWORD = "HiddenPass-" + secrets.token_urlsafe(12)


def project_root() -> Path:
    return Path(os.environ["PROJECT_DIR"]).resolve()


def reset_project_modules():
    for name in PROJECT_MODULES:
        sys.modules.pop(name, None)


def configure_env(tmp_path: Path, extra: dict | None = None):
    os.environ["PROJECT2_DB_FILE"] = str(tmp_path / "project2_eval.db")
    os.environ["PROJECT2_DATA_DIR"] = str(tmp_path)
    os.environ["BEDS_CONFIG"] = '{"beds":[["R1203","B1"],["R1203","B2"],["R1204","B1"]]}'
    os.environ["SLEEP_IMPORT_ENABLED"] = "0"
    os.environ["BEMFA_UID"] = ""
    os.environ["ADMIN_AUTH_ENABLED"] = "1"
    os.environ["ADMIN_SESSION_TTL_MS"] = str(8 * 60 * 60 * 1000)
    os.environ["SESSION_TTL_MS"] = "120000"
    if extra:
        for key, value in extra.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)


def import_gateway(tmp_path: Path, extra_env: dict | None = None):
    configure_env(tmp_path, extra_env)
    gateway_dir = str(project_root() / "gateway")
    if gateway_dir not in sys.path:
        sys.path.insert(0, gateway_dir)
    reset_project_modules()
    gw = importlib.import_module("gateway")
    gw.init_management_db()
    return gw


class GatewayServer:
    def __init__(self, tmp_path: Path, *, remote=False, extra_env: dict | None = None):
        self.gw = import_gateway(tmp_path, extra_env)
        if remote:
            self.gw.Handler._is_local_request = lambda _self: False
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.gw.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)


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


def request_text(base_url: str, path: str, cookie: str = ""):
    headers = {"Cookie": cookie} if cookie else {}
    req = urllib.request.Request(base_url + path, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace"), resp.headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace"), exc.headers


def cookie_from(headers) -> str:
    cookie = headers.get("Set-Cookie", "")
    return cookie.split(";", 1)[0] if cookie else ""


def admin_setup(base_url: str) -> str:
    status, data, headers = request_json(
        base_url,
        "POST",
        "/api/v3/admin/setup",
        {
            "username": "admin",
            "display_name": "Admin",
            "password": ADMIN_TEST_PASSWORD,
            "password_confirm": ADMIN_TEST_PASSWORD,
        },
    )
    if status != 200:
        raise AssertionError(f"admin setup failed: {status} {data}")
    cookie = cookie_from(headers)
    if not cookie:
        raise AssertionError("admin setup did not set cookie")
    return cookie


def db_rows(db_file: str, sql: str, args=()):
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in conn.execute(sql, args).fetchall()]
    finally:
        conn.close()


def now_ms() -> int:
    return int(time.time() * 1000)


class TempProjectTestMixin:
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        reset_project_modules()
        gc.collect()
        self.tmp.cleanup()
