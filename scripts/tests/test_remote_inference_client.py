from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts import remote_inference_client as client_module


class FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self._body = body

    def json(self) -> dict[str, object]:
        return self._body

    def raise_for_status(self) -> None:
        return None


class FakeClient:
    def __init__(self, **_: object) -> None:
        pass

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get(self, url: str) -> FakeResponse:
        assert url.endswith("/v1/status")
        return FakeResponse({
            "status": "ready",
            "model": {"modelId": "yolo26n-ppe-v2-640"},
        })

    def post(self, url: str, *, files: dict[str, tuple[str, bytes, str]],
             data: dict[str, str]) -> FakeResponse:
        assert url.endswith("/v1/inference")
        assert files["frame"][2] == "image/jpeg"
        metadata = json.loads(data["metadata"])
        return FakeResponse({
            "apiVersion": "1.0",
            "frameId": metadata["frameId"],
            "sequenceNumber": metadata["sequenceNumber"],
            "captureTimestampMs": metadata["captureTimestampMs"],
            "timing": {"totalServerMs": 3.0, "inferenceMs": 1.0},
            "detections": [],
        })


def test_image_round_trip_writes_ordered_jsonl(tmp_path: Path, monkeypatch) -> None:
    image_path = tmp_path / "frame.png"
    output_path = tmp_path / "result.jsonl"
    Image.new("RGB", (32, 24), (10, 20, 30)).save(image_path)
    monkeypatch.setattr(client_module.httpx, "Client", FakeClient)

    args = client_module.parse_args([
        "--server", "http://server:8081",
        "--model-id", "yolo26n-ppe-v2-640",
        "--input", str(image_path),
        "--output", str(output_path),
    ])
    assert client_module.run(args) == 0
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["recordType"] == "remoteInference"
    assert rows[0]["response"]["sequenceNumber"] == 0
    assert rows[0]["client"]["encodedBytes"] > 0
    assert rows[0]["client"]["sequentialRequest"] is True
