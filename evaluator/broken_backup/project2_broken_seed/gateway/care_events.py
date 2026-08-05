"""Care event tracking for nursing actions.

This module provides CRUD for care_event records — nursing observations,
turning assists, medication checks, etc. that happen during a shift.

TODO: still needs some extra fields, proper route wiring, and integration
with the chat context builder.
"""
from db import db_connect, row_to_dict
from utils import make_id, now_ms


def init_care_events_table():
    """Create care_events table if not exists.

    NOTE: table schema is a first draft — still missing a few columns
    that the v3 spec calls for.  Needs updating before the context
    integration is wired up.
    """
    with db_connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS care_events (
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

            CREATE INDEX IF NOT EXISTS idx_care_events_subject
                ON care_events(subject_id, created_ts DESC);
            CREATE INDEX IF NOT EXISTS idx_care_events_room_bed
                ON care_events(room, bed, created_ts DESC);
        """)


def create_care_event(row: dict) -> dict:
    """Create a new care event record.

    TODO: should check that the caller is authorized before writing.
    """
    event_id = str((row or {}).get("event_id") or make_id("care"))
    subject_id = str((row or {}).get("subject_id") or "")
    room = str((row or {}).get("room") or "")
    bed = str((row or {}).get("bed") or "")
    kind = str((row or {}).get("kind") or "note")
    title = str((row or {}).get("title") or "")
    content = str((row or {}).get("content") or "")
    ts = now_ms()
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO care_events
                (event_id, subject_id, room, bed, kind, title, content, created_ts, updated_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, subject_id, room, bed, kind, title, content, ts, ts),
        )
    return {"event_id": event_id, "subject_id": subject_id, "ok": True}


def list_care_events(subject_id: str = "", room: str = "", bed: str = "") -> list[dict]:
    """List care events, optionally filtered by subject or bed."""
    sql = "SELECT * FROM care_events WHERE 1=1"
    args = []
    if subject_id:
        sql += " AND subject_id = ?"
        args.append(subject_id)
    if room:
        sql += " AND room = ?"
        args.append(room)
    if bed:
        sql += " AND bed = ?"
        args.append(bed)
    sql += " ORDER BY created_ts DESC"
    with db_connect() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [row_to_dict(r) for r in rows]


def build_care_events_context(subject_id: str, limit: int = 10) -> dict:
    """Build care-events section for the v3 chat context.

    TODO: stub for now — returns empty.  Hook it into the context
    builder once the other pieces are ready.
    """
    return {"items": [], "brief": ""}
