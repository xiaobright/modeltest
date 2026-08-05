import os
import sqlite3

from bed_config import BEDS
from config import DB_FILE
from utils import normalize_bed, normalize_room, now_ms


def db_connect():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def row_to_dict(row):
    return dict(row) if row is not None else None


def init_management_db():
    with db_connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS beds (
                room TEXT NOT NULL,
                bed TEXT NOT NULL,
                display_name TEXT NOT NULL DEFAULT '',
                ward TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1,
                device_group TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL,
                PRIMARY KEY (room, bed)
            );

            CREATE TABLE IF NOT EXISTS subjects (
                subject_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                gender TEXT NOT NULL DEFAULT '',
                age INTEGER,
                notes TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bed_assignments (
                assignment_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                room TEXT NOT NULL,
                bed TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                start_ts INTEGER NOT NULL,
                end_ts INTEGER NOT NULL DEFAULT 0,
                created_by TEXT NOT NULL DEFAULT '',
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL,
                FOREIGN KEY(subject_id) REFERENCES subjects(subject_id),
                FOREIGN KEY(room, bed) REFERENCES beds(room, bed)
            );

            CREATE TABLE IF NOT EXISTS credentials (
                credential_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                type TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT '',
                template_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL,
                FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
            );

            CREATE TABLE IF NOT EXISTS memories (
                memory_id TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                content_compressed TEXT NOT NULL,
                visibility_scope TEXT NOT NULL DEFAULT 'care_team',
                source TEXT NOT NULL DEFAULT 'manual',
                confidence REAL NOT NULL DEFAULT 1.0,
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL,
                FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                actor_subject_id TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'unknown',
                auth_methods_json TEXT NOT NULL DEFAULT '[]',
                assurance_level TEXT NOT NULL DEFAULT 'none',
                identity_state TEXT NOT NULL DEFAULT 'unknown',
                emotion_json TEXT NOT NULL DEFAULT '{}',
                created_ts INTEGER NOT NULL,
                last_seen_ts INTEGER NOT NULL,
                expires_ts INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_accounts (
                username TEXT PRIMARY KEY,
                subject_id TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_ts INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL,
                FOREIGN KEY(subject_id) REFERENCES subjects(subject_id)
            );

            CREATE TABLE IF NOT EXISTS admin_http_sessions (
                token_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_ts INTEGER NOT NULL,
                last_seen_ts INTEGER NOT NULL,
                expires_ts INTEGER NOT NULL,
                FOREIGN KEY(username) REFERENCES admin_accounts(username)
            );

            CREATE INDEX IF NOT EXISTS idx_subjects_role_status
                ON subjects(role, status);
            CREATE INDEX IF NOT EXISTS idx_assignments_bed_status
                ON bed_assignments(room, bed, status);
            CREATE INDEX IF NOT EXISTS idx_assignments_subject_status
                ON bed_assignments(subject_id, status);
            CREATE INDEX IF NOT EXISTS idx_credentials_subject_type
                ON credentials(subject_id, type);
            CREATE INDEX IF NOT EXISTS idx_memories_subject_updated
                ON memories(subject_id, updated_ts DESC);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires
                ON sessions(expires_ts, last_seen_ts DESC);
            CREATE INDEX IF NOT EXISTS idx_admin_http_sessions_expires
                ON admin_http_sessions(expires_ts, last_seen_ts DESC);

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
            """
        )
        sync_config_beds(conn)
    print(f'[DB] SQLite management database: {DB_FILE}')


def sync_config_beds(conn):
    ts = now_ms()
    for room, bed in BEDS:
        room_n = normalize_room(room)
        bed_n = normalize_bed(bed)
        device_group = f'{room_n.lower()}{bed_n.lower()}'
        conn.execute(
            """
            INSERT OR IGNORE INTO beds
                (room, bed, display_name, ward, enabled, device_group, notes, created_ts, updated_ts)
            VALUES (?, ?, ?, '', 1, ?, '', ?, ?)
            """,
            (room_n, bed_n, f'{room_n}-{bed_n}', device_group, ts, ts),
        )
        conn.execute(
            """
            UPDATE beds
               SET device_group = CASE WHEN device_group = '' THEN ? ELSE device_group END,
                   updated_ts = ?
             WHERE room = ? AND bed = ?
            """,
            (device_group, ts, room_n, bed_n),
        )
