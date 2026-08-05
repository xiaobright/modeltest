#!/usr/bin/env python3
"""V4.1 DB migration hidden tests.

F6-01 uses a full oldest-schema fixture (end-to-end upgrade).
F6-02..05 use independent intermediate fixtures so a single init crash
(e.g. CREATE INDEX before ADD COLUMN ts) does not zero the entire family.
"""
from __future__ import annotations

import importlib
import os
import sqlite3
import sys
import unittest
from pathlib import Path

from eval_helpers import TempProjectTestMixin, configure_env, reset_project_modules, now_ms


LEGACY_CREATED_TS = 1710000000000
LEGACY_EVENT_ID = "care_old_001"
LEGACY_SUBJECT = "sub_patient_test"


class DbMigrationTest(TempProjectTestMixin, unittest.TestCase):
    # ------------------------------------------------------------------ fixtures
    def _db_path(self) -> Path:
        configure_env(self.tmp_path)
        return Path(os.environ["PROJECT2_DB_FILE"])

    def _connect(self, db_file: Path) -> sqlite3.Connection:
        return sqlite3.connect(db_file)

    def _write_v0_legacy_schema(self, db_file: Path) -> None:
        """Oldest care_events schema: no severity/source/created_by/ts."""
        conn = self._connect(db_file)
        try:
            conn.executescript(
                f"""
                CREATE TABLE care_events (
                    event_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    room TEXT NOT NULL,
                    bed TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    created_ts INTEGER NOT NULL,
                    updated_ts INTEGER NOT NULL
                );
                INSERT INTO care_events
                    (event_id, subject_id, room, bed, kind, title, content, created_ts, updated_ts)
                VALUES
                    ('{LEGACY_EVENT_ID}', '{LEGACY_SUBJECT}', 'R1203', 'B1', 'note',
                     'old title', 'old content', {LEGACY_CREATED_TS}, {LEGACY_CREATED_TS});
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _write_schema_with_new_columns(
        self,
        db_file: Path,
        *,
        ts_value: int | None,
    ) -> None:
        """Intermediate fixture: new columns exist; optional ts backfill pending.

        Used so fidelity / sort / idempotent checks remain observable even when
        a candidate's full v0→current upgrade path crashes.
        """
        # Store NULL when ts_value is None (pending backfill).
        ts_sql = "NULL" if ts_value is None else str(int(ts_value))
        conn = self._connect(db_file)
        try:
            conn.executescript(
                f"""
                CREATE TABLE care_events (
                    event_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    room TEXT NOT NULL,
                    bed TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    title TEXT NOT NULL DEFAULT '',
                    content TEXT NOT NULL DEFAULT '',
                    severity TEXT NOT NULL DEFAULT 'info',
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_by TEXT NOT NULL DEFAULT '',
                    ts INTEGER,
                    created_ts INTEGER NOT NULL,
                    updated_ts INTEGER NOT NULL
                );
                INSERT INTO care_events
                    (event_id, subject_id, room, bed, kind, title, content,
                     severity, source, created_by, ts, created_ts, updated_ts)
                VALUES
                    ('{LEGACY_EVENT_ID}', '{LEGACY_SUBJECT}', 'R1203', 'B1', 'note',
                     'old title', 'old content',
                     'info', 'manual', '', {ts_sql},
                     {LEGACY_CREATED_TS}, {LEGACY_CREATED_TS});
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _import_gateway_after_prepared_db(self):
        project = Path(os.environ["PROJECT_DIR"]).resolve()
        gateway_dir = str(project / "gateway")
        if gateway_dir not in sys.path:
            sys.path.insert(0, gateway_dir)
        reset_project_modules()
        gw = importlib.import_module("gateway")
        gw.init_management_db()
        return gw, importlib.import_module("care_events")

    def _find_legacy(self, rows):
        return next((r for r in rows if r.get("event_id") == LEGACY_EVENT_ID), None)

    # ------------------------------------------------------------------ F6-01
    def test_existing_old_care_events_table_is_migrated_without_data_loss(self):
        """F6a: full oldest schema must not crash init; old row survives; new write ok."""
        db_file = self._db_path()
        self._write_v0_legacy_schema(db_file)
        gw, care_events = self._import_gateway_after_prepared_db()
        self.assertTrue(db_file.is_file())
        rows = care_events.list_care_events(subject_id=LEGACY_SUBJECT)
        old = self._find_legacy(rows)
        self.assertIsNotNone(old, f"old care_event row lost after migration: {rows}")
        self.assertEqual(old.get("title"), "old title")
        gw.create_subject({"subject_id": LEGACY_SUBJECT, "name": "Patient", "role": "patient"})
        result = care_events.create_care_event({
            "event_id": "care_new_001",
            "subject_id": LEGACY_SUBJECT,
            "room": "R1203",
            "bed": "B1",
            "kind": "note",
            "title": "new title",
            "content": "new content",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": now_ms(),
        })
        self.assertTrue(result.get("ok"), result)

    # ------------------------------------------------------------------ F6-02
    def test_migration_adds_columns_and_keeps_old_rows(self):
        """F6b: required columns present after init on intermediate schema; old row kept.

        Independent of v0 E2E: fixture already has new columns so an
        index-before-column crash on pure v0 does not block this check.
        """
        db_file = self._db_path()
        self._write_schema_with_new_columns(db_file, ts_value=LEGACY_CREATED_TS)
        _gw, care_events = self._import_gateway_after_prepared_db()
        conn = self._connect(db_file)
        try:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(care_events)").fetchall()}
        finally:
            conn.close()
        for column in ("severity", "source", "created_by", "ts"):
            self.assertIn(column, columns, f"care_events missing column {column}")
        rows = care_events.list_care_events(subject_id=LEGACY_SUBJECT)
        old = self._find_legacy(rows)
        self.assertIsNotNone(old)

    # ------------------------------------------------------------------ F6-03
    def test_migration_backfills_ts_from_created_ts(self):
        """F6c: ts must be backfilled from created_ts when ts is null/zero."""
        db_file = self._db_path()
        # ts NULL = pending backfill; columns already present (independent fixture).
        self._write_schema_with_new_columns(db_file, ts_value=None)
        _gw, care_events = self._import_gateway_after_prepared_db()
        rows = care_events.list_care_events(subject_id=LEGACY_SUBJECT)
        old = self._find_legacy(rows)
        self.assertIsNotNone(old)
        self.assertGreater(int(old.get("ts") or 0), 0)
        self.assertEqual(
            int(old.get("ts")),
            LEGACY_CREATED_TS,
            "old care_event timestamp was not mapped correctly from created_ts during migration",
        )

    # ------------------------------------------------------------------ F6-04
    def test_migration_init_is_idempotent(self):
        """F6d: running init twice must not crash or drop rows."""
        db_file = self._db_path()
        self._write_schema_with_new_columns(db_file, ts_value=LEGACY_CREATED_TS)
        gw, care_events = self._import_gateway_after_prepared_db()
        gw.init_management_db()
        rows = care_events.list_care_events(subject_id=LEGACY_SUBJECT)
        self.assertTrue(any(r.get("event_id") == LEGACY_EVENT_ID for r in rows))

    # ------------------------------------------------------------------ F6-05
    def test_migration_mixed_old_new_sort_order(self):
        """F6e: old + new rows list with newer ts first."""
        db_file = self._db_path()
        self._write_schema_with_new_columns(db_file, ts_value=LEGACY_CREATED_TS)
        gw, care_events = self._import_gateway_after_prepared_db()
        gw.create_subject({"subject_id": LEGACY_SUBJECT, "name": "Patient", "role": "patient"})
        newer_ts = 1800000000000
        care_events.create_care_event({
            "event_id": "care_new_sort",
            "subject_id": LEGACY_SUBJECT,
            "room": "R1203",
            "bed": "B1",
            "kind": "note",
            "title": "newer",
            "content": "n",
            "severity": "info",
            "source": "manual",
            "created_by": "sub_staff_test",
            "ts": newer_ts,
        })
        rows = care_events.list_care_events(subject_id=LEGACY_SUBJECT)
        self.assertGreaterEqual(len(rows), 2)
        try:
            ordered = care_events.list_care_events(subject_id=LEGACY_SUBJECT, limit=10)
        except TypeError:
            ordered = rows
        ids = [r.get("event_id") for r in ordered]
        if "care_new_sort" in ids and LEGACY_EVENT_ID in ids:
            self.assertLess(
                ids.index("care_new_sort"),
                ids.index(LEGACY_EVENT_ID),
                f"expected newer event before old: {ids}",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
