import base64
import threading
from collections import defaultdict, deque

from config import ESP_ONLINE_TTL_MS, ESP_REQUIRED_STREAMS, ESP_SET_TIMEOUT_MS, ESP_STORE_DEPTH
from sensor_store import _bed_key, source_online
from utils import now_ms


_esp_state = defaultdict(lambda: {
    'sets': deque(maxlen=ESP_STORE_DEPTH),
    'current_set': None,
    'last_packet': None,
    'last_seen_ms': 0,
    'bytes_rx': 0,
    'set_seq': 0,
    'crc_fail': 0,
})
esp_lock = threading.Lock()


def _get_esp_state(room: str, bed: str):
    key = _bed_key(room, bed)
    return _esp_state[key]


def new_esp_set(now: int, peer: str, seq: int):
    return {
        "set_id": seq,
        "ts_start": now,
        "ts_complete": 0,
        "peer": peer,
        "frames": {},
    }


def append_esp_packet(room: str, bed: str, sensor_type: int, sensor_id: int,
                       payload: bytes, crc: int, peer: str, crc_ok: bool):
    now = now_ms()
    stream = _esp_stream_key(sensor_type, sensor_id)
    frame = {
        "ts": now,
        "sensor_type": int(sensor_type),
        "sensor_id": int(sensor_id),
        "stream": stream,
        "payload_len": len(payload),
        "crc": int(crc),
        "crc_ok": bool(crc_ok),
        "peer": peer,
        "payload": payload,
    }

    state = _get_esp_state(room, bed)
    with esp_lock:
        state["last_seen_ms"] = now
        state["last_packet"] = {
            "ts": now,
            "sensor_type": int(sensor_type),
            "sensor_id": int(sensor_id),
            "stream": stream,
            "payload_len": len(payload),
            "crc": int(crc),
            "crc_ok": bool(crc_ok),
            "peer": peer,
        }

        cur = state["current_set"]
        if cur is not None:
            if now - int(cur.get("ts_start", now)) > ESP_SET_TIMEOUT_MS:
                state["set_seq"] += 1
                state["current_set"] = new_esp_set(now, peer, state["set_seq"])
                cur = state["current_set"]

        if cur is None:
            state["set_seq"] += 1
            state["current_set"] = new_esp_set(now, peer, state["set_seq"])
            cur = state["current_set"]

        cur["frames"][stream] = frame

        if all(k in cur["frames"] for k in ESP_REQUIRED_STREAMS):
            cur["ts_complete"] = now
            state["sets"].append(cur)
            state["current_set"] = None


def _esp_stream_key(sensor_type: int, sensor_id: int):
    st = int(sensor_type)
    sid = int(sensor_id)
    if st == 0x01 and sid == 0x01:
        return "mlx1"
    if st == 0x01 and sid == 0x02:
        return "mlx2"
    if st == 0x02 and sid == 0x01:
        return "tof1"
    if st == 0x02 and sid == 0x02:
        return "tof2"
    return "unknown"


def build_esp_set_view(one_set, include_payload=False):
    if not one_set:
        return {}

    frames = {}
    for stream in ESP_REQUIRED_STREAMS:
        item = one_set.get("frames", {}).get(stream)
        if not item:
            continue
        row = {
            "ts": int(item.get("ts", 0)),
            "sensor_type": int(item.get("sensor_type", 0)),
            "sensor_id": int(item.get("sensor_id", 0)),
            "payload_len": int(item.get("payload_len", 0)),
            "crc": int(item.get("crc", 0)),
            "crc_ok": bool(item.get("crc_ok", False)),
            "peer": item.get("peer", ""),
        }
        if include_payload:
            row["payload_b64"] = base64.b64encode(item.get("payload", b"")).decode("ascii")
        frames[stream] = row

    return {
        "set_id": int(one_set.get("set_id", 0)),
        "ts_start": int(one_set.get("ts_start", 0)),
        "ts_complete": int(one_set.get("ts_complete", 0)),
        "peer": one_set.get("peer", ""),
        "streams": list(frames.keys()),
        "frames": frames,
    }


def get_esp_status(room: str, bed: str):
    state = _get_esp_state(room, bed)
    with esp_lock:
        last_set = state["sets"][-1] if state["sets"] else None
        current_set = state["current_set"]
        last = state["last_packet"]
        last_seen = state["last_seen_ms"]
        set_count = len(state["sets"])
        total_bytes = state["bytes_rx"]
        crc_fail = state["crc_fail"]

    current_streams = []
    current_set_id = 0
    if current_set:
        current_set_id = int(current_set.get("set_id", 0))
        current_streams = sorted(list(current_set.get("frames", {}).keys()))

    online = (now_ms() - int(last_seen)) <= ESP_ONLINE_TTL_MS if last_seen else False

    return {
        "ok": True,
        "room": room,
        "bed": bed,
        "online": online,
        "status": "connected" if online else "disconnected",
        "store_depth": ESP_STORE_DEPTH,
        "cached_sets": set_count,
        "bytes_rx": total_bytes,
        "crc_fail": crc_fail,
        "last_seen_ts": int(last_seen),
        "last_packet": last or {},
        "current_set_id": current_set_id,
        "current_set_streams": current_streams,
        "current_set_ready": len(current_streams) == len(ESP_REQUIRED_STREAMS),
        "last_complete_set": build_esp_set_view(last_set, include_payload=False),
        "ts": now_ms(),
    }


def get_latest_esp_set(room: str, bed: str, include_payload=False):
    state = _get_esp_state(room, bed)
    with esp_lock:
        one_set = state["sets"][-1] if state["sets"] else None
    return build_esp_set_view(one_set, include_payload=include_payload)
