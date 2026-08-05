from __future__ import annotations

import time
from dataclasses import dataclass


def now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class FramePacket:
    frame: object = None
    ts: int = 0
    source: str = "unknown"
    source_state: str = "idle"
    notes: str = ""


class MockFrameSource:
    def __init__(self, default_label: str = "自然"):
        self.default_label = default_label

    def open(self) -> None:
        return None

    def read(self) -> FramePacket:
        return FramePacket(
            frame=None,
            ts=now_ms(),
            source="mock",
            source_state="mock",
            notes=f"default_label={self.default_label}",
        )

    def close(self) -> None:
        return None


class OpenCVCameraSource:
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480):
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cv2 = None
        self.cap = None

    def open(self) -> None:
        import cv2

        self.cv2 = cv2
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError(f"无法打开摄像头 index={self.camera_index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    def read(self) -> FramePacket:
        if self.cap is None:
            raise RuntimeError("摄像头尚未初始化")
        ok, frame = self.cap.read()
        if not ok or frame is None:
            return FramePacket(
                frame=None,
                ts=now_ms(),
                source="camera",
                source_state="read_failed",
                notes=f"camera_index={self.camera_index}",
            )
        return FramePacket(
            frame=frame,
            ts=now_ms(),
            source="camera",
            source_state="ready",
            notes=f"camera_index={self.camera_index}",
        )

    def close(self) -> None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None
