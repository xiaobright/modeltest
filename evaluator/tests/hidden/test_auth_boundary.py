#!/usr/bin/env python3
import unittest

from eval_helpers import (
    ADMIN_TEST_PASSWORD,
    GatewayServer,
    TempProjectTestMixin,
    admin_setup,
    cookie_from,
    db_rows,
    import_gateway,
    now_ms,
    request_json,
    request_text,
)


class AuthBoundaryTest(TempProjectTestMixin, unittest.TestCase):
    def test_admin_setup_stores_password_and_session_token_hashes(self):
        server = GatewayServer(self.tmp_path)
        try:
            cookie = admin_setup(server.base_url)
            rows = db_rows(
                server.gw.DB_FILE,
                "SELECT username, password_hash, salt FROM admin_accounts WHERE username = ?",
                ("admin",),
            )
            self.assertEqual(len(rows), 1)
            self.assertNotEqual(rows[0]["password_hash"], ADMIN_TEST_PASSWORD)
            self.assertTrue(rows[0]["salt"])

            token = cookie.split("=", 1)[1]
            token_rows = db_rows(
                server.gw.DB_FILE,
                "SELECT token_hash FROM admin_http_sessions",
            )
            self.assertTrue(token_rows)
            self.assertNotEqual(token_rows[0]["token_hash"], token)
            self.assertEqual(len(token_rows[0]["token_hash"]), 64)
        finally:
            server.close()

    def test_admin_page_and_auth_state_after_setup(self):
        server = GatewayServer(self.tmp_path)
        try:
            status, html, _ = request_text(server.base_url, "/admin")
            self.assertEqual(status, 200)
            self.assertIn("管理员", html)

            cookie = admin_setup(server.base_url)
            status, data, _ = request_json(server.base_url, "GET", "/api/v3/admin/auth", cookie=cookie)
            self.assertEqual(status, 200)
            self.assertFalse(data.get("setup_required"), data)
            self.assertTrue(data.get("authenticated"), data)

            status, data, _ = request_json(server.base_url, "POST", "/api/v3/admin/setup", {
                "username": "other_admin",
                "display_name": "Other Admin",
                "password": ADMIN_TEST_PASSWORD + "-again",
                "password_confirm": ADMIN_TEST_PASSWORD + "-again",
            })
            self.assertIn(status, (400, 409), data)
        finally:
            server.close()

    def test_management_api_requires_exact_valid_admin_cookie(self):
        server = GatewayServer(self.tmp_path)
        try:
            cookie = admin_setup(server.base_url)
            cookie_name = cookie.split("=", 1)[0]

            status, _, _ = request_json(server.base_url, "GET", "/api/v3/subjects")
            self.assertEqual(status, 401)

            status, _, _ = request_json(
                server.base_url,
                "GET",
                "/api/v3/subjects",
                cookie=f"{cookie_name}=definitely-not-a-real-token",
            )
            self.assertEqual(status, 401)

            status, data, _ = request_json(server.base_url, "GET", "/api/v3/subjects", cookie=cookie)
            self.assertEqual(status, 200)
            self.assertIn("subjects", data)
        finally:
            server.close()

    def test_logout_invalidates_the_old_cookie(self):
        server = GatewayServer(self.tmp_path)
        try:
            cookie = admin_setup(server.base_url)

            status, _, headers = request_json(server.base_url, "POST", "/api/v3/admin/logout", {}, cookie=cookie)
            self.assertEqual(status, 200)
            self.assertIn("Max-Age=0", headers.get("Set-Cookie", ""))

            status, _, _ = request_json(server.base_url, "GET", "/api/v3/subjects", cookie=cookie)
            self.assertEqual(status, 401)
        finally:
            server.close()

    def test_admin_login_returns_a_new_valid_cookie(self):
        server = GatewayServer(self.tmp_path)
        try:
            admin_setup(server.base_url)

            status, _, headers = request_json(server.base_url, "POST", "/api/v3/admin/login", {
                "username": "admin",
                "password": ADMIN_TEST_PASSWORD,
            })
            self.assertEqual(status, 200)
            login_cookie = cookie_from(headers)
            self.assertTrue(login_cookie)

            status, data, _ = request_json(server.base_url, "GET", "/api/v3/subjects", cookie=login_cookie)
            self.assertEqual(status, 200)
            self.assertIn("subjects", data)
        finally:
            server.close()

    def test_remote_identity_gallery_is_not_public(self):
        server = GatewayServer(self.tmp_path, remote=True)
        try:
            status, data, _ = request_json(server.base_url, "GET", "/api/v3/identity/gallery?type=face")
            self.assertIn(status, (401, 403))
            self.assertNotIn("template", str(data).lower())
        finally:
            server.close()

    def test_unknown_identity_session_is_not_authenticated(self):
        """Sessions with identity_state='unknown' must not be treated as authenticated.
        This is an authentication test, not a context authorization test."""
        gw = import_gateway(self.tmp_path)
        gw.create_subject({"subject_id": "sub_staff_test", "name": "Staff", "role": "staff"})
        gw.create_subject({"subject_id": "sub_patient_test", "name": "Patient", "role": "patient"})
        gw.upsert_session({
            "session_id": "sess_unknown",
            "actor_subject_id": "sub_staff_test",
            "identity_state": "unknown",
            "assurance_level": "medium",
            "auth_methods": [],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({"session_id": ["sess_unknown"], "target_subject_id": ["sub_patient_test"]})
        self.assertFalse(ctx["policy"]["allowed"],
                         "unknown identity must not be authenticated")
        self.assertEqual(ctx["policy"]["reason"], "not_authenticated")
        self.assertEqual(ctx["target"]["patient"], {})

    def test_local_session_spoofing_requires_admin_auth(self):
        """Local callers must not be able to create arbitrary v3 sessions.

        The supported local identity path is /api/v3/vision/observation,
        where assurance comes from the identity matcher.  /api/v3/sessions
        is a management API and must require an admin cookie.
        """
        server = GatewayServer(self.tmp_path)
        try:
            server.gw.create_subject({"subject_id": "sub_patient_test", "name": "Patient", "role": "patient"})

            status, data, _ = request_json(server.base_url, "POST", "/api/v3/sessions", {
                "session_id": "sess_spoof",
                "actor_subject_id": "sub_patient_test",
                "identity_state": "recognized",
                "assurance_level": "high",
                "auth_methods": ["face"],
                "expires_ts": now_ms() + 60000,
            })
            self.assertEqual(status, 401, data)
            self.assertFalse(server.gw.get_session("sess_spoof"),
                             "unauthenticated session-spoofing request must not create a session")
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
