#!/usr/bin/env python3
"""
视觉 Worker（阶段 2/3）
- 默认以 mock 方式运行，方便在没有摄像头时联调 gateway / frontend / voice。
- 可切换为 camera 模式：摄像头取流 + YuNet 人脸检测 + ONNXRuntime 情绪分类。
- 低频推理，默认 1Hz，避免在板端抢占过多资源。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from emotion_runtime import OnnxEmotionRuntime
    from frame_source import MockFrameSource, OpenCVCameraSource
    from identity_runtime import LocalCvFaceEmbedder, match_face_vector
else:
    from .emotion_runtime import OnnxEmotionRuntime
    from .frame_source import MockFrameSource, OpenCVCameraSource
    from .identity_runtime import LocalCvFaceEmbedder, match_face_vector


def now_ms() -> int:
    return int(time.time() * 1000)


WORKER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = WORKER_DIR.parent

GATEWAY_BASE = os.getenv("GATEWAY_BASE", "http://127.0.0.1:8765").rstrip("/")
EMOTION_INGEST_URL = os.getenv("EMOTION_INGEST_URL", f"{GATEWAY_BASE}/api/v2/ingest/emotion")
VISION_OBSERVATION_URL = os.getenv("VISION_OBSERVATION_URL", f"{GATEWAY_BASE}/api/v3/vision/observation")
VISION_IDENTITY_GALLERY_URL = os.getenv("VISION_IDENTITY_GALLERY_URL", f"{GATEWAY_BASE}/api/v3/identity/gallery?type=face")

VISION_SOURCE = os.getenv("VISION_SOURCE", "mock").strip().lower()
VISION_INTERVAL_S = max(0.5, float(os.getenv("VISION_INTERVAL_S", "1.0")))
VISION_CAMERA_INDEX = int(os.getenv("VISION_CAMERA_INDEX", "0"))
VISION_CAMERA_WIDTH = int(os.getenv("VISION_CAMERA_WIDTH", "640"))
VISION_CAMERA_HEIGHT = int(os.getenv("VISION_CAMERA_HEIGHT", "480"))
VISION_FACE_SCORE_THRESHOLD = float(os.getenv("VISION_FACE_SCORE_THRESHOLD", "0.75"))
VISION_EMOTION_CONFIDENCE_THRESHOLD = float(os.getenv("VISION_EMOTION_CONFIDENCE_THRESHOLD", "0.6"))
VISION_IDENTITY_ENABLED = os.getenv("VISION_IDENTITY_ENABLED", "1") not in ("0", "false", "False")
VISION_IDENTITY_REFRESH_S = max(5.0, float(os.getenv("VISION_IDENTITY_REFRESH_S", "30")))
VISION_FACE_MATCH_RECOGNIZED_THRESHOLD = float(os.getenv("FACE_MATCH_RECOGNIZED_THRESHOLD", "0.82"))
VISION_FACE_MATCH_CANDIDATE_THRESHOLD = float(os.getenv("FACE_MATCH_CANDIDATE_THRESHOLD", "0.72"))

VISION_FACE_MODEL = os.getenv(
    "VISION_FACE_MODEL",
    str(WORKER_DIR / "models" / "face_detection_yunet_2023mar.onnx"),
)
VISION_EMOTION_MODEL = os.getenv(
    "VISION_EMOTION_MODEL",
    str(WORKER_DIR / "models" / "emotion_mamba.onnx"),
)

VISION_MOCK_LABEL = os.getenv("VISION_MOCK_LABEL", "自然").strip() or "自然"
VISION_MOCK_CONFIDENCE = max(0.0, min(1.0, float(os.getenv("VISION_MOCK_CONFIDENCE", "0.88"))))
VISION_MOCK_FACE_COUNT = max(0, int(os.getenv("VISION_MOCK_FACE_COUNT", "1")))
VISION_MOCK_SUBJECT_ID = os.getenv("VISION_MOCK_SUBJECT_ID", "").strip()


class YuNetFaceDetector:
    def __init__(self, model_path: str, score_threshold: float = 0.75):
        import cv2

        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError("当前 OpenCV 不包含 FaceDetectorYN，请安装带 contrib 的版本。")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"未找到 YuNet 人脸检测模型: {model_path}")

        self.cv2 = cv2
        self.detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=20,
        )

    def detect(self, frame) -> list[tuple[int, int, int, int]]:
        h, w = frame.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(frame)
        out = []
        if faces is None:
            return out
        for face in faces:
            x, y, fw, fh = face[:4]
            x = max(0, int(round(x)))
            y = max(0, int(round(y)))
            fw = max(1, int(round(fw)))
            fh = max(1, int(round(fh)))
            if x >= w or y >= h:
                continue
            fw = min(fw, w - x)
            fh = min(fh, h - y)
            out.append((x, y, fw, fh))
        out.sort(key=lambda item: item[2] * item[3], reverse=True)
        return out


def crop_face(frame, rect, pad_ratio: float = 0.12):
    x, y, w, h = rect
    pad_x = int(w * pad_ratio)
    pad_y = int(h * pad_ratio)
    x0 = max(0, x - pad_x)
    y0 = max(0, y - pad_y)
    x1 = min(frame.shape[1], x + w + pad_x)
    y1 = min(frame.shape[0], y + h + pad_y)
    return frame[y0:y1, x0:x1]


def build_probability_map(label: str, confidence: float) -> dict:
    labels = ["愤怒", "蔑视", "厌恶", "恐惧", "开心", "自然", "悲伤", "惊讶"]
    base = {name: 0.0 for name in labels}
    if label in base:
        base[label] = round(confidence, 4)
    return base


def post_result_to_gateway(result: dict) -> bool:
    try:
        r = requests.post(EMOTION_INGEST_URL, json=result, timeout=2.0)
        r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[VISION] 推送情绪结果失败: {e}")
        return False


def post_observation_to_gateway(identity: dict, emotion: dict) -> bool:
    try:
        payload = {
            "source": emotion.get("source", "unknown"),
            "camera_index": emotion.get("camera_index", -1),
            "identity": identity or {},
            "emotion": emotion or {},
            "ts": emotion.get("ts") or now_ms(),
        }
        r = requests.post(VISION_OBSERVATION_URL, json=payload, timeout=2.0)
        r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[VISION] 推送视觉会话观察失败: {e}")
        return False


class GatewayFaceIdentityClient:
    def __init__(self):
        self.embedder = LocalCvFaceEmbedder()
        self.gallery: list[dict] = []
        self.next_refresh_ts = 0.0
        self.last_error = ""

    def refresh_if_needed(self) -> None:
        if not VISION_IDENTITY_ENABLED:
            return
        now = time.monotonic()
        if now < self.next_refresh_ts:
            return
        self.next_refresh_ts = now + VISION_IDENTITY_REFRESH_S
        try:
            r = requests.get(VISION_IDENTITY_GALLERY_URL, timeout=2.0)
            r.raise_for_status()
            data = r.json()
            self.gallery = data.get("credentials", []) if isinstance(data, dict) else []
            self.last_error = ""
        except Exception as e:  # noqa: BLE001
            self.last_error = str(e)

    def match(self, face_bgr) -> dict:
        if not VISION_IDENTITY_ENABLED:
            return {"type": "face", "auth_method": "face", "identity_state": "disabled", "subject_id": "", "confidence": 0.0}
        self.refresh_if_needed()
        if not self.gallery:
            return {
                "type": "face",
                "auth_method": "face",
                "identity_state": "no_gallery",
                "subject_id": "",
                "confidence": 0.0,
                "notes": self.last_error,
            }
        try:
            vector = self.embedder.embed(face_bgr)
            return match_face_vector(
                vector,
                self.gallery,
                recognized_threshold=VISION_FACE_MATCH_RECOGNIZED_THRESHOLD,
                candidate_threshold=VISION_FACE_MATCH_CANDIDATE_THRESHOLD,
            )
        except Exception as e:  # noqa: BLE001
            return {
                "type": "face",
                "auth_method": "face",
                "identity_state": "match_error",
                "subject_id": "",
                "confidence": 0.0,
                "notes": str(e),
            }


def create_mock_payload(infer_count: int, stable_for_ms: int) -> dict:
    return {
        "label": VISION_MOCK_LABEL,
        "confidence": round(VISION_MOCK_CONFIDENCE, 4),
        "confidence_flag": "high" if VISION_MOCK_CONFIDENCE >= VISION_EMOTION_CONFIDENCE_THRESHOLD else "low",
        "probabilities": build_probability_map(VISION_MOCK_LABEL, VISION_MOCK_CONFIDENCE),
        "face_count": VISION_MOCK_FACE_COUNT,
        "face_present": VISION_MOCK_FACE_COUNT > 0,
        "source": "mock",
        "source_state": "mock",
        "backend": "mock",
        "camera_index": -1,
        "stable_for_ms": stable_for_ms,
        "infer_ms": 0.0,
        "infer_count": infer_count,
        "notes": "mock emotion for integration testing",
        "ts": now_ms(),
    }


def create_mock_identity() -> dict:
    if not VISION_MOCK_SUBJECT_ID:
        return {}
    return {
        "type": "face",
        "auth_method": "face",
        "identity_state": "recognized",
        "subject_id": VISION_MOCK_SUBJECT_ID,
        "confidence": 0.99,
        "assurance_level": "medium",
        "provider": "mock",
    }


def update_stability(last_label: str, stable_since_ms: int, label: str, face_present: bool):
    if not face_present or not label or label in ("未知", "无人脸"):
        return "", 0, 0
    now = now_ms()
    if label == last_label and stable_since_ms > 0:
        return last_label, stable_since_ms, max(0, now - stable_since_ms)
    return label, now, 0


def open_camera_pipeline():
    source = OpenCVCameraSource(
        camera_index=VISION_CAMERA_INDEX,
        width=VISION_CAMERA_WIDTH,
        height=VISION_CAMERA_HEIGHT,
    )
    source.open()
    detector = YuNetFaceDetector(VISION_FACE_MODEL, score_threshold=VISION_FACE_SCORE_THRESHOLD)
    runtime = OnnxEmotionRuntime(VISION_EMOTION_MODEL)
    return source, detector, runtime


def main():
    print("=" * 50)
    print("  Vision Worker")
    print("=" * 50)
    print(f"网关地址: {GATEWAY_BASE}")
    print(f"推送目标: {EMOTION_INGEST_URL}")
    print(f"会话目标: {VISION_OBSERVATION_URL}")
    print(f"视觉源:   {VISION_SOURCE}")
    print(f"身份识别: {'enabled' if VISION_IDENTITY_ENABLED else 'disabled'}")
    print(f"运行频率: {1.0 / VISION_INTERVAL_S:.2f}Hz (间隔 {VISION_INTERVAL_S:.2f}s)")
    print()

    infer_count = 0
    last_label = ""
    stable_since_ms = 0

    if VISION_SOURCE == "mock":
        source = MockFrameSource(default_label=VISION_MOCK_LABEL)
        source.open()
        print(f"[VISION] mock 模式已启用，默认情绪={VISION_MOCK_LABEL}")
        while True:
            infer_count += 1
            last_label, stable_since_ms, stable_for_ms = update_stability(
                last_label,
                stable_since_ms,
                VISION_MOCK_LABEL,
                VISION_MOCK_FACE_COUNT > 0,
            )
            payload = create_mock_payload(infer_count=infer_count, stable_for_ms=stable_for_ms)
            identity = create_mock_identity()
            if identity:
                payload["subject_id"] = identity.get("subject_id", "")
                payload["identity_state"] = identity.get("identity_state", "")
                payload["identity"] = identity
            post_result_to_gateway(payload)
            if identity:
                post_observation_to_gateway(identity, payload)
            time.sleep(VISION_INTERVAL_S)

    if VISION_SOURCE not in ("camera", "auto"):
        print(f"[VISION] 不支持的视觉源: {VISION_SOURCE}")
        return 1

    try:
        source, detector, runtime = open_camera_pipeline()
        identity_client = GatewayFaceIdentityClient()
        identity_client.refresh_if_needed()
        backend_name = "onnx_cpu"
        print(f"[VISION] camera 模式已启用，camera_index={VISION_CAMERA_INDEX}")
    except Exception as e:  # noqa: BLE001
        if VISION_SOURCE == "auto":
            print(f"[VISION] camera 初始化失败，已回退 mock: {e}")
            source = MockFrameSource(default_label=VISION_MOCK_LABEL)
            source.open()
            while True:
                infer_count += 1
                last_label, stable_since_ms, stable_for_ms = update_stability(
                    last_label,
                    stable_since_ms,
                    VISION_MOCK_LABEL,
                    VISION_MOCK_FACE_COUNT > 0,
                )
                payload = create_mock_payload(infer_count=infer_count, stable_for_ms=stable_for_ms)
                payload["source"] = "auto-fallback-mock"
                payload["notes"] = f"camera fallback: {e}"
                identity = create_mock_identity()
                if identity:
                    payload["subject_id"] = identity.get("subject_id", "")
                    payload["identity_state"] = identity.get("identity_state", "")
                    payload["identity"] = identity
                post_result_to_gateway(payload)
                if identity:
                    post_observation_to_gateway(identity, payload)
                time.sleep(VISION_INTERVAL_S)
        print(f"[VISION] camera 初始化失败: {e}")
        return 1

    while True:
        packet = source.read()
        infer_count += 1

        if packet.frame is None:
            payload = {
                "label": "未知",
                "confidence": 0.0,
                "confidence_flag": "none",
                "probabilities": {},
                "face_count": 0,
                "face_present": False,
                "source": packet.source,
                "source_state": packet.source_state,
                "backend": "none",
                "camera_index": VISION_CAMERA_INDEX,
                "stable_for_ms": 0,
                "infer_ms": 0.0,
                "infer_count": infer_count,
                "notes": packet.notes,
                "ts": packet.ts or now_ms(),
            }
            post_result_to_gateway(payload)
            time.sleep(VISION_INTERVAL_S)
            continue

        t0 = time.monotonic()
        try:
            rects = detector.detect(packet.frame)
        except Exception as e:  # noqa: BLE001
            payload = {
                "label": "未知",
                "confidence": 0.0,
                "confidence_flag": "none",
                "probabilities": {},
                "face_count": 0,
                "face_present": False,
                "source": packet.source,
                "source_state": "detect_error",
                "backend": backend_name,
                "camera_index": VISION_CAMERA_INDEX,
                "stable_for_ms": 0,
                "infer_ms": 0.0,
                "infer_count": infer_count,
                "notes": str(e),
                "ts": now_ms(),
            }
            post_result_to_gateway(payload)
            time.sleep(VISION_INTERVAL_S)
            continue

        if not rects:
            payload = {
                "label": "无人脸",
                "confidence": 0.0,
                "confidence_flag": "none",
                "probabilities": {},
                "face_count": 0,
                "face_present": False,
                "source": packet.source,
                "source_state": "no_face",
                "backend": backend_name,
                "camera_index": VISION_CAMERA_INDEX,
                "stable_for_ms": 0,
                "infer_ms": round((time.monotonic() - t0) * 1000.0, 1),
                "infer_count": infer_count,
                "notes": packet.notes,
                "ts": now_ms(),
            }
            post_result_to_gateway(payload)
            time.sleep(VISION_INTERVAL_S)
            continue

        try:
            face_img = crop_face(packet.frame, rects[0])
            label, confidence, probabilities = runtime.predict(face_img, face_id=0)
            identity = identity_client.match(face_img)
            last_label, stable_since_ms, stable_for_ms = update_stability(
                last_label,
                stable_since_ms,
                label,
                True,
            )
            payload = {
                "label": label,
                "confidence": round(confidence, 4),
                "confidence_flag": "high" if confidence >= VISION_EMOTION_CONFIDENCE_THRESHOLD else "low",
                "probabilities": probabilities,
                "face_count": len(rects),
                "face_present": True,
                "source": packet.source,
                "source_state": packet.source_state,
                "backend": backend_name,
                "camera_index": VISION_CAMERA_INDEX,
                "stable_for_ms": stable_for_ms,
                "infer_ms": round((time.monotonic() - t0) * 1000.0, 1),
                "infer_count": infer_count,
                "notes": packet.notes,
                "subject_id": identity.get("subject_id", ""),
                "identity_state": identity.get("identity_state", ""),
                "identity_confidence": identity.get("confidence", 0.0),
                "identity": identity,
                "ts": now_ms(),
            }
        except Exception as e:  # noqa: BLE001
            identity = {}
            payload = {
                "label": "未知",
                "confidence": 0.0,
                "confidence_flag": "none",
                "probabilities": {},
                "face_count": len(rects),
                "face_present": len(rects) > 0,
                "source": packet.source,
                "source_state": "infer_error",
                "backend": backend_name,
                "camera_index": VISION_CAMERA_INDEX,
                "stable_for_ms": 0,
                "infer_ms": round((time.monotonic() - t0) * 1000.0, 1),
                "infer_count": infer_count,
                "notes": str(e),
                "ts": now_ms(),
            }

        post_result_to_gateway(payload)
        if payload.get("face_present"):
            post_observation_to_gateway(identity, payload)
        time.sleep(VISION_INTERVAL_S)


if __name__ == "__main__":
    raise SystemExit(main())
