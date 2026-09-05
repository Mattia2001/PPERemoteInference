from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    api_version: str = os.getenv("PPE_API_VERSION", "1.0")
    backend: str = os.getenv("PPE_BACKEND", "mock").lower()
    model_path: str = os.getenv("PPE_MODEL_PATH", "/models/best.pt")
    model_id: str = os.getenv("PPE_MODEL_ID", "yolo26n-ppe-v2-960")
    model_version: str = os.getenv("PPE_MODEL_VERSION", "1")
    runtime: str = os.getenv("PPE_RUNTIME", "ultralytics")
    device: str = os.getenv("PPE_DEVICE", "cuda:0")
    input_size: int = _int("PPE_INPUT_SIZE", 960)
    confidence: float = _float("PPE_CONFIDENCE", 0.25)
    iou: float = _float("PPE_IOU", 0.45)
    max_payload_bytes: int = _int("PPE_MAX_PAYLOAD_BYTES", 8 * 1024 * 1024)
    max_concurrency: int = _int("PPE_MAX_CONCURRENCY", 1)
    queue_timeout_ms: float = _float("PPE_QUEUE_TIMEOUT_MS", 100.0)
    warmup_runs: int = _int("PPE_WARMUP_RUNS", 1)
    warmup_frame_width: int = _int("PPE_WARMUP_FRAME_WIDTH", 1080)
    warmup_frame_height: int = _int("PPE_WARMUP_FRAME_HEIGHT", 1920)
    bearer_token: str | None = os.getenv("PPE_BEARER_TOKEN") or None

    def validate(self) -> None:
        if self.backend not in {"mock", "ultralytics"}:
            raise ValueError("PPE_BACKEND must be mock or ultralytics")
        if (
            self.input_size <= 0
            or self.max_payload_bytes <= 0
            or self.max_concurrency <= 0
            or self.queue_timeout_ms <= 0
            or self.warmup_frame_width <= 0
            or self.warmup_frame_height <= 0
        ):
            raise ValueError("size and concurrency settings must be positive")
        if self.warmup_runs < 0:
            raise ValueError("PPE_WARMUP_RUNS must be zero or positive")
        if not 0.0 <= self.confidence <= 1.0 or not 0.0 <= self.iou <= 1.0:
            raise ValueError("confidence and IoU must be in [0, 1]")
