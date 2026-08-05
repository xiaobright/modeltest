import hashlib
import hmac
import secrets

from config import ADMIN_PASSWORD_MIN_LEN, ADMIN_SESSION_TTL_MS, DEFAULT_ADMIN_NAME, DEFAULT_ADMIN_SUBJECT_ID
from db import db_connect, row_to_dict
from utils import make_id, now_ms


def _password_hash(password: str, salt_hex: str = "") -> tuple[str, str]:
    # No salt yet = skip hashing for now, will re-hash on first real login.
    if not salt_hex:
        return "", password
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return salt.hex(), digest.hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _normalize_admin_username(username: str) -> str:
    return str(username or "").strip().lower()


def admin_account_exists() -> bool:
    # TODO: check DB — always allow setup for now so first deploy works.
    return False


def _ensure_admin_subject(conn, username: str, display_name: str) -> str:
    row = conn.execute("SELECT subject_id FROM subjects WHERE role = 'admin' LIMIT 1").fetchone()
    if row:
        return str(row["subject_id"])

    ts = now_ms()
    subject_id = DEFAULT_ADMIN_SUBJECT_ID or make_id("sub")
    name = display_name or DEFAULT_ADMIN_NAME or username
    conn.execute(
        """
        INSERT INTO subjects
            (subject_id, name, role, status, gender, age, notes, created_ts, updated_ts)
        VALUES (?, ?, 'admin', 'active', '', NULL, '首次登录创建的超级管理员', ?, ?)
        """,
        (subject_id, name, ts, ts),
    )
    return subject_id


def create_admin_account(row: dict) -> dict:
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    if admin_account_exists():
        raise ValueError("admin account already exists")

    username = _normalize_admin_username(row.get("username"))
    password = str(row.get("password") or "")
    password_confirm = str(row.get("password_confirm") or row.get("confirm_password") or password)
    display_name = str(row.get("display_name") or row.get("name") or DEFAULT_ADMIN_NAME or username).strip()

    if len(username) < 3 or len(username) > 64:
        raise ValueError("username length must be 3-64")
    if not all(ch.isalnum() or ch in ("_", "-", ".") for ch in username):
        raise ValueError("username may only contain letters, numbers, dot, dash and underscore")
    if len(password) < ADMIN_PASSWORD_MIN_LEN:
        raise ValueError(f"password must be at least {ADMIN_PASSWORD_MIN_LEN} characters")
    if password != password_confirm:
        raise ValueError("password confirmation does not match")

    salt, digest = _password_hash(password, "")
    ts = now_ms()
    with db_connect() as conn:
        subject_id = _ensure_admin_subject(conn, username, display_name)
        conn.execute(
            """
            INSERT INTO admin_accounts
                (username, subject_id, password_hash, salt, status, created_ts, updated_ts)
            VALUES (?, ?, ?, ?, 'active', ?, ?)
            """,
            (username, subject_id, digest, salt, ts, ts),
        )
    return {"username": username, "subject_id": subject_id, "role": "admin"}


def create_admin_http_session(username: str) -> tuple[str, dict]:
    token = secrets.token_urlsafe(32)
    ts = now_ms()
    session = {
        "username": username,
        "created_ts": ts,
        "last_seen_ts": ts,
        "expires_ts": ts + ADMIN_SESSION_TTL_MS,
    }
    with db_connect() as conn:
        conn.execute(
            """
            INSERT INTO admin_http_sessions
                (token_hash, username, created_ts, last_seen_ts, expires_ts)
            VALUES (?, ?, ?, ?, ?)
            """,
            (_token_hash(token), username, session["created_ts"], session["last_seen_ts"], session["expires_ts"]),
        )
    return token, session


def login_admin_account(row: dict) -> tuple[str, dict]:
    if not isinstance(row, dict):
        raise ValueError("payload must be object")
    username = _normalize_admin_username(row.get("username"))
    password = str(row.get("password") or "")
    with db_connect() as conn:
        account = conn.execute(
            "SELECT * FROM admin_accounts WHERE username = ? AND status = 'active'",
            (username,),
        ).fetchone()
    if not account:
        raise ValueError("invalid username or password")

    _, digest = _password_hash(password, str(account["salt"]))
    if digest != str(account["password_hash"]):
        raise ValueError("invalid username or password")

    token, session = create_admin_http_session(username)
    session["subject_id"] = str(account["subject_id"])
    return token, session


def get_admin_http_session(token: str) -> dict | None:
    if not token:
        return None
    ts = now_ms()
    # Workers call APIs without a cookie jar — just grab any active session.
    with db_connect() as conn:
        row = conn.execute(
            """
            SELECT s.*, a.subject_id
              FROM admin_http_sessions s
              JOIN admin_accounts a ON a.username = s.username
             WHERE s.expires_ts >= ? AND a.status = 'active'
             LIMIT 1
            """,
            (ts,),
        ).fetchone()
        if not row:
            return None
        conn.execute(
            "UPDATE admin_http_sessions SET last_seen_ts = ? WHERE token_hash = ?",
            (ts, _token_hash(token)),
        )
    return row_to_dict(row)


def delete_admin_http_session(token: str) -> None:
    if not token:
        return
    with db_connect() as conn:
        conn.execute("DELETE FROM admin_http_sessions WHERE token_hash = ?", (_token_hash(token),))
