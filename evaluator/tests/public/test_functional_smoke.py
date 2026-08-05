#!/usr/bin/env python3
"""Basic functional smoke test — verifies the gateway HTTP server starts
and key API endpoints respond with *something*.

This is intentionally shallow: it does NOT check security properties,
authorization policy, or data correctness.  It only confirms that the
HTTP routes are wired and the admin setup endpoint can be called.
"""
import importlib
import gc
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import warnings
from http.server import ThreadingHTTPServer
from pathlib import Path

warnings.simplefilter("ignore", ResourceWarning)

MODULES = [
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


def import_fresh_gateway(project: Path):
    gateway_dir = str(project / "gateway")
    if gateway_dir not in sys.path:
        sys.path.insert(0, gateway_dir)
    for name in MODULES:
        sys.modules.pop(name, None)
    return importlib.import_module("gateway")


class FunctionalSmokeTest(unittest.TestCase):
    def setUp(self):
        self.project = Path(os.environ["PROJECT_DIR"]).resolve()
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["PROJECT2_DB_FILE"] = str(Path(self.tmp.name) / "project2_func.db")
        os.environ["BEDS_CONFIG"] = '{"beds":[["R1203","B1"],["R1203","B2"]]}'
        os.environ["SLEEP_IMPORT_ENABLED"] = "0"
        os.environ["BEMFA_UID"] = ""
        os.environ["ADMIN_AUTH_ENABLED"] = "1"

        self.gw = import_fresh_gateway(self.project)
        self.gw.init_management_db()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), self.gw.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=3)
        for name in MODULES:
            sys.modules.pop(name, None)
        gc.collect()
        self.tmp.cleanup()

    def _get(self, path):
        req = urllib.request.Request(self.base_url + path, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")

    def _post_json(self, path, body):
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = {"raw": raw}
            return exc.code, parsed

    def test_admin_page_is_served(self):
        """GET /admin returns an HTML page (the admin management UI)."""
        status, body = self._get("/admin")
        self.assertEqual(status, 200, f"/admin returned {status}")
        self.assertIn("管理员", body, "/admin page missing expected content")

    def test_admin_setup_endpoint_responds(self):
        """POST /api/v3/admin/setup returns 200 with a session cookie."""
        status, data = self._post_json("/api/v3/admin/setup", {
            "username": "admin",
            "display_name": "Admin",
            "password": "SmokeTest-Password-123",
            "password_confirm": "SmokeTest-Password-123",
        })
        self.assertEqual(status, 200, f"admin setup returned {status}: {data}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
