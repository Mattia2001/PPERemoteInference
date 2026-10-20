from __future__ import annotations

import io
import hashlib
import json

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, _checkpoint_sha256
from app.backend import Prediction, RawDetection


def test_checkpoint_hash_is_derived_from_file_bytes(tmp_path) -> None:
    checkpoint = tmp_path / "best.pt"
    checkpoint.write_bytes(b"checkpoint-content")
    assert _checkpoint_sha256(str(checkpoint)) == hashlib.sha256(b"checkpoint-content").hexdigest()


def jpeg_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), color=(20, 40, 60)).save(buffer, format="JPEG")
    return buffer.getvalue()


def metadata(**updates: object) -> str:
    value: dict[str, object] = {
        "apiVersion": "1.0",
        "frameId": "frame_000001",
        "sequenceNumber": 1,
        "captureTimestampMs": 1782900984463,
        "modelId": "yolo26n-ppe-v2-960",
        "selectedClasses": [],
    }
    value.update(updates)
    return json.dumps(value)


def test_health_and_readiness() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        response = client.get("/v1/ready")
        assert response.status_code == 200
        assert response.json()["model"]["runtime"] == "mock"
        assert response.json()["model"]["modelSha256"] is None


def test_status_reports_completed_warmup() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/status")
    assert response.status_code == 200
    assert response.json()["warmUp"]["completed"] is True


def test_inference_echoes_identity_and_image_shape() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/inference",
            files={"frame": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
            data={"metadata": metadata()},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["frameId"] == "frame_000001"
    assert body["sequenceNumber"] == 1
    assert body["image"] == {"width": 64, "height": 48}
    assert body["detections"] == []
    assert body["allDetections"] == []
    assert body["timing"]["totalServerMs"] >= 0


def test_all_detections_preserve_unselected_and_unmatched_ppe() -> None:
    class FixedBackend:
        ready = True

        def predict(self, image):
            return Prediction(detections=[
                RawDetection(0, "person", 0.9, (0.0, 0.0, 20.0, 20.0)),
                RawDetection(1, "helmet", 0.8, (2.0, 2.0, 8.0, 8.0)),
                RawDetection(3, "gloves", 0.7, (40.0, 30.0, 46.0, 36.0)),
            ])

    with TestClient(app) as client:
        app.state.backend = FixedBackend()
        response = client.post(
            "/v1/inference",
            files={"frame": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
            data={"metadata": metadata(selectedClasses=["person", "helmet"])},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [item["className"] for item in body["detections"]] == ["person", "helmet"]
    assert [item["className"] for item in body["allDetections"]] == ["person", "helmet", "gloves"]
    assert body["allDetections"][2]["associatedPersonId"] is None


def test_model_mismatch_is_stable_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/inference",
            files={"frame": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
            data={"metadata": metadata(modelId="unknown")},
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "MODEL_MISMATCH"
    assert response.json()["frameId"] == "frame_000001"


def test_invalid_image_is_stable_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/inference",
            files={"frame": ("frame.jpg", b"not-an-image", "image/jpeg")},
            data={"metadata": metadata()},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_IMAGE"


def test_metrics_expose_bounded_operational_telemetry() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/v1/inference",
            files={"frame": ("frame.jpg", jpeg_bytes(), "image/jpeg")},
            data={"metadata": metadata()},
        )
        assert response.status_code == 200
        metrics = client.get("/metrics").text

    assert "ppe_inference_requests_total" in metrics
    assert "ppe_inference_request_bytes_bucket" in metrics
    assert "ppe_inference_queue_depth" in metrics
    assert "ppe_inference_model_seconds_bucket" in metrics
    assert 'model_id="yolo26n-ppe-v2-960"' in metrics
    assert "frame_000001" not in metrics
