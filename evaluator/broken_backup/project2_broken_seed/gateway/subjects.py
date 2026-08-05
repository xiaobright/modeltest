import sqlite3

from config import (
    FACE_DETECTOR_MODEL,
    FACE_DETECT_SCORE_THRESHOLD,
    FACE_ENROLL_DETECT,
    FACE_MATCH_CANDIDATE_THRESHOLD,
    FACE_MATCH_RECOGNIZED_THRESHOLD,
    SESSION_TTL_MS,
)
from db import db_connect, row_to_dict
from utils import (
    as_bool,
    as_float,
    as_int,
    json_dumps_compact,
    json_loads_default,
    make_id,
    normalize_bed,
    normalize_room,
    now_ms,
)

try:
    from vision.identity_runtime import (
        build_face_template_from_image_b64,
        match_face_image_b64,
        match_face_vector,
        template_vector,
    )
    IDENTITY_RUNTIME_ERROR = ''
except Exception as e:  # noqa: BLE001
    IDENTITY_RUNTIME_ERROR = str(e)
    build_face_template_from_image_b64 = None
    match_face_image_b64 = None
    match_face_vector = None
    template_vector = None


def list_subjects(role: str = "", status: str = ""):
    sql = "SELECT * FROM subjects WHERE 1=1"
    args = []
    if role:
        sql += " AND role = ?"
        args.append(role)
    if status:
        sql += " AND status = ?"
        args.append(status)
    sql += " ORDER BY role, name, subject_id"
    with db_connect() as conn:
        return [row_to_dict(r) for r in conn.execute(sql, args).fetchall()]


def get_subject(subject_id: str):
    if not subject_id:
        return None
    with db_connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM subjects WHERE subject_id = ?", (subject_id,)).fetchone())


def create_subject(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    ts = now_ms()
    subject_id = str(row.get("subject_id") or make_id("sub"))
    name = str(row.get("name") or subject_id)
    role = str(row.get("role") or "patient").strip().lower()
    if role not in ("admin", "staff", "patient", "visitor", "unknown"):
        raise ValueError("invalid role")
    status = str(row.get("status") or "active").strip().lower()
    gender = str(row.get("gender") or "")
    age = row.get("age")
    age = None if age in (None, "") else as_int(age, 0)
    notes = str(row.get("notes") or "")
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO subjects
                (subject_id, name, role, status, gender, age, notes, created_ts, updated_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (subject_id, name, role, status, gender, age, notes, ts, ts),
        )
    return get_subject(subject_id)


def get_bed_meta(room: str, bed: str):
    room_n = normalize_room(room)
    bed_n = normalize_bed(bed)
    with db_connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM beds WHERE room = ? AND bed = ?", (room_n, bed_n)).fetchone())


def list_bed_meta():
    with db_connect() as conn:
        rows = conn.execute("SELECT * FROM beds ORDER BY room, bed").fetchall()
        return [row_to_dict(r) for r in rows]


def get_active_assignment_for_bed(room: str, bed: str):
    room_n = normalize_room(room)
    bed_n = normalize_bed(bed)
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT a.*, s.name AS subject_name, s.role AS subject_role, s.status AS subject_status
              FROM bed_assignments a
              JOIN subjects s ON s.subject_id = a.subject_id
             WHERE a.room = ? AND a.bed = ? AND a.status = 'active'
             ORDER BY a.start_ts DESC
             LIMIT 1
            """,
            (room_n, bed_n),
        ).fetchone()
        return row_to_dict(row)


def get_active_assignment_for_subject(subject_id: str):
    if not subject_id:
        return None
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT a.*, b.display_name
              FROM bed_assignments a
              JOIN beds b ON b.room = a.room AND b.bed = a.bed
             WHERE a.subject_id = ? AND a.status = 'active'
             ORDER BY a.start_ts DESC
             LIMIT 1
            """,
            (subject_id,),
        ).fetchone()
        return row_to_dict(row)


def list_assignments(subject_id: str = "", room: str = "", bed: str = "", status: str = ""):
    sql = """
        SELECT a.*, s.name AS subject_name, s.role AS subject_role
          FROM bed_assignments a
          JOIN subjects s ON s.subject_id = a.subject_id
         WHERE 1=1
    """
    args = []
    if subject_id:
        sql += " AND a.subject_id = ?"
        args.append(subject_id)
    if room:
        sql += " AND a.room = ?"
        args.append(normalize_room(room))
    if bed:
        sql += " AND a.bed = ?"
        args.append(normalize_bed(bed))
    if status:
        sql += " AND a.status = ?"
        args.append(status)
    sql += " ORDER BY a.start_ts DESC"
    with db_connect() as conn:
        return [row_to_dict(r) for r in conn.execute(sql, args).fetchall()]


def create_assignment(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    subject_id = str(row.get("subject_id") or "")
    room = normalize_room(row.get("room"))
    bed = normalize_bed(row.get("bed"))
    if not subject_id or not room or not bed:
        raise ValueError("subject_id, room and bed are required")
    ts = now_ms()
    assignment_id = str(row.get("assignment_id") or make_id("assign"))
    start_ts = as_int(row.get("start_ts"), ts)
    created_by = str(row.get("created_by") or "")
    with db_connect() as conn:
        if not conn.execute("SELECT 1 FROM subjects WHERE subject_id = ?", (subject_id,)).fetchone():
            raise ValueError("subject not found")
        if not conn.execute("SELECT 1 FROM beds WHERE room = ? AND bed = ?", (room, bed)).fetchone():
            raise ValueError("bed not found")
        conn.execute(
            """
            UPDATE bed_assignments
               SET status = 'closed', end_ts = ?, updated_ts = ?
             WHERE status = 'active' AND room = ? AND bed = ?
            """,
            (start_ts, ts, room, bed),
        )
        conn.execute(
            """
            UPDATE bed_assignments
               SET status = 'closed', end_ts = ?, updated_ts = ?
             WHERE status = 'active' AND subject_id = ?
            """,
            (start_ts, ts, subject_id),
        )
        conn.execute(
            """
            INSERT INTO bed_assignments
                (assignment_id, subject_id, room, bed, status, start_ts, end_ts, created_by, created_ts, updated_ts)
            VALUES (?, ?, ?, ?, 'active', ?, 0, ?, ?, ?)
            """,
            (assignment_id, subject_id, room, bed, start_ts, created_by, ts, ts),
        )
    rows = list_assignments(status="active", room=room, bed=bed)
    return rows[0] if rows else None


def close_assignment(assignment_id: str):
    ts = now_ms()
    with db_connect() as conn:
        conn.execute(
            """
            UPDATE bed_assignments
               SET status = 'closed', end_ts = CASE WHEN end_ts = 0 THEN ? ELSE end_ts END, updated_ts = ?
             WHERE assignment_id = ?
            """,
            (ts, ts, assignment_id),
        )
    return {"assignment_id": assignment_id, "status": "closed", "ts": ts}


def list_memories(subject_id: str, limit: int = 20):
    if not subject_id:
        return []
    limit = max(1, min(as_int(limit, 20), 200))
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT *
              FROM memories
             WHERE subject_id = ?
             ORDER BY updated_ts DESC
             LIMIT ?
            """,
            (subject_id, limit),
        ).fetchall()
        return [row_to_dict(r) for r in rows]


def create_memory(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    subject_id = str(row.get("subject_id") or "")
    content = str(row.get("content_compressed") or row.get("content") or "").strip()
    if not subject_id or not content:
        raise ValueError("subject_id and content_compressed are required")
    ts = now_ms()
    memory_id = str(row.get("memory_id") or make_id("mem"))
    kind = str(row.get("kind") or "care_note")
    visibility_scope = str(row.get("visibility_scope") or "care_team")
    source = str(row.get("source") or "manual")
    confidence = as_float(row.get("confidence"), 1.0)
    with db_connect() as conn:
        if not conn.execute("SELECT 1 FROM subjects WHERE subject_id = ?", (subject_id,)).fetchone():
            raise ValueError("subject not found")
        conn.execute(
            """
            INSERT INTO memories
                (memory_id, subject_id, kind, content_compressed, visibility_scope, source, confidence, created_ts, updated_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (memory_id, subject_id, kind, content, visibility_scope, source, confidence, ts, ts),
        )
    return list_memories(subject_id, limit=1)[0]


def list_credentials(subject_id: str = "", credential_type: str = "", include_template: bool = False):
    sql = "SELECT * FROM credentials WHERE 1=1"
    args = []
    if subject_id:
        sql += " AND subject_id = ?"
        args.append(subject_id)
    if credential_type:
        sql += " AND type = ?"
        args.append(credential_type)
    sql += " ORDER BY type, created_ts DESC"
    with db_connect() as conn:
        rows = [row_to_dict(r) for r in conn.execute(sql, args).fetchall()]
    out = []
    for row in rows:
        template = json_loads_default(row.pop("template_json", "{}"), {})
        if include_template:
            row["template"] = template
        else:
            row["template_meta"] = {
                "keys": sorted(template.keys()) if isinstance(template, dict) else [],
            }
        out.append(row)
    return out


def create_credential(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    subject_id = str(row.get("subject_id") or "")
    credential_type = str(row.get("type") or "").strip().lower()
    if not subject_id or not credential_type:
        raise ValueError("subject_id and type are required")
    ts = now_ms()
    credential_id = str(row.get("credential_id") or make_id("cred"))
    provider = str(row.get("provider") or "")
    template = row.get("template") if isinstance(row.get("template"), dict) else {}
    status = str(row.get("status") or "active")
    with db_connect() as conn:
        if not conn.execute("SELECT 1 FROM subjects WHERE subject_id = ?", (subject_id,)).fetchone():
            raise ValueError("subject not found")
        conn.execute(
            """
            INSERT INTO credentials
                (credential_id, subject_id, type, provider, template_json, status, created_ts, updated_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (credential_id, subject_id, credential_type, provider, json_dumps_compact(template), status, ts, ts),
        )
    rows = list_credentials(subject_id=subject_id, credential_type=credential_type, include_template=True)
    return next((x for x in rows if x.get("credential_id") == credential_id), rows[0] if rows else None)


def _extract_image_b64(row: dict) -> str:
    image_b64 = str(row.get("image_b64") or row.get("image") or "")
    if image_b64:
        return image_b64
    artifacts = row.get("artifacts")
    if isinstance(artifacts, list):
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            kind = str(artifact.get("kind") or artifact.get("type") or "").lower()
            if kind in ("image_b64", "image", "face_image"):
                data = str(artifact.get("data") or artifact.get("image_b64") or "")
                if data:
                    return data
    artifact = row.get("artifact") if isinstance(row.get("artifact"), dict) else {}
    kind = str(artifact.get("kind") or artifact.get("type") or "").lower()
    if kind in ("image_b64", "image", "face_image"):
        return str(artifact.get("data") or artifact.get("image_b64") or "")
    return ""


def create_credential_from_enrollment(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    subject_id = str(row.get("subject_id") or "")
    credential_type = str(row.get("type") or row.get("credential_type") or "").strip().lower()
    if not subject_id or not credential_type:
        raise ValueError("subject_id and type are required")
    provider = str(row.get("provider") or "admin_upload")
    status = str(row.get("status") or "active")
    template = row.get("template") if isinstance(row.get("template"), dict) else {}

    if credential_type == "face":
        if build_face_template_from_image_b64 is None:
            raise ValueError(f"identity runtime unavailable: {IDENTITY_RUNTIME_ERROR}")
        if not template:
            image_b64 = _extract_image_b64(row)
            if not image_b64:
                raise ValueError("face enrollment requires image_b64 or template")
            detect_face = as_bool(row.get("detect_face"), FACE_ENROLL_DETECT)
            try:
                template = build_face_template_from_image_b64(
                    image_b64,
                    detector_model_path=FACE_DETECTOR_MODEL,
                    detect_face=detect_face,
                    score_threshold=FACE_DETECT_SCORE_THRESHOLD,
                )
            except Exception as e:  # noqa: BLE001
                raise ValueError(f"face enrollment failed: {e}") from e
        template["enrollment"] = {
            "method": "image_upload",
            "provider": provider,
            "enrolled_ts": now_ms(),
        }
    elif not template:
        template = {
            "schema": f"project2.credential.{credential_type}.v1",
            "modality": credential_type,
            "payload": row.get("payload") if isinstance(row.get("payload"), dict) else {},
            "enrollment": {
                "method": str(row.get("method") or "placeholder"),
                "provider": provider,
                "enrolled_ts": now_ms(),
            },
        }

    return create_credential({
        "credential_id": row.get("credential_id", ""),
        "subject_id": subject_id,
        "type": credential_type,
        "provider": provider,
        "template": template,
        "status": status,
    })


def list_identity_gallery(credential_type: str = "face"):
    credential_type = str(credential_type or "face").strip().lower()
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT c.*, s.name AS subject_name, s.role AS subject_role, s.status AS subject_status
              FROM credentials c
              JOIN subjects s ON s.subject_id = c.subject_id
             WHERE c.type = ? AND c.status = 'active' AND s.status = 'active'
             ORDER BY c.updated_ts DESC
            """,
            (credential_type,),
        ).fetchall()
    out = []
    for row in rows:
        obj = row_to_dict(row)
        obj["template"] = json_loads_default(obj.pop("template_json", "{}"), {})
        out.append(obj)
    return out


def match_identity(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    credential_type = str(row.get("type") or row.get("credential_type") or "face").strip().lower()
    if credential_type != "face":
        raise ValueError("identity match currently supports face only")
    if match_face_image_b64 is None or match_face_vector is None or template_vector is None:
        raise ValueError(f"identity runtime unavailable: {IDENTITY_RUNTIME_ERROR}")

    gallery = list_identity_gallery("face")
    image_b64 = _extract_image_b64(row)
    if image_b64:
        try:
            return match_face_image_b64(
                image_b64,
                gallery,
                detector_model_path=FACE_DETECTOR_MODEL,
                detect_face=as_bool(row.get("detect_face"), True),
                score_threshold=FACE_DETECT_SCORE_THRESHOLD,
                recognized_threshold=FACE_MATCH_RECOGNIZED_THRESHOLD,
                candidate_threshold=FACE_MATCH_CANDIDATE_THRESHOLD,
            )
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"face match failed: {e}") from e

    template = row.get("template") if isinstance(row.get("template"), dict) else {}
    vector = template_vector(template)
    if vector is None:
        raise ValueError("face match requires image_b64 or template vector")
    return match_face_vector(
        vector,
        gallery,
        recognized_threshold=FACE_MATCH_RECOGNIZED_THRESHOLD,
        candidate_threshold=FACE_MATCH_CANDIDATE_THRESHOLD,
    )


def get_session(session_id: str):
    if not session_id:
        return None
    with db_connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
    obj = row_to_dict(row)
    if obj:
        obj["auth_methods"] = json_loads_default(obj.pop("auth_methods_json", "[]"), [])
        obj["emotion"] = json_loads_default(obj.pop("emotion_json", "{}"), {})
    return obj


def get_current_session():
    ts = now_ms()
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT *
              FROM sessions
             WHERE expires_ts >= ?
             ORDER BY last_seen_ts DESC
             LIMIT 1
            """,
            (ts,),
        ).fetchone()
    obj = row_to_dict(row)
    if obj:
        obj["auth_methods"] = json_loads_default(obj.pop("auth_methods_json", "[]"), [])
        obj["emotion"] = json_loads_default(obj.pop("emotion_json", "{}"), {})
    return obj


def upsert_session(row: dict):
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    ts = now_ms()
    subject_id = str(row.get("actor_subject_id") or row.get("subject_id") or "")
    subject = get_subject(subject_id) if subject_id else None
    if subject_id and subject is None:
        raise ValueError("subject not found")
    role = str(row.get("role") or (subject or {}).get("role") or "unknown")
    auth_methods = row.get("auth_methods") if isinstance(row.get("auth_methods"), list) else []
    assurance_level = str(row.get("assurance_level") or "none")
    identity_state = str(row.get("identity_state") or ("recognized" if subject else "unknown"))
    emotion = row.get("emotion") if isinstance(row.get("emotion"), dict) else {}
    session_id = str(row.get("session_id") or "")
    if not session_id:
        current = get_current_session()
        if current and current.get("actor_subject_id", "") == subject_id and current.get("identity_state", "") == identity_state:
            session_id = current["session_id"]
        else:
            session_id = make_id("sess")
    expires_ts = as_int(row.get("expires_ts"), ts + SESSION_TTL_MS)
    with db_connect() as conn:
        old = conn.execute("SELECT created_ts FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        created_ts = as_int(old["created_ts"], ts) if old else ts
        conn.execute(
            """
            INSERT INTO sessions
                (session_id, actor_subject_id, role, auth_methods_json, assurance_level,
                 identity_state, emotion_json, created_ts, last_seen_ts, expires_ts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                actor_subject_id = excluded.actor_subject_id,
                role = excluded.role,
                auth_methods_json = excluded.auth_methods_json,
                assurance_level = excluded.assurance_level,
                identity_state = excluded.identity_state,
                emotion_json = excluded.emotion_json,
                last_seen_ts = excluded.last_seen_ts,
                expires_ts = excluded.expires_ts
            """,
            (
                session_id,
                subject_id,
                role,
                json_dumps_compact(auth_methods),
                assurance_level,
                identity_state,
                json_dumps_compact(emotion),
                created_ts,
                ts,
                expires_ts,
            ),
        )
    return get_session(session_id)


def create_session_from_observation(row: dict):
    identity = row.get("identity") if isinstance(row, dict) and isinstance(row.get("identity"), dict) else {}
    emotion = row.get("emotion") if isinstance(row, dict) and isinstance(row.get("emotion"), dict) else {}
    subject_id = str(identity.get("subject_id") or row.get("subject_id") or "")
    if subject_id and not get_subject(subject_id):
        subject_id = ""
    confidence = as_float(identity.get("confidence"), 0.0)
    identity_state = str(identity.get("identity_state") or ("recognized" if subject_id else "unknown"))
    if not subject_id:
        if identity_state in ("no_gallery", "disabled", "match_error"):
            return get_current_session() or {}
        identity_state = "unknown"
    assurance_level = str(identity.get("assurance_level") or "")
    if not assurance_level:
        if identity_state == "recognized" and subject_id and confidence >= 0.90:
            assurance_level = "high"
        elif identity_state == "recognized" and subject_id and confidence >= 0.82:
            assurance_level = "medium"
        elif identity_state in ("recognized", "candidate") and subject_id and confidence >= 0.60:
            assurance_level = "low"
        else:
            assurance_level = "none"
    auth_methods = identity.get("auth_methods") if isinstance(identity.get("auth_methods"), list) else []
    if not auth_methods and assurance_level not in ("none", ""):
        auth_methods = [str(identity.get("auth_method") or identity.get("type") or "face")]
    return upsert_session({
        "session_id": row.get("session_id", ""),
        "actor_subject_id": subject_id,
        "auth_methods": auth_methods,
        "assurance_level": assurance_level,
        "identity_state": identity_state,
        "emotion": emotion,
    })
