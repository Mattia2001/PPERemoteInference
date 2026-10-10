"""Explicit color boundary between JPEG/PIL RGB and Ultralytics NumPy BGR."""

import io
import numpy as np
from PIL import Image


def decode_rgb(payload: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        return np.asarray(image.convert("RGB"))


def to_ultralytics_bgr(rgb: np.ndarray) -> np.ndarray:
    """The pinned Ultralytics predictor treats HWC NumPy input as BGR."""
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("Expected an HWC RGB uint8 image")
    return np.ascontiguousarray(rgb[:, :, ::-1])
