import json
import csv
import os
import socketserver
import socket
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# =====================
# Local TCP ingest config
# =====================
INGEST_HOST = "0.0.0.0"
INGEST_PORT = 9100

# =====================
# ESP TCP binary ingest config
# =====================
ESP_INGEST_HOST = "0.0.0.0"
ESP_INGEST_PORT = 9101
ESP_STORE_DEPTH = max(1, int(os.getenv("ESP_STORE_DEPTH", "1")))

# =====================
# HTTP API config
# =====================
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8765
LOCATION = "default"

# =====================
# Sleep pipeline integration config
# =====================
SLEEP_OUTPUT_DIR = os.path.abspath(
    os.getenv("SLEEP_OUTPUT_DIR", os.path.join(os.path.dirname(__file__), "..", "sleep_deploy_pack", "examples"))
)
SLEEP_EPOCH_FILE = os.path.abspath(os.getenv("SLEEP_EPOCH_FILE", os.path.join(SLEEP_OUTPUT_DIR, "fusion_eeg_final_conf.csv")))
SLEEP_QUALITY_FILE = os.path.abspath(os.getenv("SLEEP_QUALITY_FILE", os.path.join(SLEEP_OUTPUT_DIR, "sleep_quality_per_record.csv")))
SLEEP_IMPORT_INTERVAL_S = max(3, int(os.getenv("SLEEP_IMPORT_INTERVAL_S", "10")))
SLEEP_IMPORT_ENABLED = os.getenv("SLEEP_IMPORT_ENABLED", "1") not in ("0", "false", "False")

DASHBOARD_FILE = os.path.join(os.path.dirname(__file__), "dashboard.html")


def load_dashboard_html():
    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:  # noqa: BLE001
        return (
            "<html><body><h1>Dashboard Missing</h1>"
            f"<p>Cannot load: {DASHBOARD_FILE}</p>"
            f"<p>Error: {e}</p></body></html>"
        )

# =====================
# Data cache (single location)
# =====================
HISTORY_MINUTES = 30
HISTORY_TTL_MS = HISTORY_MINUTES * 60 * 1000
KINDS = (
    "radar",
    "env",
    "audio",
    "sleep_epoch",
    "sleep_quality",
)
KIND_TTL_MS = {
    "sleep_epoch": 48 * 60 * 60 * 1000,
    "sleep_quality": 7 * 24 * 60 * 60 * 1000,
}

history = defaultdict(lambda: deque())  # history[kind] = deque(items)
lock = threading.Lock()

esp_lock = threading.Lock()
esp_packets = deque(maxlen=ESP_STORE_DEPTH)
esp_last_seen_ms = 0
esp_online_ttl_ms = 15000
esp_bytes_rx = 0


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


def sleep_epoch_zero():
    return {
        "record": "",
        "start_s": 0.0,
        "end_s": 0.0,
        "BR_mean": 0.0,
        "BR_std": 0.0,
        "HR_mean": 0.0,
        "HR_std": 0.0,
        "RMSSD": 0.0,
        "SDNN": 0.0,
        "EEG_stage": "W",
        "EEG_conf": 0.0,
        "Sleep_detect": "W",
        "Sleep_W_prob": 0.0,
        "Final_stage": "W",
        "RuleApplied": 0,
        "ts": 0,
    }


def sleep_quality_zero():
    return {
        "record": "",
        "total_h": 0.0,
        "sleep_h": 0.0,
        "W_epochs": 0,
        "N1_epochs": 0,
        "N2_epochs": 0,
        "N3_epochs": 0,
        "REM_epochs": 0,
        "N1_ratio_in_sleep": 0.0,
        "N2_ratio_in_sleep": 0.0,
        "N3_ratio_in_sleep": 0.0,
        "REM_ratio_in_sleep": 0.0,
        "score_valid": 0,
        "duration_score": 0.0,
        "structure_score": 0.0,
        "total_score": 0.0,
        "grade": "数据不足，暂不评分",
        "ts": 0,
    }


def now_ms():
    return int(time.time() * 1000)


def prune(deq: deque, ttl_ms: int):
    cutoff = now_ms() - ttl_ms
    while deq and int(deq[0].get("ts", 0) or 0) < cutoff:
        deq.popleft()


def safe_json_loads(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None


def append_item(kind: str, payload: dict):
    if kind not in KINDS or not isinstance(payload, dict):
        return

    ts = payload.get("ts")
    try:
        ts = int(ts)
    except Exception:
        ts = now_ms()

    item = {"ts": ts}
    item.update(payload)

    with lock:
        deq = history[kind]
        deq.append(item)
        prune(deq, KIND_TTL_MS.get(kind, HISTORY_TTL_MS))


def replace_items(kind: str, items: list[dict]):
    if kind not in KINDS:
        return
    normalized = []
    for it in items:
        if not isinstance(it, dict):
            continue
        ts = as_int(it.get("ts"), now_ms())
        row = {"ts": ts}
        row.update(it)
        normalized.append(row)
    normalized.sort(key=lambda x: as_int(x.get("ts"), 0))
    with lock:
        history[kind] = deque(normalized)
        prune(history[kind], KIND_TTL_MS.get(kind, HISTORY_TTL_MS))


def latest_one(kind: str):
    with lock:
        deq = history[kind]
        if not deq:
            return None
        return deq[-1]


def list_latest(kind: str, limit: int = 100, record: str = ""):
    limit = max(1, min(limit, 2000))
    with lock:
        data = list(history[kind])
    if record:
        data = [x for x in data if str(x.get("record", "")) == record]
    if not data:
        return []
    return data[-limit:]


def series(kind: str, minutes=30, step_s=10):
    """Return a sampled sequence within the latest window."""
    minutes = max(1, min(int(minutes), 120))
    step_s = max(1, min(int(step_s), 60))
    window_ms = minutes * 60 * 1000
    cutoff = now_ms() - window_ms

    with lock:
        data = list(history[kind])

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


def append_esp_packet(sensor_type: int, sensor_id: int, payload_len: int, crc: int, peer: str):
    global esp_last_seen_ms
    item = {
        "ts": now_ms(),
        "sensor_type": int(sensor_type),
        "sensor_id": int(sensor_id),
        "payload_len": int(payload_len),
        "crc": int(crc),
        "peer": peer,
    }
    with esp_lock:
        esp_packets.append(item)
        esp_last_seen_ms = item["ts"]


def get_esp_status():
    with esp_lock:
        last = esp_packets[-1] if esp_packets else None
        last_seen = esp_last_seen_ms
        count = len(esp_packets)
        total_bytes = esp_bytes_rx
    online = (now_ms() - int(last_seen)) <= esp_online_ttl_ms if last_seen else False
    return {
        "ok": True,
        "online": online,
        "status": "connected" if online else "disconnected",
        "store_depth": ESP_STORE_DEPTH,
        "cached_packets": count,
        "bytes_rx": total_bytes,
        "last_seen_ts": int(last_seen),
        "last_packet": last or {},
        "ts": now_ms(),
    }


def compute_sleep_score(radar_item, env_item, audio_item):
    score = 80

    motion = float(radar_item.get("motion", 0) or 0)
    turning = int(radar_item.get("turning", 0) or 0)
    score -= min(20, motion * 50)
    if turning == 1:
        score -= 5

    noise_db = float(env_item.get("noise_db", 0) or 0)
    snore_level = int(audio_item.get("snore_level", 0) or 0)
    score -= max(0, (noise_db - 35) * 0.8)
    score -= snore_level * 4

    co2 = float(env_item.get("co2_ppm", 0) or 0)
    if co2 > 1200:
        score -= min(15, (co2 - 1200) / 50)

    return max(0, min(100, int(score)))


def normalize_sleep_epoch(row: dict, fallback_ts: int):
    z = sleep_epoch_zero()
    out = dict(z)
    out.update(
        {
            "record": str(row.get("record", "") or ""),
            "start_s": as_float(row.get("start_s"), 0.0),
            "end_s": as_float(row.get("end_s"), 0.0),
            "BR_mean": as_float(row.get("BR_mean"), as_float(row.get("breath_bpm"), 0.0)),
            "BR_std": as_float(row.get("BR_std"), 0.0),
            "HR_mean": as_float(row.get("HR_mean"), as_float(row.get("heart_bpm"), 0.0)),
            "HR_std": as_float(row.get("HR_std"), 0.0),
            "RMSSD": as_float(row.get("RMSSD"), 0.0),
            "SDNN": as_float(row.get("SDNN"), 0.0),
            "EEG_stage": str(row.get("EEG_stage", "W") or "W"),
            "EEG_conf": as_float(row.get("EEG_conf"), 0.0),
            "Sleep_detect": str(row.get("Sleep_detect", "W") or "W"),
            "Sleep_W_prob": as_float(row.get("Sleep_W_prob"), 0.0),
            "Final_stage": str(row.get("Final_stage", "W") or "W"),
            "RuleApplied": as_int(row.get("RuleApplied"), 0),
        }
    )
    out["ts"] = as_int(row.get("ts"), fallback_ts)
    return out


def normalize_sleep_quality(row: dict, fallback_ts: int):
    z = sleep_quality_zero()
    out = dict(z)
    out.update(
        {
            "record": str(row.get("record", "") or ""),
            "total_h": as_float(row.get("total_h"), 0.0),
            "sleep_h": as_float(row.get("sleep_h"), 0.0),
            "W_epochs": as_int(row.get("W_epochs"), 0),
            "N1_epochs": as_int(row.get("N1_epochs"), 0),
            "N2_epochs": as_int(row.get("N2_epochs"), 0),
            "N3_epochs": as_int(row.get("N3_epochs"), 0),
            "REM_epochs": as_int(row.get("REM_epochs"), 0),
            "N1_ratio_in_sleep": as_float(row.get("N1_ratio_in_sleep"), 0.0),
            "N2_ratio_in_sleep": as_float(row.get("N2_ratio_in_sleep"), 0.0),
            "N3_ratio_in_sleep": as_float(row.get("N3_ratio_in_sleep"), 0.0),
            "REM_ratio_in_sleep": as_float(row.get("REM_ratio_in_sleep"), 0.0),
            "score_valid": as_int(row.get("score_valid"), 0),
            "duration_score": as_float(row.get("duration_score"), 0.0),
            "structure_score": as_float(row.get("structure_score"), 0.0),
            "total_score": as_float(row.get("total_score"), as_float(row.get("score"), 0.0)),
            "grade": str(row.get("grade", "数据不足，暂不评分") or "数据不足，暂不评分"),
        }
    )
    out["ts"] = as_int(row.get("ts"), fallback_ts)
    return out


def latest_sleep_epoch():
    return normalize_sleep_epoch(latest_one("sleep_epoch") or {}, 0)


def latest_sleep_quality():
    return normalize_sleep_quality(latest_one("sleep_quality") or {}, 0)


def build_voice_sleep_context():
    epoch = latest_sleep_epoch()
    quality = latest_sleep_quality()
    radar = latest_one("radar") or {}
    env = latest_one("env") or {}
    audio = latest_one("audio") or {}

    brief = (
        f"当前睡眠分期{epoch.get('Final_stage', 'W')}，"
        f"睡眠评分{quality.get('total_score', 0):.1f}分，"
        f"等级{quality.get('grade', '数据不足，暂不评分')}。"
    )

    return {
        "record": quality.get("record") or epoch.get("record", ""),
        "sleep_stage": epoch.get("Final_stage", "W"),
        "sleep_score": as_float(quality.get("total_score"), 0.0),
        "sleep_grade": quality.get("grade", "数据不足，暂不评分"),
        "sleep_h": as_float(quality.get("sleep_h"), 0.0),
        "snore_level": as_int(audio.get("snore_level"), 0),
        "snore_count_1min": as_int(audio.get("snore_count_1min"), 0),
        "heart_bpm": as_float(radar.get("heart_bpm"), 0.0),
        "breath_bpm": as_float(radar.get("breath_bpm"), 0.0),
        "noise_db": as_float(env.get("noise_db"), 0.0),
        "co2_ppm": as_float(env.get("co2_ppm"), 0.0),
        "brief": brief,
        "ts": now_ms(),
    }


_import_state = {
    "epoch_mtime": -1,
    "quality_mtime": -1,
}


def _read_csv_rows(path: str):
    if not os.path.isfile(path):
        return []
    rows = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
    except Exception as e:  # noqa: BLE001
        print(f"[SLEEP-IMPORT] failed reading {path}: {e}")
        return []
    return rows


def import_sleep_outputs_once(force: bool = False):
    now = now_ms()

    try:
        epoch_mtime = os.path.getmtime(SLEEP_EPOCH_FILE)
    except Exception:
        epoch_mtime = -1
    if force or (epoch_mtime > 0 and epoch_mtime != _import_state["epoch_mtime"]):
        rows = _read_csv_rows(SLEEP_EPOCH_FILE)
        items = []
        for i, row in enumerate(rows):
            fallback_ts = now + i
            items.append(normalize_sleep_epoch(row, fallback_ts))
        if items:
            replace_items("sleep_epoch", items)
            _import_state["epoch_mtime"] = epoch_mtime
            print(f"[SLEEP-IMPORT] sleep_epoch rows={len(items)} from {SLEEP_EPOCH_FILE}")

    try:
        quality_mtime = os.path.getmtime(SLEEP_QUALITY_FILE)
    except Exception:
        quality_mtime = -1
    if force or (quality_mtime > 0 and quality_mtime != _import_state["quality_mtime"]):
        rows = _read_csv_rows(SLEEP_QUALITY_FILE)
        items = []
        for i, row in enumerate(rows):
            fallback_ts = now + i
            items.append(normalize_sleep_quality(row, fallback_ts))
        if items:
            replace_items("sleep_quality", items)
            _import_state["quality_mtime"] = quality_mtime
            print(f"[SLEEP-IMPORT] sleep_quality rows={len(items)} from {SLEEP_QUALITY_FILE}")


def run_sleep_output_importer():
    print(f"[SLEEP-IMPORT] enabled={SLEEP_IMPORT_ENABLED} interval={SLEEP_IMPORT_INTERVAL_S}s")
    print(f"[SLEEP-IMPORT] epoch_file={SLEEP_EPOCH_FILE}")
    print(f"[SLEEP-IMPORT] quality_file={SLEEP_QUALITY_FILE}")
    while True:
        try:
            import_sleep_outputs_once(force=False)
        except Exception as e:  # noqa: BLE001
            print(f"[SLEEP-IMPORT] loop error: {e}")
        time.sleep(SLEEP_IMPORT_INTERVAL_S)


class IngestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"[INGEST] connected: {peer}")
        try:
            while True:
                raw = self.rfile.readline()
                if not raw:
                    break

                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                obj = safe_json_loads(line)
                if not isinstance(obj, dict):
                    continue

                kind = obj.get("kind")
                if kind not in KINDS:
                    continue

                obj.pop("kind", None)
                append_item(kind, obj)
        finally:
            print(f"[INGEST] disconnected: {peer}")


class ESPIngestHandler(socketserver.BaseRequestHandler):
    """Receive ESP binary packets: [AA 55 type id len_l len_h payload crc_l crc_h]."""

    def handle(self):
        global esp_bytes_rx
        peer = f"{self.client_address[0]}:{self.client_address[1]}"
        print(f"[ESP-INGEST] connected: {peer}")
        buf = bytearray()
        try:
            while True:
                chunk = self.request.recv(4096)
                if not chunk:
                    break
                with esp_lock:
                    esp_bytes_rx += len(chunk)
                buf.extend(chunk)

                # Parse as many complete frames as possible.
                while True:
                    if len(buf) < 8:
                        break

                    sync_idx = buf.find(b"\xAA\x55")
                    if sync_idx < 0:
                        # Keep at most one trailing byte to catch split sync.
                        if len(buf) > 1:
                            del buf[:-1]
                        break
                    if sync_idx > 0:
                        del buf[:sync_idx]

                    if len(buf) < 6:
                        break

                    sensor_type = buf[2]
                    sensor_id = buf[3]
                    payload_len = int(buf[4]) | (int(buf[5]) << 8)
                    full_len = 6 + payload_len + 2

                    if len(buf) < full_len:
                        break

                    crc_l = buf[6 + payload_len]
                    crc_h = buf[6 + payload_len + 1]
                    crc = int(crc_l) | (int(crc_h) << 8)
                    append_esp_packet(sensor_type, sensor_id, payload_len, crc, peer)
                    del buf[:full_len]
        except Exception as e:  # noqa: BLE001
            print(f"[ESP-INGEST] error from {peer}: {e}")
        finally:
            print(f"[ESP-INGEST] disconnected: {peer}")


class ReusableThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body_bytes, content_type="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body_bytes)))
        self.end_headers()
        self.wfile.write(body_bytes)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, body)

    def _html(self, html, code=200):
        self._send(code, html.encode("utf-8"), "text/html; charset=utf-8")

    def _read_json(self):
        length = as_int(self.headers.get("Content-Length"), 0)
        if length <= 0:
            return None
        raw = self.rfile.read(length)
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        q = urlparse(self.path)
        params = parse_qs(q.query)

        if q.path == "/" or q.path == "/dashboard":
            self._html(load_dashboard_html())
            return

        if q.path == "/favicon.ico":
            self._send(204, b"", "image/x-icon")
            return

        if q.path == "/health":
            self._json(
                {
                    "ok": True,
                    "mode": "lan-direct",
                    "location": LOCATION,
                    "minutes": HISTORY_MINUTES,
                    "ingest": {"host": INGEST_HOST, "port": INGEST_PORT},
                    "esp_ingest": {
                        "host": ESP_INGEST_HOST,
                        "port": ESP_INGEST_PORT,
                        "store_depth": ESP_STORE_DEPTH,
                    },
                    "sleep_integration": {
                        "import_enabled": SLEEP_IMPORT_ENABLED,
                        "epoch_file": SLEEP_EPOCH_FILE,
                        "quality_file": SLEEP_QUALITY_FILE,
                        "import_interval_s": SLEEP_IMPORT_INTERVAL_S,
                    },
                }
            )
            return

        if q.path == "/api/esp/status":
            self._json(get_esp_status())
            return

        if q.path == "/api/v2/latest":
            r = latest_one("radar") or {"ts": 0}
            e = latest_one("env") or {"ts": 0}
            a = latest_one("audio") or {"ts": 0}
            ep = latest_sleep_epoch()
            sq = latest_sleep_quality()

            obj = {
                "location": LOCATION,
                "status": {
                    "radar": source_online(r.get("ts", 0)),
                    "env": source_online(e.get("ts", 0)),
                    "audio": source_online(a.get("ts", 0)),
                },
                "radar": r if r.get("ts") else {},
                "env": e if e.get("ts") else {},
                "audio": a if a.get("ts") else {},
                "sleep": {
                    "record": sq.get("record") or ep.get("record", ""),
                    "final_stage": ep.get("Final_stage", "W"),
                    "sleep_score": as_float(sq.get("total_score"), 0.0),
                    "sleep_grade": sq.get("grade", "数据不足，暂不评分"),
                    "sleep_h": as_float(sq.get("sleep_h"), 0.0),
                },
                "ts": now_ms(),
            }
            self._json(obj)
            return

        if q.path == "/api/v2/rrhr":
            minutes = int((params.get("minutes") or ["30"])[0])
            step = int((params.get("step") or ["10"])[0])

            s = series("radar", minutes=minutes, step_s=step)
            table = []
            for it in s:
                table.append(
                    {
                        "time": to_timestr(int(it["ts"])),
                        "breath_bpm": float(it.get("breath_bpm", 0) or 0),
                        "heart_bpm": float(it.get("heart_bpm", 0) or 0),
                        "motion": float(it.get("motion", 0) or 0),
                        "turning": int(it.get("turning", 0) or 0),
                    }
                )
            self._json({"table": table})
            return

        if q.path == "/api/v2/env_latest":
            e = latest_one("env") or {}
            self._json(
                {
                    "co2_ppm": float(e.get("co2_ppm", 0) or 0),
                    "temp_c": float(e.get("temp_c", 0) or 0),
                    "rh": float(e.get("rh", 0) or 0),
                    "noise_db": float(e.get("noise_db", 0) or 0),
                    "ts": int(e.get("ts", 0) or 0),
                }
            )
            return

        if q.path == "/api/v2/turn_stats":
            minutes = int((params.get("minutes") or ["30"])[0])

            s = series("radar", minutes=minutes, step_s=5)
            turn_cnt = sum(1 for it in s if int(it.get("turning", 0) or 0) == 1)
            motions = [float(it.get("motion", 0) or 0) for it in s]
            motion_avg = sum(motions) / len(motions) if motions else 0.0

            self._json(
                {
                    "minutes": minutes,
                    "turn_count": turn_cnt,
                    "motion_avg": round(motion_avg, 3),
                    "ts": now_ms(),
                }
            )
            return

        if q.path == "/api/v2/snore_count_latest":
            a = latest_one("audio") or {}
            self._json(
                {
                    "snore_count_1min": int(a.get("snore_count_1min", 0) or 0),
                    "snore_level": int(a.get("snore_level", 0) or 0),
                    "ts": int(a.get("ts", 0) or 0),
                }
            )
            return

        if q.path == "/api/v2/snore_db_range":
            minutes = int((params.get("minutes") or ["30"])[0])
            bucket_min = int((params.get("bucket") or ["5"])[0])

            env_s = series("env", minutes=minutes, step_s=10)
            if not env_s:
                self._json({"table": []})
                return

            buckets = defaultdict(list)
            for it in env_s:
                ts = int(it["ts"])
                lt = time.localtime(ts / 1000)
                mm = (lt.tm_min // bucket_min) * bucket_min
                key = time.strftime(f"%H:{mm:02d}", lt)
                db = float(it.get("noise_db", 0) or 0)
                buckets[key].append(db)

            table = []
            for k in sorted(buckets.keys()):
                arr = buckets[k]
                table.append({"name": k, "start": round(min(arr), 1), "end": round(max(arr), 1)})

            self._json({"table": table})
            return

        if q.path == "/api/v2/sleep_score_bar":
            minutes = int((params.get("minutes") or ["30"])[0])
            bucket_min = int((params.get("bucket") or ["5"])[0])

            radar_s = series("radar", minutes=minutes, step_s=10)
            env_s = series("env", minutes=minutes, step_s=10)
            audio_s = series("audio", minutes=minutes, step_s=10)

            if not radar_s:
                self._json({"table": []})
                return

            def bucketize(seq):
                m = {}
                for it in seq:
                    ts = int(it["ts"])
                    lt = time.localtime(ts / 1000)
                    mm = (lt.tm_min // bucket_min) * bucket_min
                    key = time.strftime(f"%H:{mm:02d}", lt)
                    if key not in m or int(m[key]["ts"]) < ts:
                        m[key] = it
                return m

            br = bucketize(radar_s)
            be = bucketize(env_s)
            ba = bucketize(audio_s)

            keys = sorted(set(br.keys()) | set(be.keys()) | set(ba.keys()))
            table = []
            for k in keys:
                r = br.get(k, {})
                e = be.get(k, {})
                a = ba.get(k, {})
                score = compute_sleep_score(r, e, a)
                table.append({"time": k, "score": score})

            self._json({"table": table})
            return

        if q.path == "/api/v2/sleep/epoch/latest":
            self._json(latest_sleep_epoch())
            return

        if q.path == "/api/v2/sleep/quality/latest":
            self._json(latest_sleep_quality())
            return

        if q.path == "/api/v2/sleep/model_input/latest":
            ep = latest_sleep_epoch()
            self._json(
                {
                    "record": ep.get("record", ""),
                    "start_s": as_float(ep.get("start_s"), 0.0),
                    "end_s": as_float(ep.get("end_s"), 0.0),
                    "BR_mean": as_float(ep.get("BR_mean"), 0.0),
                    "BR_std": as_float(ep.get("BR_std"), 0.0),
                    "HR_mean": as_float(ep.get("HR_mean"), 0.0),
                    "HR_std": as_float(ep.get("HR_std"), 0.0),
                    "RMSSD": as_float(ep.get("RMSSD"), 0.0),
                    "SDNN": as_float(ep.get("SDNN"), 0.0),
                    "EEG_stage": ep.get("EEG_stage", "W"),
                    "EEG_conf": as_float(ep.get("EEG_conf"), 0.0),
                    "ts": as_int(ep.get("ts"), 0),
                }
            )
            return

        if q.path == "/api/v2/sleep/epoch/list":
            limit = as_int((params.get("limit") or ["120"])[0], 120)
            record = (params.get("record") or [""])[0]
            rows = [normalize_sleep_epoch(x, 0) for x in list_latest("sleep_epoch", limit=limit, record=record)]
            self._json({"table": rows})
            return

        if q.path == "/api/v2/sleep/quality/list":
            limit = as_int((params.get("limit") or ["120"])[0], 120)
            record = (params.get("record") or [""])[0]
            rows = [normalize_sleep_quality(x, 0) for x in list_latest("sleep_quality", limit=limit, record=record)]
            self._json({"table": rows})
            return

        if q.path == "/api/v2/voice/sleep_context":
            self._json(build_voice_sleep_context())
            return

        if q.path == "/api/v2/sleep/import_now":
            import_sleep_outputs_once(force=True)
            self._json({"ok": True, "msg": "import completed", "ts": now_ms()})
            return

        self._json({"error": "not found", "path": q.path}, code=404)

    def do_POST(self):
        q = urlparse(self.path)
        body = self._read_json()
        if body is None:
            self._json({"error": "invalid json"}, code=400)
            return

        if q.path == "/api/v2/ingest":
            kind = str(body.get("kind", "") or "")
            payload = body.get("payload", body)
            if kind not in KINDS:
                self._json({"error": "invalid kind", "kinds": list(KINDS)}, code=400)
                return
            if isinstance(payload, list):
                n = 0
                for x in payload:
                    if isinstance(x, dict):
                        append_item(kind, x)
                        n += 1
                self._json({"ok": True, "kind": kind, "ingested": n, "ts": now_ms()})
                return
            if not isinstance(payload, dict):
                self._json({"error": "payload must be object or list"}, code=400)
                return
            append_item(kind, payload)
            self._json({"ok": True, "kind": kind, "ingested": 1, "ts": now_ms()})
            return

        if q.path == "/api/v2/ingest/sleep_epoch":
            rows = body if isinstance(body, list) else [body]
            n = 0
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                item = normalize_sleep_epoch(row, now_ms() + i)
                append_item("sleep_epoch", item)
                n += 1
            self._json({"ok": True, "kind": "sleep_epoch", "ingested": n, "ts": now_ms()})
            return

        if q.path == "/api/v2/ingest/sleep_quality":
            rows = body if isinstance(body, list) else [body]
            n = 0
            for i, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                item = normalize_sleep_quality(row, now_ms() + i)
                append_item("sleep_quality", item)
                n += 1
            self._json({"ok": True, "kind": "sleep_quality", "ingested": n, "ts": now_ms()})
            return

        if q.path == "/api/v2/sleep/import_now":
            import_sleep_outputs_once(force=True)
            self._json({"ok": True, "msg": "import completed", "ts": now_ms()})
            return

        self._json({"error": "not found", "path": q.path}, code=404)


def run_tcp_ingest():
    server = ReusableThreadingTCPServer((INGEST_HOST, INGEST_PORT), IngestHandler)
    print(f"[INGEST] tcp://{INGEST_HOST}:{INGEST_PORT}")
    server.serve_forever()


def run_esp_tcp_ingest():
    server = ReusableThreadingTCPServer((ESP_INGEST_HOST, ESP_INGEST_PORT), ESPIngestHandler)
    print(f"[ESP-INGEST] tcp://{ESP_INGEST_HOST}:{ESP_INGEST_PORT} depth={ESP_STORE_DEPTH}")
    server.serve_forever()


def main():
    t = threading.Thread(target=run_tcp_ingest, daemon=True)
    t.start()

    te = threading.Thread(target=run_esp_tcp_ingest, daemon=True)
    te.start()

    if SLEEP_IMPORT_ENABLED:
        ti = threading.Thread(target=run_sleep_output_importer, daemon=True)
        ti.start()

    server = HTTPServer((HTTP_HOST, HTTP_PORT), Handler)
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/health")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/latest")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/esp/status")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/rrhr?minutes=30&step=10")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/sleep/model_input/latest")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/sleep/quality/latest")
    print(f"[HTTP] http://127.0.0.1:{HTTP_PORT}/api/v2/voice/sleep_context")
    server.serve_forever()


if __name__ == "__main__":
    main()
