from __future__ import annotations

import base64
import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

FACE_TEMPLATE_SCHEMA = "project2.credential.face_embedding.v1"
FACE_EMBEDDING_MODEL = "project2.local_cv_face_v1"
FACE_EMBEDDING_VERSION = 1
DEFAULT_RECOGNIZED_THRESHOLD = 0.82
DEFAULT_CANDIDATE_THRESHOLD = 0.72


def now_ms() -> int:
    return int(time.time() * 1000)


def _strip_data_url(image_b64: str) -> tuple[str, str]:
    text = (image_b64 or "").strip()
    if "," not in text or not text.lower().startswith("data:"):
        return text, ""
    header, payload = text.split(",", 1)
    mime = header[5:].split(";", 1)[0].strip().lower()
    return payload, mime


def decode_image_b64(image_b64: str):
    import cv2

    payload, mime = _strip_data_url(image_b64)
    try:
        raw = base64.b64decode(payload, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("invalid base64 image") from exc
    arr = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("image decode failed")
    return image, raw, mime


class YuNetFaceCropper:
    def __init__(self, model_path: str, score_threshold: float = 0.75):
        import cv2

        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError("OpenCV FaceDetectorYN is unavailable")
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"face detector model not found: {model_path}")
        self.cv2 = cv2
        self.model_path = model_path
        self.detector = cv2.FaceDetectorYN.create(
            model_path,
            "",
            (320, 320),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=20,
        )

    def crop_largest(self, image_bgr, pad_ratio: float = 0.12):
        h, w = image_bgr.shape[:2]
        self.detector.setInputSize((w, h))
        _, faces = self.detector.detect(image_bgr)
        if faces is None or len(faces) == 0:
            return None, {}
        best = max(faces, key=lambda face: float(face[2]) * float(face[3]))
        x, y, fw, fh = [int(round(float(v))) for v in best[:4]]
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))
        fw = max(1, min(fw, w - x))
        fh = max(1, min(fh, h - y))
        pad_x = int(fw * pad_ratio)
        pad_y = int(fh * pad_ratio)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(w, x + fw + pad_x)
        y1 = min(h, y + fh + pad_y)
        meta = {
            "face_detected": True,
            "face_box": [x, y, fw, fh],
            "crop_box": [x0, y0, x1 - x0, y1 - y0],
            "detector": "yunet",
            "detector_score": round(float(best[-1]), 4) if len(best) >= 15 else None,
        }
        return image_bgr[y0:y1, x0:x1], meta


class LocalCvFaceEmbedder:
    """Small deterministic face embedding for integration.

    It is intentionally model-swappable: production can replace this class with
    ArcFace/InsightFace while preserving the template schema and gateway APIs.
    """

    def __init__(self):
        import cv2

        self.cv2 = cv2

    def _lbp_histogram(self, gray: np.ndarray) -> np.ndarray:
        center = gray[1:-1, 1:-1]
        codes = np.zeros(center.shape, dtype=np.uint8)
        neighbors = [
            gray[:-2, :-2], gray[:-2, 1:-1], gray[:-2, 2:],
            gray[1:-1, 2:], gray[2:, 2:], gray[2:, 1:-1],
            gray[2:, :-2], gray[1:-1, :-2],
        ]
        for idx, neighbor in enumerate(neighbors):
            codes |= ((neighbor >= center).astype(np.uint8) << idx)
        hist = np.bincount(codes.ravel(), minlength=256).astype(np.float32)
        total = float(hist.sum())
        return hist / total if total > 0 else hist

    def embed(self, face_bgr) -> np.ndarray:
        cv2 = self.cv2
        resized = cv2.resize(face_bgr, (64, 64), interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        gray32 = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        gray32 = gray32 - float(gray32.mean())
        std = float(gray32.std())
        if std > 1e-6:
            gray32 = gray32 / std
        dct = cv2.dct(gray32)
        dct_features = dct[:12, :12].reshape(-1).astype(np.float32)

        lbp_features = self._lbp_histogram(gray)

        hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [16, 4, 4], [0, 180, 0, 256, 0, 256])
        color_features = hist.reshape(-1).astype(np.float32)
        color_sum = float(color_features.sum())
        if color_sum > 0:
            color_features = color_features / color_sum

        vector = np.concatenate([dct_features, lbp_features, color_features]).astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if norm > 1e-8:
            vector = vector / norm
        return vector


def vector_to_json(vector: np.ndarray) -> list[float]:
    return [round(float(x), 6) for x in vector.tolist()]


def template_vector(template: dict[str, Any]) -> np.ndarray | None:
    if not isinstance(template, dict):
        return None
    embedding = template.get("embedding") if isinstance(template.get("embedding"), dict) else template
    raw_vector = embedding.get("vector")
    if not isinstance(raw_vector, list) or not raw_vector:
        return None
    try:
        vector = np.asarray(raw_vector, dtype=np.float32)
    except Exception:
        return None
    norm = float(np.linalg.norm(vector))
    if norm > 1e-8:
        vector = vector / norm
    return vector


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    if a is None or b is None or a.size == 0 or b.size == 0 or a.shape != b.shape:
        return 0.0
    return float(np.dot(a, b))


def build_face_template_from_image_b64(
    image_b64: str,
    *,
    detector_model_path: str = "",
    detect_face: bool = True,
    score_threshold: float = 0.75,
) -> dict[str, Any]:
    image, raw, mime = decode_image_b64(image_b64)
    face = image
    face_meta: dict[str, Any] = {
        "face_detected": False,
        "face_box": [],
        "crop_box": [0, 0, int(image.shape[1]), int(image.shape[0])],
        "detector": "none",
    }
    if detect_face and detector_model_path:
        cropper = YuNetFaceCropper(detector_model_path, score_threshold=score_threshold)
        cropped, meta = cropper.crop_largest(image)
        if cropped is None:
            raise ValueError("no face found in image")
        face = cropped
        face_meta = meta

    embedder = LocalCvFaceEmbedder()
    vector = embedder.embed(face)
    return {
        "schema": FACE_TEMPLATE_SCHEMA,
        "modality": "face",
        "embedding": {
            "model": FACE_EMBEDDING_MODEL,
            "version": FACE_EMBEDDING_VERSION,
            "dim": int(vector.size),
            "vector": vector_to_json(vector),
            "encoding": "float32_json_l2",
        },
        "source_image": {
            "sha256": hashlib.sha256(raw).hexdigest(),
            "mime": mime,
            "width": int(image.shape[1]),
            "height": int(image.shape[0]),
            "stored": False,
        },
        "face": face_meta,
        "created_ts": now_ms(),
    }


@dataclass
class GalleryEntry:
    credential_id: str
    subject_id: str
    subject_name: str
    subject_role: str
    provider: str
    template: dict[str, Any]
    vector: np.ndarray


def gallery_entries(rows: list[dict[str, Any]]) -> list[GalleryEntry]:
    entries: list[GalleryEntry] = []
    for row in rows:
        template = row.get("template") if isinstance(row.get("template"), dict) else {}
        vector = template_vector(template)
        if vector is None:
            continue
        entries.append(
            GalleryEntry(
                credential_id=str(row.get("credential_id") or ""),
                subject_id=str(row.get("subject_id") or ""),
                subject_name=str(row.get("subject_name") or row.get("name") or ""),
                subject_role=str(row.get("subject_role") or row.get("role") or ""),
                provider=str(row.get("provider") or ""),
                template=template,
                vector=vector,
            )
        )
    return entries


def match_face_vector(
    vector: np.ndarray,
    rows: list[dict[str, Any]],
    *,
    recognized_threshold: float = DEFAULT_RECOGNIZED_THRESHOLD,
    candidate_threshold: float = DEFAULT_CANDIDATE_THRESHOLD,
) -> dict[str, Any]:
    best_entry: GalleryEntry | None = None
    best_score = 0.0
    for entry in gallery_entries(rows):
        score = cosine_similarity(vector, entry.vector)
        if score > best_score:
            best_entry = entry
            best_score = score

    if best_entry is None:
        return {
            "type": "face",
            "auth_method": "face",
            "identity_state": "no_gallery",
            "subject_id": "",
            "confidence": 0.0,
            "score": 0.0,
        }

    if best_score >= recognized_threshold:
        identity_state = "recognized"
        assurance_level = "medium" if best_score < 0.9 else "high"
    elif best_score >= candidate_threshold:
        identity_state = "candidate"
        assurance_level = "low"
    else:
        identity_state = "unknown"
        assurance_level = "none"

    return {
        "type": "face",
        "auth_method": "face",
        "identity_state": identity_state,
        "subject_id": best_entry.subject_id if identity_state in ("recognized", "candidate") else "",
        "subject_name": best_entry.subject_name if identity_state in ("recognized", "candidate") else "",
        "subject_role": best_entry.subject_role if identity_state in ("recognized", "candidate") else "",
        "credential_id": best_entry.credential_id if identity_state in ("recognized", "candidate") else "",
        "provider": best_entry.provider if identity_state in ("recognized", "candidate") else "",
        "confidence": round(max(0.0, min(1.0, best_score)), 4),
        "score": round(best_score, 4),
        "assurance_level": assurance_level,
        "recognized_threshold": recognized_threshold,
        "candidate_threshold": candidate_threshold,
    }


def match_face_image_b64(
    image_b64: str,
    rows: list[dict[str, Any]],
    *,
    detector_model_path: str = "",
    detect_face: bool = True,
    score_threshold: float = 0.75,
    recognized_threshold: float = DEFAULT_RECOGNIZED_THRESHOLD,
    candidate_threshold: float = DEFAULT_CANDIDATE_THRESHOLD,
) -> dict[str, Any]:
    template = build_face_template_from_image_b64(
        image_b64,
        detector_model_path=detector_model_path,
        detect_face=detect_face,
        score_threshold=score_threshold,
    )
    vector = template_vector(template)
    identity = match_face_vector(
        vector,
        rows,
        recognized_threshold=recognized_threshold,
        candidate_threshold=candidate_threshold,
    )
    identity["probe_template_meta"] = {
        "schema": template.get("schema", ""),
        "model": (template.get("embedding") or {}).get("model", ""),
        "dim": (template.get("embedding") or {}).get("dim", 0),
        "face": template.get("face", {}),
    }
    return identity
