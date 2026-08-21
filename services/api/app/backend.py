from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from .config import Settings
from .schemas import CANONICAL_CLASSES


@dataclass(frozen=True)
class RawDetection:
    class_id: int
    class_name: str
    confidence: float
    xyxy: tuple[float, float, float, float]


@dataclass(frozen=True)
class Prediction:
    detections: list[RawDetection]
    preprocess_ms: float = 0.0
    inference_ms: float = 0.0
    postprocess_ms: float = 0.0


class Backend(Protocol):
    ready: bool

    def predict(self, image: np.ndarray) -> Prediction: ...


class MockBackend:
    ready = True

    def predict(self, image: np.ndarray) -> Prediction:
        return Prediction(detections=[])


class UltralyticsBackend:
    def __init__(self, settings: Settings) -> None:
        from ultralytics import YOLO

        path = Path(settings.model_path)
        if not path.is_file():
            raise FileNotFoundError(f"Model not found: {path}")
        self.settings = settings
        self.model = YOLO(str(path), task="detect")
        self.ready = True

    def predict(self, image: np.ndarray) -> Prediction:
        result = self.model.predict(
            source=image,
            imgsz=self.settings.input_size,
            conf=self.settings.confidence,
            iou=self.settings.iou,
            device=self.settings.device,
            verbose=False,
        )[0]
        names = result.names
        detections: list[RawDetection] = []
        if result.boxes is not None:
            for box, confidence, class_id in zip(
                result.boxes.xyxy.cpu().tolist(),
                result.boxes.conf.cpu().tolist(),
                result.boxes.cls.cpu().tolist(),
                strict=True,
            ):
                class_id_int = int(class_id)
                class_name = str(names[class_id_int])
                if class_name not in CANONICAL_CLASSES:
                    continue
                detections.append(
                    RawDetection(
                        class_id=class_id_int,
                        class_name=class_name,
                        confidence=float(confidence),
                        xyxy=tuple(float(value) for value in box),
                    )
                )
        speed = result.speed or {}
        return Prediction(
            detections=detections,
            preprocess_ms=float(speed.get("preprocess", 0.0)),
            inference_ms=float(speed.get("inference", 0.0)),
            postprocess_ms=float(speed.get("postprocess", 0.0)),
        )


def create_backend(settings: Settings) -> Backend:
    if settings.backend == "mock":
        return MockBackend()
    return UltralyticsBackend(settings)


def gpu_snapshot() -> dict[str, object] | None:
    """Return a bounded best-effort GPU snapshot without making readiness depend on NVML."""
    try:
        import pynvml

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode()
        return {
            "name": str(name),
            "utilizationPercent": int(utilization.gpu),
            "memoryUsedMiB": round(memory.used / 2**20, 1),
            "memoryTotalMiB": round(memory.total / 2**20, 1),
        }
    except Exception:
        return None
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass
