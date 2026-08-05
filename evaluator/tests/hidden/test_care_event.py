#!/usr/bin/env python3
"""Care-event hidden tests — split for granularity and reduced auth coupling.

test_care_event_create_and_query:
    CRUD via Python API.  Does NOT require admin HTTP auth, so a model
    that implements care_events correctly but hasn't fixed auth.py can
    still earn partial credit.

test_care_event_context_integration:
    Context pipeline via Python API (upsert_session + build_chat_context_v3).
    Also independent of admin HTTP auth.

test_care_event_create_requires_admin_auth:
    HTTP-level auth gate.  This one intentionally depends on the full
    admin auth pipeline.
"""
import importlib
import unittest

from eval_helpers import GatewayServer, TempProjectTestMixin, admin_setup, now_ms, import_gateway, request_json


class CareEventModuleCrudTest(TempProjectTestMixin, unittest.TestCase):
    """CRUD tests via the care_events module — no admin HTTP auth required."""

    def _gateway_and_care_events_module(self):
        gw = import_gateway(self.tmp_path)
        return gw, importlib.import_module("care_events")

    def _seed_subjects(self, gw):
        gw.create_subject({"subject_id": "sub_patient_test", "name": "Patient", "role": "patient"})
        gw.create_subject({"subject_id": "sub_staff_test", "name": "Staff", "role": "staff"})

    def test_care_event_create_and_query(self):
        gw, care_events = self._gateway_and_care_events_module()
        self._seed_subjects(gw)

        event = {
            "event_id": "care_crud_001",
            "subject_id": "sub_patient_test",
            "room": "R1203",
            "bed": "B1",
            "kind": "turning_assist",
            "title": "协助翻身",
            "content": "22:10 已协助患者由仰卧调整为侧卧。",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": now_ms(),
        }

        result = care_events.create_care_event(event)
        self.assertTrue(result.get("ok"), f"create_care_event returned: {result}")

        rows = care_events.list_care_events(subject_id="sub_patient_test")
        self.assertTrue(rows, "list_care_events returned no rows for sub_patient_test")
        found = next((r for r in rows if r.get("event_id") == "care_crud_001"), None)
        self.assertIsNotNone(found, f"care event not found in results: {rows}")
        self.assertEqual(found.get("title"), "协助翻身")
        self.assertEqual(found.get("severity"), "info")
        self.assertEqual(found.get("source"), "manual")
        self.assertEqual(found.get("created_by"), "sub_staff_test")
        self.assertGreater(int(found.get("ts") or 0), 0)

    def test_care_event_query_by_room_bed(self):
        gw, care_events = self._gateway_and_care_events_module()
        self._seed_subjects(gw)

        care_events.create_care_event({
            "event_id": "care_room_001",
            "subject_id": "sub_patient_test",
            "room": "R1203",
            "bed": "B1",
            "kind": "note",
            "title": "R1203-B1 event",
            "content": "test content",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": now_ms(),
        })

        rows = care_events.list_care_events(room="R1203", bed="B1")
        self.assertTrue(rows, "list_care_events by room/bed returned no rows")
        self.assertTrue(any(r.get("event_id") == "care_room_001" for r in rows), rows)

    def test_care_event_limit_and_descending_order(self):
        gw, care_events = self._gateway_and_care_events_module()
        self._seed_subjects(gw)

        for idx, ts in enumerate((1710000000000, 1710000001000, 1710000002000), start=1):
            care_events.create_care_event({
                "event_id": f"care_order_{idx}",
                "subject_id": "sub_patient_test",
                "room": "R1203",
                "bed": "B1",
                "kind": "note",
                "title": f"order {idx}",
                "content": f"content {idx}",
                "severity": "info",
                "source": "manual",
                "created_by": "sub_staff_test",
                "ts": ts,
            })

        try:
            rows = care_events.list_care_events(subject_id="sub_patient_test", limit=2)
        except TypeError as exc:
            self.fail(f"list_care_events must accept limit keyword: {exc}")

        ids = [r.get("event_id") for r in rows]
        self.assertEqual(ids[:2], ["care_order_3", "care_order_2"], rows)
        self.assertEqual(len(rows), 2, rows)

    def test_care_event_room_bed_case_normalization(self):
        """Room/bed values in care events must be normalized (uppercased)
        so that case-insensitive queries work consistently across modules.
        The gateway's _get_room_bed and sensor_store use uppercase, but
        sleep_importer uses lowercase — a model that copies the wrong
        convention will fail this test."""
        gw, care_events = self._gateway_and_care_events_module()
        self._seed_subjects(gw)

        # Create with lowercase room/bed
        care_events.create_care_event({
            "event_id": "care_case_001",
            "subject_id": "sub_patient_test",
            "room": "r1203",
            "bed": "b1",
            "kind": "note",
            "title": "case test",
            "content": "testing case normalization",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": now_ms(),
        })

        # Query with uppercase — the gateway convention everywhere else
        rows_upper = care_events.list_care_events(room="R1203", bed="B1")
        found = any(r.get("event_id") == "care_case_001" for r in rows_upper)
        self.assertTrue(found,
            "care event created with lowercase room/bed should be findable with uppercase query")


class CareEventContextTest(TempProjectTestMixin, unittest.TestCase):
    """Context integration via Python API — uses upsert_session to bypass
    admin HTTP auth, so it does NOT depend on auth.py being fully fixed."""

    def test_care_event_authorized_context_includes_care(self):
        """V4.1b F5-05: authorized path only (no unauth half — that is F3-05).

        Unauth/ambient care leakage is scored once under F3-05 ambient zero-leak
        to avoid Ability double-counting the same policy root cause.
        """
        gw = import_gateway(self.tmp_path)
        care_events = importlib.import_module("care_events")

        gw.create_subject({"subject_id": "sub_staff_test", "name": "Staff", "role": "staff"})
        gw.create_subject({"subject_id": "sub_patient_test", "name": "Patient", "role": "patient"})
        gw.create_assignment({
            "assignment_id": "assign_patient_test",
            "subject_id": "sub_patient_test",
            "room": "R1203",
            "bed": "B1",
        })

        care_events.create_care_event({
            "event_id": "care_ctx_001",
            "subject_id": "sub_patient_test",
            "room": "R1203",
            "bed": "B1",
            "kind": "turning_assist",
            "title": "协助翻身",
            "content": "22:10 已协助患者由仰卧调整为侧卧。",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": now_ms(),
        })

        gw.upsert_session({
            "session_id": "sess_staff",
            "actor_subject_id": "sub_staff_test",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })

        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_staff"],
            "target_subject_id": ["sub_patient_test"],
        })
        self.assertTrue(ctx["policy"]["allowed"],
                        f"expected policy.allowed=True, got: {ctx['policy']}")
        self.assertIn("care", str(ctx.get("modalities", {})).lower(),
                       "care_events missing from modalities")
        self.assertIn("协助翻身", str(ctx),
                       "care event content not found in authorized context")


class CareEventAuthGateTest(TempProjectTestMixin, unittest.TestCase):
    """HTTP-level auth gate — depends on admin auth pipeline."""

    def test_care_event_create_requires_admin_auth(self):
        server = GatewayServer(self.tmp_path)
        try:
            cookie = admin_setup(server.base_url)
            server.gw.create_subject({"subject_id": "sub_patient_test", "name": "Patient", "role": "patient"})
            server.gw.create_subject({"subject_id": "sub_staff_test", "name": "Staff", "role": "staff"})

            event = {
                "event_id": "care_auth_001",
                "subject_id": "sub_patient_test",
                "room": "R1203",
                "bed": "B1",
                "kind": "turning_assist",
                "title": "协助翻身",
                "content": "22:10 已协助患者由仰卧调整为侧卧。",
                "severity": "info",
                "source": "manual",
                "created_by": "sub_staff_test",
                "ts": now_ms(),
            }

            # Without admin cookie → must be 401
            status, _, _ = request_json(server.base_url, "POST", "/api/v3/care/events", event)
            self.assertEqual(status, 401, "care event write must require admin login")

            # With admin cookie → must succeed
            status, data, _ = request_json(
                server.base_url, "POST", "/api/v3/care/events", event, cookie=cookie,
            )
            self.assertEqual(status, 200, data)
            self.assertTrue(data.get("ok", True))

            status, data, _ = request_json(
                server.base_url,
                "GET",
                "/api/v3/care/events?subject_id=sub_patient_test",
                cookie=cookie,
            )
            self.assertEqual(status, 200, data)
            self.assertIn("协助翻身", str(data))

            status, _, _ = request_json(
                server.base_url,
                "GET",
                "/api/v3/care/events?subject_id=sub_patient_test",
            )
            self.assertEqual(status, 401, "care event read must require admin login")
        finally:
            server.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
