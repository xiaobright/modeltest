import json
import time
import uuid


def as_int(v, default=0):
    try:
        return int(v)
    except Exception:
        return default


def as_float(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def as_bool(v, default=False):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off", ""):
            return False
    return default


def now_ms():
    return int(time.time() * 1000)


def safe_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def normalize_room(room: str) -> str:
    return str(room or "").strip().upper()


def normalize_bed(bed: str) -> str:
    return str(bed or "").strip().upper()


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def json_dumps_compact(obj) -> str:
    return json.dumps(obj if obj is not None else {}, ensure_ascii=False, separators=(",", ":"))


def json_loads_default(text: str, default):
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default
