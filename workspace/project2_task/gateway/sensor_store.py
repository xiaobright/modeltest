import threading
from collections import defaultdict, deque
import time

from bed_config import ALL_KINDS
from config import HISTORY_MINUTES, HISTORY_TTL_MS, KIND_TTL_MS
from utils import as_int, now_ms


history = defaultdict(lambda: defaultdict(deque))
lock = threading.Lock()


def _bed_key(room: str, bed: str) -> tuple:
    return (room, bed)


def prune(deq: deque, ttl_ms: int):
    cutoff = now_ms() - ttl_ms
    while deq and int(deq[0].get("ts", 0) or 0) < cutoff:
        deq.popleft()


def append_item(room: str, bed: str, kind: str, payload: dict):
    if kind not in ALL_KINDS or not isinstance(payload, dict):
        return

    ts = payload.get("ts")
    try:
        ts = int(ts)
    except Exception:
        ts = now_ms()

    item = {"ts": ts, "room": room, "bed": bed}
    item.update(payload)

    key = _bed_key(room, bed)
    with lock:
        deq = history[key][kind]
        deq.append(item)
        prune(deq, KIND_TTL_MS.get(kind, HISTORY_TTL_MS))


def replace_items(room: str, bed: str, kind: str, items: list[dict]):
    if kind not in ALL_KINDS:
        return
    normalized = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ts = as_int(it.get("ts"), now_ms())
        row = {"ts": ts, "room": room, "bed": bed}
        row.update(it)
        normalized.append(row)
    normalized.sort(key=lambda x: as_int(x.get("ts"), 0))
    key = _bed_key(room, bed)
    with lock:
        history[key][kind] = deque(normalized)
        prune(history[key][kind], KIND_TTL_MS.get(kind, HISTORY_TTL_MS))


def latest_one(room: str, bed: str, kind: str):
    key = _bed_key(room, bed)
    with lock:
        deq = history[key][kind]
        if not deq:
            return None
        return deq[-1]


def list_latest(room: str, bed: str, kind: str, limit: int = 100, record: str = ""):
    limit = max(1, min(limit, 2000))
    key = _bed_key(room, bed)
    with lock:
        data = list(history[key][kind])
    if record:
        data = [x for x in data if str(x.get("record", "")) == record]
    if not data:
        return []
    return data[-limit:]


def series(room: str, bed: str, kind: str, minutes=30, step_s=10):
    minutes = max(1, min(int(minutes), 120))
    step_s = max(1, min(int(step_s), 60))
    window_ms = minutes * 60 * 1000
    cutoff = now_ms() - window_ms

    key = _bed_key(room, bed)
    with lock:
        data = list(history[key][kind])

    data = [x for x in data if int(x.get("ts", 0) or 0) >= cutoff]
    if not data:
        return []

    data.sort(key=lambda x: int(x.get("ts", 0) or 0))
    out = []
    idx = 0
    t = int(data[0]["ts"])
    end = int(data[-1]["ts"])
    step_ms = step_s * 1000
    last = None

    while t <= end:
        while idx < len(data) and int(data[idx].get("ts", 0) or 0) <= t:
            last = data[idx]
            idx += 1
        if last is not None:
            out.append(last)
        t += step_ms

    return out


def to_timestr(ts_ms: int):
    lt = time.localtime(ts_ms / 1000)
    return time.strftime("%H:%M:%S", lt)


def source_online(ts_last, ttl_ms=15000):
    if not ts_last:
        return "offline"
    return "online" if (now_ms() - int(ts_last)) <= ttl_ms else "offline"
