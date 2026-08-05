#!/usr/bin/env python3
"""V4 context policy: behavior tests (F3) separated from reason semantics (F12)."""
import importlib
import unittest

from eval_helpers import TempProjectTestMixin, import_gateway, now_ms


# Unique care marker for ambient zero-leak (must not appear when unauth).
AMBIENT_CARE_TITLE = "协助翻身-ambient-probe"
AMBIENT_CARE_CONTENT = "22:10 ambient probe care content must not leak without session."


class ContextPolicyTest(TempProjectTestMixin, unittest.TestCase):
    def _seed(self):
        gw = import_gateway(self.tmp_path)
        gw.create_subject({"subject_id": "sub_staff_test", "name": "Staff", "role": "staff"})
        gw.create_subject({"subject_id": "sub_patient_a", "name": "Patient A", "role": "patient"})
        gw.create_subject({"subject_id": "sub_patient_b", "name": "Patient B", "role": "patient"})
        gw.create_assignment({"assignment_id": "assign_a", "subject_id": "sub_patient_a", "room": "R1203", "bed": "B1"})
        gw.create_assignment({"assignment_id": "assign_b", "subject_id": "sub_patient_b", "room": "R1203", "bed": "B2"})
        gw.create_memory({
            "memory_id": "mem_a",
            "subject_id": "sub_patient_a",
            "kind": "care_preference",
            "content_compressed": "Patient A likes quiet night rounds.",
        })
        gw.append_item("R1203", "B1", "sleep_quality", {"record": "qa", "sleep_h": 6.5, "score": 82, "grade": "good"})
        gw.append_item("R1203", "B2", "sleep_quality", {"record": "qb", "sleep_h": 2.0, "score": 31, "grade": "bad"})
        return gw

    def _assert_zero_leak(self, ctx, *, care_markers: tuple[str, ...] = ()):
        self.assertEqual(ctx["target"]["patient"], {})
        self.assertEqual(ctx["target"].get("assignment", {}), {})
        self.assertEqual(ctx["modalities"]["memory"].get("items", []), [])
        sleep = ctx["modalities"].get("sleep") or {}
        self.assertTrue(sleep == {} or not sleep.get("sleep_score"))
        self.assertNotIn("Patient A", ctx.get("brief", ""))
        self.assertNotIn("Patient A likes quiet", str(ctx))
        blob = str(ctx)
        for marker in care_markers:
            self.assertNotIn(marker, blob, f"care marker leaked into unauthorized context: {marker!r}")

    # --- positive control ---
    def test_staff_can_access_target_patient_context(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_staff",
            "actor_subject_id": "sub_staff_test",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({"session_id": ["sess_staff"], "target_subject_id": ["sub_patient_a"]})
        self.assertTrue(ctx["policy"]["allowed"])
        self.assertEqual(ctx["target"]["patient"].get("subject_id"), "sub_patient_a")
        self.assertIn("Patient A likes quiet", ctx["modalities"]["memory"].get("brief", ""))
        self.assertGreater(ctx["modalities"]["sleep"].get("sleep_score", 0), 0)

    # --- unauthenticated ---
    def test_unauthenticated_context_behavior(self):
        gw = self._seed()
        ctx = gw.build_chat_context_v3({"target_subject_id": ["sub_patient_a"]})
        self.assertFalse(ctx["policy"]["allowed"])
        self._assert_zero_leak(ctx)

    def test_unauthenticated_context_reason(self):
        gw = self._seed()
        ctx = gw.build_chat_context_v3({"target_subject_id": ["sub_patient_a"]})
        self.assertEqual(ctx["policy"]["reason"], "not_authenticated")

    # --- cross patient ---
    def test_patient_cannot_access_other_patient_behavior(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_patient_a",
            "actor_subject_id": "sub_patient_a",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_patient_a"],
            "target_subject_id": ["sub_patient_b"],
        })
        self.assertFalse(ctx["policy"]["allowed"])
        # Patient B data must not leak (reuse full zero-leak checks adapted for B)
        self.assertEqual(ctx["target"]["patient"], {})
        self.assertEqual(ctx["target"].get("assignment", {}), {})
        self.assertEqual(ctx["modalities"]["memory"].get("items", []), [])
        sleep = ctx["modalities"].get("sleep") or {}
        self.assertTrue(sleep == {} or not sleep.get("sleep_score"))
        self.assertNotIn("Patient B", ctx.get("brief", ""))
        self.assertNotIn("Patient B", str(ctx.get("modalities", {})))

    def test_patient_cannot_access_other_patient_reason(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_patient_a",
            "actor_subject_id": "sub_patient_a",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_patient_a"],
            "target_subject_id": ["sub_patient_b"],
        })
        self.assertEqual(ctx["policy"]["reason"], "not_authorized_for_target")

    # --- expired ---
    def test_expired_session_behavior(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_expired",
            "actor_subject_id": "sub_staff_test",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() - 1000,
        })
        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_expired"],
            "target_subject_id": ["sub_patient_a"],
        })
        self.assertFalse(ctx["policy"]["allowed"])
        self._assert_zero_leak(ctx)

    def test_expired_session_reason(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_expired",
            "actor_subject_id": "sub_staff_test",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() - 1000,
        })
        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_expired"],
            "target_subject_id": ["sub_patient_a"],
        })
        self.assertEqual(ctx["policy"]["reason"], "not_authenticated")

    # --- no actor ---
    def test_session_without_actor_subject_behavior(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_no_actor",
            "actor_subject_id": "",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_no_actor"],
            "target_subject_id": ["sub_patient_a"],
        })
        self.assertFalse(ctx["policy"]["allowed"])
        self._assert_zero_leak(ctx)

    def test_session_without_actor_subject_reason(self):
        gw = self._seed()
        gw.upsert_session({
            "session_id": "sess_no_actor",
            "actor_subject_id": "",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({
            "session_id": ["sess_no_actor"],
            "target_subject_id": ["sub_patient_a"],
        })
        self.assertEqual(ctx["policy"]["reason"], "not_authorized_for_target")

    # --- ambient / current fallback ---
    def test_sensitive_target_context_requires_explicit_session_behavior(self):
        """A previous/current session must not silently authorize a targeted
        context request that did not provide an explicit session_id.

        V4.1b: also seeds a care_event so unauth care leakage is covered here
        (single Ability charge via F3-05), not double-counted on F5-05.
        """
        gw = self._seed()
        care_events = importlib.import_module("care_events")
        care_events.create_care_event({
            "event_id": "care_ambient_probe",
            "subject_id": "sub_patient_a",
            "room": "R1203",
            "bed": "B1",
            "kind": "turning_assist",
            "title": AMBIENT_CARE_TITLE,
            "content": AMBIENT_CARE_CONTENT,
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": now_ms(),
        })
        gw.upsert_session({
            "session_id": "sess_staff_recent",
            "actor_subject_id": "sub_staff_test",
            "identity_state": "recognized",
            "assurance_level": "medium",
            "auth_methods": ["face"],
            "expires_ts": now_ms() + 60000,
        })
        ctx = gw.build_chat_context_v3({"target_subject_id": ["sub_patient_a"]})
        self.assertFalse(ctx["policy"]["allowed"])
        self._assert_zero_leak(
            ctx,
            care_markers=(AMBIENT_CARE_TITLE, AMBIENT_CARE_CONTENT),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
