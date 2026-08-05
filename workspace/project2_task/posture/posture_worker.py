#!/usr/bin/env python3
"""
睡姿分类 Worker (多床轮询版)
- 从网关获取床位列表，依次拉取各床位的最新 ESP 四通道完整数据集
- 重构原始数组 → 预处理(resize + normalize) → 构造9728维特征向量
- 调用 Random Forest 模型(ctypes)推理
- 将结果 POST 回网关 /api/v2/ingest/posture (附带 room/bed)

依赖: numpy, requests
"""

import base64
import ctypes
import json
import os
import struct
import sys
import time
from pathlib import Path

import numpy as np
import requests

# ===================== 配置 =====================
GATEWAY_BASE = os.getenv("GATEWAY_BASE", "http://127.0.0.1:8765").rstrip("/")
POLL_INTERVAL_S = max(0.5, float(os.getenv("POSTURE_POLL_INTERVAL_S", "2.0")))
BED_POLL_GAP_S = float(os.getenv("POSTURE_BED_POLL_GAP_S", "0.5"))

# 模型路径
WORKER_DIR = Path(__file__).resolve().parent
MODEL_SO_PATH = os.getenv("POSTURE_MODEL_SO", str(WORKER_DIR / "posture_model" / "libposture_model.so"))

# 图像尺寸（与训练时一致）
IMG_W = 64
IMG_H = 64
THERMAL_W = 24
THERMAL_H = 32
FEATURE_SIZE = IMG_W * IMG_H * 2 + THERMAL_W * THERMAL_H * 2  # 9728
NUM_CLASSES = 3

CLASS_NAMES = ["仰卧(Supine)", "侧卧(Lateral)", "俯卧(Prone)"]

# MLX 帧格式常量
MLX_PIXELS = 24 * 32
MLX_BYTES_PER_SENSOR = MLX_PIXELS * 4

# MaixSense 帧格式
MAIXSENSE_WIDTH = 100
MAIXSENSE_HEIGHT = 100
MAIXSENSE_META_LEN = 16

# 热成像归一化范围
THERMAL_MIN = 15.0
THERMAL_MAX = 40.0

# 置信度阈值
CONFIDENCE_THRESHOLD = float(os.getenv("POSTURE_CONFIDENCE_THRESHOLD", "0.6"))


# ===================== MaixSense 帧解析 =====================
def parse_maixsense_frame(payload: bytes) -> np.ndarray | None:
    if len(payload) < 6:
        return None
    if payload[0] == 0x00 and payload[1] == 0xFF:
        data_len = payload[2] | (payload[3] << 8)
        expected_frame_len = 2 + 2 + data_len + 1 + 1
        if len(payload) == expected_frame_len and payload[-1] == 0xDD:
            frame_payload = payload[4:-2]
            if len(frame_payload) < MAIXSENSE_META_LEN:
                return None
            img_data = frame_payload[MAIXSENSE_META_LEN:]
            if len(img_data) == MAIXSENSE_WIDTH * MAIXSENSE_HEIGHT:
                return np.frombuffer(img_data, dtype=np.uint8).reshape(
                    (MAIXSENSE_HEIGHT, MAIXSENSE_WIDTH)
                )
    buf = bytearray(payload)
    pos = buf.find(b"\x00\xFF")
    while pos >= 0:
        remaining = buf[pos:]
        if len(remaining) < 6:
            break
        data_len = remaining[2] | (remaining[3] << 8)
        frame_len = 2 + 2 + data_len + 1 + 1
        if len(remaining) < frame_len:
            break
        if remaining[frame_len - 1] == 0xDD:
            frame_payload = remaining[4 : frame_len - 2]
            if len(frame_payload) >= MAIXSENSE_META_LEN:
                img_data = frame_payload[MAIXSENSE_META_LEN:]
                if len(img_data) == MAIXSENSE_WIDTH * MAIXSENSE_HEIGHT:
                    return np.frombuffer(img_data, dtype=np.uint8).reshape(
                        (MAIXSENSE_HEIGHT, MAIXSENSE_WIDTH)
                    )
        pos = buf.find(b"\x00\xFF", pos + 1)
    return None


# ===================== MLX 解析 =====================
def parse_mlx_payload(payload: bytes) -> np.ndarray | None:
    if len(payload) < MLX_BYTES_PER_SENSOR:
        return None
    try:
        temps = np.frombuffer(payload[:MLX_BYTES_PER_SENSOR], dtype=np.float32)
        return temps.reshape((THERMAL_H, THERMAL_W))
    except Exception:
        return None


# ===================== 预处理 =====================
def resize_nearest(arr: np.ndarray, target_h: int, target_w: int) -> np.ndarray:
    src_h, src_w = arr.shape[:2]
    row_idx = np.clip(
        (np.arange(target_h) * src_h / target_h).astype(int), 0, src_h - 1
    )
    col_idx = np.clip(
        (np.arange(target_w) * src_w / target_w).astype(int), 0, src_w - 1
    )
    return arr[np.ix_(row_idx, col_idx)]


def normalize_tof(img: np.ndarray) -> np.ndarray:
    return img.astype(np.float64) / 255.0


def normalize_thermal(img: np.ndarray) -> np.ndarray:
    norm = (img.astype(np.float64) - THERMAL_MIN) / (THERMAL_MAX - THERMAL_MIN)
    return np.clip(norm, 0.0, 1.0)


def build_feature_vector(
    tof1: np.ndarray, tof2: np.ndarray, mlx1: np.ndarray, mlx2: np.ndarray
) -> np.ndarray:
    tof1_r = resize_nearest(tof1, IMG_H, IMG_W)
    tof2_r = resize_nearest(tof2, IMG_H, IMG_W)
    mlx1_r = resize_nearest(mlx1, THERMAL_H, THERMAL_W)
    mlx2_r = resize_nearest(mlx2, THERMAL_H, THERMAL_W)

    tof1_n = normalize_tof(tof1_r).flatten()
    tof2_n = normalize_tof(tof2_r).flatten()
    mlx1_n = normalize_thermal(mlx1_r).flatten()
    mlx2_n = normalize_thermal(mlx2_r).flatten()

    features = np.concatenate([tof1_n, tof2_n, mlx1_n, mlx2_n])
    assert features.shape[0] == FEATURE_SIZE, f"特征向量长度不匹配: {features.shape[0]} != {FEATURE_SIZE}"
    return features


# ===================== 模型推理 (ctypes) =====================
class PostureModel:
    def __init__(self, so_path: str):
        if not os.path.isfile(so_path):
            raise FileNotFoundError(f"模型 .so 文件不存在: {so_path}")
        self.lib = ctypes.CDLL(so_path)
        self.lib.score.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
        ]
        self.lib.score.restype = None
        self._input_buf = (ctypes.c_double * FEATURE_SIZE)()
        self._output_buf = (ctypes.c_double * NUM_CLASSES)()
        print(f"[POSTURE-MODEL] 已加载: {so_path}")

    def predict(self, features: np.ndarray) -> dict:
        if features.shape[0] != FEATURE_SIZE:
            raise ValueError(f"特征向量长度错误: {features.shape[0]} != {FEATURE_SIZE}")
        for i in range(FEATURE_SIZE):
            self._input_buf[i] = float(features[i])
        t0 = time.monotonic()
        self.lib.score(self._input_buf, self._output_buf)
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        probs = [float(self._output_buf[i]) for i in range(NUM_CLASSES)]
        best_idx = int(np.argmax(probs))
        confidence = probs[best_idx]
        return {
            "class_idx": best_idx,
            "class_name": CLASS_NAMES[best_idx],
            "confidence": round(confidence, 4),
            "probabilities": [round(p, 4) for p in probs],
            "infer_ms": round(elapsed_ms, 1),
        }


# ===================== 网关交互 =====================
def fetch_bed_list() -> list[dict]:
    try:
        r = requests.get(f"{GATEWAY_BASE}/api/v2/beds", timeout=3.0)
        r.raise_for_status()
        obj = r.json()
        return obj.get("beds", [])
    except Exception as e:
        print(f"[POSTURE-WORKER] 获取床位列表失败: {e}")
        return []


def fetch_latest_esp_set(room: str, bed: str) -> dict | None:
    try:
        url = f"{GATEWAY_BASE}/api/esp/set/latest?payload=1&room={room}&bed={bed}"
        r = requests.get(url, timeout=3.0)
        r.raise_for_status()
        obj = r.json()
        if isinstance(obj, dict) and obj.get("has_set"):
            return obj.get("set")
    except Exception as e:
        print(f"[POSTURE-WORKER] 获取ESP数据失败 [{room}-{bed}]: {e}")
    return None


def decode_esp_frames(esp_set: dict) -> dict | None:
    frames = esp_set.get("frames", {})
    result = {}

    for key in ("tof1", "tof2"):
        frame = frames.get(key)
        if not frame or not frame.get("payload_b64"):
            result[key] = None
            continue
        payload = base64.b64decode(frame["payload_b64"])
        depth_map = parse_maixsense_frame(payload)
        result[key] = depth_map
        if depth_map is None:
            print(f"[POSTURE-WORKER] {key} 帧解析失败, payload_len={len(payload)}")

    for key in ("mlx1", "mlx2"):
        frame = frames.get(key)
        if not frame or not frame.get("payload_b64"):
            result[key] = None
            continue
        payload = base64.b64decode(frame["payload_b64"])
        temps = parse_mlx_payload(payload)
        result[key] = temps
        if temps is None:
            print(f"[POSTURE-WORKER] {key} 帧解析失败, payload_len={len(payload)}")

    return result


def post_result_to_gateway(room: str, bed: str, result: dict) -> bool:
    result["room"] = room
    result["bed"] = bed
    try:
        r = requests.post(f"{GATEWAY_BASE}/api/v2/ingest/posture", json=result, timeout=2.0)
        r.raise_for_status()
        return True
    except Exception as e:
        print(f"[POSTURE-WORKER] 推送结果失败 [{room}-{bed}]: {e}")
        return False


def process_one_bed(model: PostureModel, room: str, bed: str, state: dict):
    """处理单个床位的推理，更新 state 字典。"""
    bed_key = f"{room}-{bed}"
    if bed_key not in state:
        state[bed_key] = {"last_set_id": -1, "infer_count": 0}
    per_bed = state[bed_key]

    esp_set = fetch_latest_esp_set(room, bed)
    if not esp_set:
        return

    set_id = esp_set.get("set_id", -1)
    if set_id == per_bed["last_set_id"]:
        return

    decoded = decode_esp_frames(esp_set)
    tof1 = decoded.get("tof1")
    tof2 = decoded.get("tof2")
    mlx1 = decoded.get("mlx1")
    mlx2 = decoded.get("mlx2")

    if tof1 is None or tof2 is None or mlx1 is None or mlx2 is None:
        missing = [k for k in ("tof1", "tof2", "mlx1", "mlx2") if decoded.get(k) is None]
        print(f"[POSTURE-WORKER] [{bed_key}] 数据不完整, 缺少: {missing}")
        per_bed["last_set_id"] = set_id
        return

    try:
        features = build_feature_vector(tof1, tof2, mlx1, mlx2)
    except Exception as e:
        print(f"[POSTURE-WORKER] [{bed_key}] 特征构造失败: {e}")
        per_bed["last_set_id"] = set_id
        return

    try:
        pred = model.predict(features)
    except Exception as e:
        print(f"[POSTURE-WORKER] [{bed_key}] 推理失败: {e}")
        per_bed["last_set_id"] = set_id
        return

    per_bed["infer_count"] += 1
    per_bed["last_set_id"] = set_id

    ts_ms = int(time.time() * 1000)
    confidence_flag = "high" if pred["confidence"] >= CONFIDENCE_THRESHOLD else "low"
    result = {
        "room": room,
        "bed": bed,
        "class_idx": pred["class_idx"],
        "class_name": pred["class_name"],
        "confidence": pred["confidence"],
        "confidence_flag": confidence_flag,
        "probabilities": pred["probabilities"],
        "infer_ms": pred["infer_ms"],
        "esp_set_id": set_id,
        "infer_count": per_bed["infer_count"],
        "ts": ts_ms,
    }

    ts_str = time.strftime("%H:%M:%S", time.localtime(ts_ms / 1000))
    probs_str = " | ".join(
        f"{CLASS_NAMES[i]}: {pred['probabilities'][i]*100:.1f}%"
        for i in range(NUM_CLASSES)
    )
    print(
        f"[{ts_str}] [{bed_key}] #{per_bed['infer_count']} → {pred['class_name']} "
        f"({pred['confidence']*100:.1f}%, {confidence_flag}) "
        f"[{probs_str}] infer={pred['infer_ms']:.0f}ms"
    )

    post_result_to_gateway(room, bed, result)


# ===================== 主循环 =====================
def main():
    print("=" * 50)
    print("  睡姿分类 Worker (多床轮询)")
    print("=" * 50)
    print(f"网关地址: {GATEWAY_BASE}")
    print(f"轮询间隔: {POLL_INTERVAL_S}s")
    print(f"床位轮询间隔: {BED_POLL_GAP_S}s")
    print(f"模型路径: {MODEL_SO_PATH}")
    print(f"置信阈值: {CONFIDENCE_THRESHOLD}")
    print()

    try:
        model = PostureModel(MODEL_SO_PATH)
    except Exception as e:
        print(f"[FATAL] 模型加载失败: {e}")
        sys.exit(1)

    per_bed_state = {}

    print("[POSTURE-WORKER] 开始主循环，等待床位和ESP数据……\n")

    while True:
        beds = fetch_bed_list()
        if not beds:
            print("[POSTURE-WORKER] 无床位配置，等待中...")
            time.sleep(POLL_INTERVAL_S)
            continue

        for bed_info in beds:
            room = bed_info.get("room", "")
            bed = bed_info.get("bed", "")
            if not room or not bed:
                continue
            try:
                process_one_bed(model, room, bed, per_bed_state)
            except Exception as e:
                print(f"[POSTURE-WORKER] [{room}-{bed}] 处理异常: {e}")
            time.sleep(BED_POLL_GAP_S)

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
