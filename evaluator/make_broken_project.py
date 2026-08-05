#!/usr/bin/env python3
"""Generate or reset the broken project workspace for model evaluation.

Bug injection strategy: bugs are embedded *inside* the original function
bodies using targeted text replacements, rather than appended as
overriding re-definitions at file end.  This makes the broken code look
like a real project with subtle development shortcuts, not an obvious
"comment out the override" puzzle.

Four defect categories:
  1. auth.py       – plaintext password storage + session bypass
  2. gateway.py    – authorization / authentication shortcuts
  3. sleep_importer – unscoped CSV chooses the wrong default bed
  4. care_events   – incomplete skeleton (missing fields, no routes, no context)

One incomplete feature:
  5. esp32/testpro4 – Wi-Fi + MQTT (巴法云) stripped, needs re-implementation

Required deliverable:
  - PULL_REQUEST_TEMPLATE.md – developer writes implementation notes for consistent PR review
"""
import argparse
import os
import shutil
import subprocess
import stat
from pathlib import Path


MODEL_EVAL = Path(__file__).resolve().parents[1]
WORKSPACE = MODEL_EVAL / "workspace"
EVALUATOR = MODEL_EVAL / "evaluator"
SEED = EVALUATOR / "broken_backup" / "project2_broken_seed"
TASK_PROJECT = WORKSPACE / "project2_task"


def ensure_inside_model_eval(path: Path):
    resolved = path.resolve()
    base = MODEL_EVAL.resolve()
    if base not in resolved.parents and resolved != base:
        raise RuntimeError(f"refusing to operate outside model_eval: {resolved}")


def ignore_names(src, names):
    ignored = set()
    src_path = Path(src)
    for name in names:
        p = src_path / name
        if name == "MODEL_EVAL_PROJECT_SPEC.md":
            ignored.add(name)
        if name in {".git", "__pycache__", ".pytest_cache", ".mypy_cache"}:
            ignored.add(name)
        try:
            resolved = p.resolve()
            model_eval = MODEL_EVAL.resolve()
            if resolved == model_eval:
                ignored.add(name)
        except OSError:
            pass
        if name == "build" and p.is_dir():
            ignored.add(name)
        if name.endswith((".pyc", ".pyo", ".db", ".sqlite", ".sqlite3", ".log")):
            ignored.add(name)
    return ignored


def _rmtree_onexc(func, path, exc_info):
    """Allow Windows cleanup of read-only git object files."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        raise exc_info[1]


def remove_tree(path: Path):
    """Remove a directory tree, handling read-only files on Windows."""
    try:
        shutil.rmtree(path, onexc=_rmtree_onexc)
    except TypeError:
        shutil.rmtree(path, onerror=lambda func, p, exc_info: _rmtree_onexc(func, p, exc_info))


def copy_clean_project(src: Path, dst: Path):
    ensure_inside_model_eval(dst)
    src = src.resolve()
    model_eval = MODEL_EVAL.resolve()
    if src == model_eval or model_eval in src.parents:
        raise RuntimeError(f"source project must be outside evaluator root: {src}")
    if not src.exists():
        raise RuntimeError(f"source project not found: {src}")
    if dst.exists():
        remove_tree(dst)
    shutil.copytree(src, dst, ignore=ignore_names)


# ---------------------------------------------------------------------------
# Git initialization — make the workspace look like a real project checkout
# ---------------------------------------------------------------------------

PROJECT_GITIGNORE = """\
# Python
__pycache__/
*.py[cod]
*$py.class

# Project databases
data/*.db
*.db

# Build artifacts
build/
*.o
*.elf
*.bin
*.map

# Logs
*.log

# OS
.DS_Store
Thumbs.db
desktop.ini

# IDE
.vs/
.idea/
*.swp
*~
"""


PR_TEMPLATE_CONTENT = """# Pull Request 提测说明 (Pull Request Template)

请用本文件记录你的最终实现说明。合并分支时，CI 系统和 Reviewer 会自动对本 PR 自检报告、变更 diff 进行交叉一致性校验。

## 初始自检诊断

请记录修改前运行的命令和关键结果：

- `python tests\\run_public_tests.py project2_task`
- `python tools\\run_debug_probe.py project2_task`

## 修改的文件列表

待填写。

## 架构调整与模块设计

待填写。

## 安全边界及鉴权设计

待填写。

## 睡眠 CSV 无 room/bed 时的特殊处理

待填写。

## care_event 实现细节

待填写。

## ESP32-S3 固件接口对齐说明

待填写。

## 本地测试与编译验证结果

请记录修复后运行的命令和结果，至少包括：

- `python tests\\run_public_tests.py project2_task`
- `python tools\\run_debug_probe.py project2_task`
- `python tools\\run_espidf_build.py project2_task` 编译结果或失败位置说明

## 未验证的残留技术债与风险

待填写。
"""


def write_gitignore(project: Path):
    """Write a .gitignore suitable for the candidate project."""
    gi = project / ".gitignore"
    gi.write_text(PROJECT_GITIGNORE, encoding="utf-8")


def write_pr_template(project: Path):
    """Write the candidate PULL_REQUEST_TEMPLATE.md template."""
    (project / "PULL_REQUEST_TEMPLATE.md").write_text(PR_TEMPLATE_CONTENT, encoding="utf-8")


def _git(*args, cwd: Path):
    """Run a git command.  Returns the CompletedProcess."""
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=120,
    )


def git_tree_hash(project: Path) -> str:
    """Return the committed tree hash for a repo, or empty string on failure."""
    result = _git("rev-parse", "HEAD^{tree}", cwd=project)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def init_git_repo(project: Path):
    """Initialize a git repo with one commit ('Initial commit').

    If a repo already exists and is clean, this is a no-op.
    If git is not installed, prints a warning and continues.
    """
    if (project / ".git").is_dir():
        # Repo already exists — check if working tree is clean
        status = _git("status", "--porcelain", cwd=project)
        if status.returncode == 0 and not status.stdout.strip():
            print(f"[make] git repo already exists and is clean at {project}")
            return
        # Dirty tree — just stage and commit
        _git("add", "-A", cwd=project)
        _git("commit", "-m", "Reset to initial commit", "--allow-empty", cwd=project)
        _git("tag", "-f", "project2-v4-broken-seed", cwd=project)
        _git("tag", "-f", "project2-v2-broken-seed", cwd=project)
        print(f"[make] git: committed dirty tree at {project}")
        return

    # No repo yet — init from scratch
    result = _git("init", cwd=project)
    if result.returncode != 0:
        print(f"[make] WARNING: git init failed: {result.stderr.strip()}")
        return
    # Set a local identity so commit works without global git config
    _git("config", "user.email", "dev@project2.local", cwd=project)
    _git("config", "user.name", "Project2 Dev", cwd=project)
    _git("add", "-A", cwd=project)
    _git("commit", "-m", "Initial commit", cwd=project)
    _git("tag", "-f", "project2-v4-broken-seed", cwd=project)
    _git("tag", "-f", "project2-v2-broken-seed", cwd=project)
    print(f"[make] git: initialized repo with 'Initial commit' at {project}")


def git_reset_workspace(project: Path) -> bool:
    """Fast reset: restore the workspace to the 'Initial commit' state.

    Returns True if successful, False if git is unavailable or the repo
    is missing (caller should fall back to shutil copy).
    """
    git_dir = project / ".git"
    if not git_dir.is_dir():
        return False

    if (SEED / ".git").is_dir():
        seed_status = _git("status", "--porcelain", cwd=SEED)
        if seed_status.returncode != 0 or seed_status.stdout.strip():
            print("[make] seed git tree is dirty or unreadable; falling back to copy")
            return False

        seed_tree = git_tree_hash(SEED)
        workspace_tree = git_tree_hash(project)
        if seed_tree and workspace_tree and seed_tree != workspace_tree:
            print("[make] workspace initial tree differs from seed; falling back to copy")
            return False

    # Discard tracked file changes
    r1 = _git("checkout", ".", cwd=project)
    # Remove untracked files and directories
    r2 = _git("clean", "-fdx", cwd=project)

    if r1.returncode != 0 or r2.returncode != 0:
        print(f"[make] WARNING: git reset failed, falling back to copy")
        return False

    print(f"[make] git: workspace reset to 'Initial commit' via checkout + clean")
    return True


def _replace_once(path: Path, old: str, new: str, label: str = ""):
    """Replace *old* with *new* in file, exactly once.  Fail if not found."""
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        tag = f" ({label})" if label else ""
        print(f"[make] WARNING: replacement target not found{tag}: {old[:80]}...")
        return
    if count > 1:
        tag = f" ({label})" if label else ""
        print(f"[make] WARNING: replacement target found {count} times{tag}, replacing first: {old[:80]}...")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Bug 1: auth.py – plaintext password + session bypass
# ---------------------------------------------------------------------------

def break_auth(project: Path):
    auth = project / "gateway" / "auth.py"
    text = auth.read_text(encoding="utf-8")

    # 1a. _password_hash: add a "bootstrap fast-path" that returns the
    #     password verbatim when no external salt is provided.
    text = text.replace(
        '    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)\n'
        '    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)\n'
        '    return salt.hex(), digest.hex()',
        '    # No salt yet = skip hashing for now, will re-hash on first real login.\n'
        '    if not salt_hex:\n'
        '        return "", password\n'
        '    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)\n'
        '    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)\n'
        '    return salt.hex(), digest.hex()',
        1,
    )

    # 1b. create_admin_account: pass empty salt to trigger the fast-path
    #     (stores password in plaintext).
    text = text.replace(
        '    salt, digest = _password_hash(password)\n',
        '    salt, digest = _password_hash(password, "")\n',
        1,
    )

    # 1c. admin_account_exists: always return False so setup can be re-run.
    text = text.replace(
        '    with db_connect() as conn:\n'
        "        row = conn.execute(\"SELECT 1 FROM admin_accounts WHERE status = 'active' LIMIT 1\").fetchone()\n"
        '    return row is not None',
        '    # TODO: check DB — always allow setup for now so first deploy works.\n'
        '    return False',
        1,
    )

    # 1d. login_admin_account: use != instead of hmac.compare_digest
    #     (works because both sides are the plaintext password).
    text = text.replace(
        '    if not hmac.compare_digest(digest, str(account["password_hash"])):',
        '    if digest != str(account["password_hash"]):',
        1,
    )

    # 1e. get_admin_http_session: match any active session instead of
    #     verifying the exact token hash.
    text = text.replace(
        '    ts = now_ms()\n'
        '    token_hash = _token_hash(token)\n'
        '    with db_connect() as conn:\n'
        '        row = conn.execute(\n'
        '            """\n'
        '            SELECT s.*, a.subject_id\n'
        '              FROM admin_http_sessions s\n'
        '              JOIN admin_accounts a ON a.username = s.username\n'
        "             WHERE s.token_hash = ? AND s.expires_ts >= ? AND a.status = 'active'\n"
        '            """,\n'
        '            (token_hash, ts),\n'
        '        ).fetchone()\n'
        '        if not row:\n'
        '            return None',
        '    ts = now_ms()\n'
        '    # Workers call APIs without a cookie jar — just grab any active session.\n'
        '    with db_connect() as conn:\n'
        '        row = conn.execute(\n'
        '            """\n'
        '            SELECT s.*, a.subject_id\n'
        '              FROM admin_http_sessions s\n'
        '              JOIN admin_accounts a ON a.username = s.username\n'
        "             WHERE s.expires_ts >= ? AND a.status = 'active'\n"
        '             LIMIT 1\n'
        '            """,\n'
        '            (ts,),\n'
        '        ).fetchone()\n'
        '        if not row:\n'
        '            return None',
        1,
    )

    # 1f. Also fix the UPDATE in get_admin_http_session to use _token_hash(token)
    #     instead of the removed variable (so the code compiles).
    text = text.replace(
        '            "UPDATE admin_http_sessions SET last_seen_ts = ? WHERE token_hash = ?",\n'
        '            (ts, token_hash),',
        '            "UPDATE admin_http_sessions SET last_seen_ts = ? WHERE token_hash = ?",\n'
        '            (ts, _token_hash(token)),',
        1,
    )

    auth.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Bug 2: gateway.py – authorization / authentication shortcuts
# ---------------------------------------------------------------------------

def break_gateway(project: Path):
    gateway = project / "gateway" / "gateway.py"
    text = gateway.read_text(encoding="utf-8")

    # 2a. session_is_authenticated: treat sessions with identity_state
    #     "unknown" as authenticated (for "intra-service compatibility").
    text = text.replace(
        '    if identity_state != "recognized":\n'
        '        return False\n'
        '    if assurance_level in ("none", ""):\n'
        '        return False\n'
        '    return True',
        '    # Workers / voice loop don\'t always do face auth, so skip the check here.\n'
        '    if identity_state in ("unknown", ""):\n'
        '        return True\n'
        '    if assurance_level in ("none", ""):\n'
        '        return False\n'
        '    return True',
        1,
    )

    # 2b. actor_can_access_target: when actor_subject is None, default
    #     to allowing access (for "local service path").
    text = text.replace(
        '    if not actor_subject:\n'
        '        return False',
        '    if not actor_subject:\n'
        '        # No actor info = probably an internal worker call, just allow it.\n'
        '        return True',
        1,
    )

    # 2c. _authorized_for_api: allow all local requests (remove path filter).
    text = text.replace(
        '    def _authorized_for_api(self, path: str) -> bool:\n'
        '        if self._admin_session() is not None:\n'
        '            return True\n'
        '        return self._is_local_request() and self._path_allows_local_service(path)',
        '    def _authorized_for_api(self, path: str) -> bool:\n'
        '        if self._admin_session() is not None:\n'
        '            return True\n'
        '        if self._is_local_request():\n'
        '            return True\n'
        '        return False',
        1,
    )

    gateway.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Bug 3: sleep_importer – unscoped rows choose the wrong default bed
# ---------------------------------------------------------------------------

def break_sleep_import(project: Path):
    path = project / "gateway" / "sleep_importer.py"
    text = path.read_text(encoding="utf-8")
    if "beds[-1]" in text and "beds[0]" in text:
        return
    text = text.replace(
        "        return [beds[0]] if beds else []\n",
        "        if SLEEP_IMPORT_UNSCOPED_POLICY == 'first':\n"
        "            # Default policy: use the first bed in the rotation.\n"
        "            # Note: beds are stored in insertion order from BEDS config.\n"
        "            return [beds[-1]] if beds else []\n"
        "        # Unrecognized policy — for safety, import nothing rather than fanning out.\n"
        "        return []\n",
    )
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Bug 4: care_events – replace complete module with buggy skeleton
# ---------------------------------------------------------------------------

CARE_EVENTS_SKELETON = '''"""Care event tracking for nursing actions.

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
'''

CARE_EVENTS_TABLE_IN_DB = '''
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
'''


def break_care_events(project: Path):
    """Replace care_events.py with a buggy skeleton and add an incomplete
    care_events table to db.py.

    The skeleton has:
      - Basic CRUD functions (create_care_event, list_care_events)
      - Missing table fields (severity, source, created_by, ts)
      - No auth check on create
      - A stub build_care_events_context that returns empty
      - No routes wired into gateway.py
      - No context integration
    """
    care_path = project / "gateway" / "care_events.py"
    care_path.write_text(CARE_EVENTS_SKELETON, encoding="utf-8")

    # Add incomplete care_events table to db.py
    db_path = project / "gateway" / "db.py"
    db_text = db_path.read_text(encoding="utf-8")
    if "care_events" not in db_text:
        # Insert before the closing """ of the executescript
        db_text = db_text.replace(
            '            CREATE INDEX IF NOT EXISTS idx_admin_http_sessions_expires\n'
            '                ON admin_http_sessions(expires_ts, last_seen_ts DESC);\n'
            '            """',
            '            CREATE INDEX IF NOT EXISTS idx_admin_http_sessions_expires\n'
            '                ON admin_http_sessions(expires_ts, last_seen_ts DESC);\n'
            + CARE_EVENTS_TABLE_IN_DB +
            '            """',
            1,
        )
        db_path.write_text(db_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Bug 5: ESP32 — strip Wi-Fi + MQTT code, leave as TODO stubs
# ---------------------------------------------------------------------------

def break_esp32(project: Path):
    """Ensure the ESP32 firmware is in its 'incomplete' state.

    The workspace already ships with Wi-Fi + MQTT code removed and TODO
    markers in place.  If the --source project happens to contain a
    completed ESP32 implementation, this function strips it back to the
    incomplete state by removing the network-related includes, code,
    and CMake dependencies.

    However, the primary mechanism is that the broken seed already
    contains the stripped version, so this function only acts as a
    safety net.
    """
    main_cpp = project / "esp32" / "testpro4" / "main" / "main.cpp"
    if not main_cpp.exists():
        return

    text = main_cpp.read_text(encoding="utf-8")

    # If the file already has TODO(v4) markers, it's already broken
    if "TODO(v4)" in text:
        return

    # If we get here, the source project has a complete ESP32 implementation.
    # Strip it: remove Wi-Fi/MQTT includes and code, add TODO comments.
    # This is a safety net — the broken seed should already be correct.

    # Remove MQTT/Wi-Fi includes
    for inc in [
        '#include "esp_event.h"\n',
        '#include "esp_netif.h"\n',
        '#include "esp_wifi.h"\n',
        '#include "mqtt_client.h"\n',
        '#include "mbedtls/base64.h"\n',
    ]:
        text = text.replace(inc, "")

    # Replace init_wifi_and_mqtt() call with a TODO comment
    text = text.replace(
        "    init_wifi_and_mqtt();\n",
        "    // TODO(v4): start restored Wi-Fi + MQTT network backhaul here.\n",
    )

    # Replace bemfa_mqtt_publish_binary calls with TODO comments
    text = text.replace(
        "    bemfa_mqtt_publish_binary(topic, payload, len);\n",
        "    // TODO(v4): publish this payload through the network backhaul.\n",
    )
    for line in [
        "    bemfa_mqtt_publish_binary(s_topic_mlx1, (const uint8_t *)temp_buf1, total);\n",
        "    bemfa_mqtt_publish_binary(s_topic_mlx2, (const uint8_t *)temp_buf2, total);\n",
    ]:
        text = text.replace(
            line,
            "    // TODO(v4): publish this MLX payload through the network backhaul.\n",
        )

    main_cpp.write_text(text, encoding="utf-8")

    # Strip CMakeLists.txt dependencies
    cmake = project / "esp32" / "testpro4" / "main" / "CMakeLists.txt"
    if cmake.exists():
        cmake_text = cmake.read_text(encoding="utf-8")
        # Remove network dependencies if they're in REQUIRES
        for dep in ["esp_wifi", "esp_netif", "esp_event", "lwip", "mqtt", "mbedtls"]:
            # Remove the dependency from REQUIRES list
            cmake_text = cmake_text.replace(f"        {dep}\n", "")
        cmake.write_text(cmake_text, encoding="utf-8")

    # Strip idf_component.yml mqtt dependency
    yml = project / "esp32" / "testpro4" / "main" / "idf_component.yml"
    if yml.exists():
        yml_text = yml.read_text(encoding="utf-8")
        yml_text = yml_text.replace(
            "  espressif/mqtt: '*'\n",
            "  # TODO(v4): add the MQTT client component dependency when network backhaul is restored.\n",
        )
        yml.write_text(yml_text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Seed generation and workspace reset
# ---------------------------------------------------------------------------

def make_seed(source: Path):
    copy_clean_project(source, SEED)
    break_auth(SEED)
    break_gateway(SEED)
    break_sleep_import(SEED)
    break_care_events(SEED)
    break_esp32(SEED)
    write_pr_template(SEED)
    write_gitignore(SEED)
    init_git_repo(SEED)


def reset_workspace():
    ensure_inside_model_eval(TASK_PROJECT)
    if not SEED.exists():
        raise RuntimeError(
            f"broken seed not found: {SEED}. "
            "Run this script with --source <completed_project> once to create it."
        )

    # Fast path: if workspace already has a git repo, reset in-place
    if git_reset_workspace(TASK_PROJECT):
        return

    # Slow path: full copy from seed
    if TASK_PROJECT.exists():
        remove_tree(TASK_PROJECT)
    shutil.copytree(SEED, TASK_PROJECT, ignore=ignore_names)
    write_gitignore(TASK_PROJECT)
    init_git_repo(TASK_PROJECT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="completed Project2 source tree used to refresh the broken seed before reset",
    )
    args = parser.parse_args()

    print(f"[make] eval_root={MODEL_EVAL}")
    if args.source is not None:
        print(f"[make] refreshing seed from source={args.source.resolve()}")
        make_seed(args.source)
    else:
        print(f"[make] using existing seed={SEED}")
    reset_workspace()
    print(f"[make] workspace={TASK_PROJECT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
