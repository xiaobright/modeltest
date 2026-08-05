from __future__ import annotations

import os
from collections import deque

import numpy as np

IMAGE_SIZE = (112, 112)
SEQUENCE_LENGTH = 3
SMOOTH_WINDOW = 12
NORM_MEAN = np.asarray([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
NORM_STD = np.asarray([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)
EMOTION_LABELS = ["愤怒", "蔑视", "厌恶", "恐惧", "开心", "自然", "悲伤", "惊讶"]


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - np.max(x)
    exp_x = np.exp(x)
    return exp_x / np.sum(exp_x)


class OnnxEmotionRuntime:
    def __init__(self, model_path: str):
        import cv2
        import onnxruntime as ort

        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"未找到情绪 ONNX 模型: {model_path}")

        self.cv2 = cv2
        self.ort = ort
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        self.frame_queues: dict[int, deque[np.ndarray]] = {}
        self.prob_queues: dict[int, deque[np.ndarray]] = {}

    def _preprocess(self, face_bgr: np.ndarray) -> np.ndarray:
        img_rgb = self.cv2.cvtColor(face_bgr, self.cv2.COLOR_BGR2RGB)
        img_resized = self.cv2.resize(img_rgb, IMAGE_SIZE)
        x = img_resized.astype(np.float32) / 255.0
        x = (x - NORM_MEAN) / NORM_STD
        return np.transpose(x, (2, 0, 1))

    def predict(self, face_bgr: np.ndarray, face_id: int = 0):
        if face_id not in self.frame_queues:
            self.frame_queues[face_id] = deque(maxlen=SEQUENCE_LENGTH)
        if face_id not in self.prob_queues:
            self.prob_queues[face_id] = deque(maxlen=SMOOTH_WINDOW)

        x = self._preprocess(face_bgr)
        frame_q = self.frame_queues[face_id]
        frame_q.append(x)

        seq = list(frame_q)
        while len(seq) < SEQUENCE_LENGTH:
            seq.append(seq[-1])

        model_input = np.stack(seq, axis=0)[None, ...].astype(np.float32)
        outputs = self.session.run(None, {self.input_name: model_input})
        logits = np.asarray(outputs[0], dtype=np.float32)[0]
        probs = softmax(logits)

        prob_q = self.prob_queues[face_id]
        prob_q.append(probs)
        avg_probs = np.mean(np.stack(list(prob_q), axis=0), axis=0)

        best_idx = int(np.argmax(avg_probs))
        label = EMOTION_LABELS[best_idx]
        score = float(avg_probs[best_idx])
        prob_map = {EMOTION_LABELS[i]: round(float(avg_probs[i]), 4) for i in range(len(EMOTION_LABELS))}
        return label, score, prob_map
