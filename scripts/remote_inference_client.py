"""Sequential reference client for PPE Remote Inference API v1."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
from PIL import Image


CANONICAL_CLASSES = ("person", "helmet", "safety_vest", "gloves", "safety_boots")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


@dataclass(frozen=True)
class EncodedFrame:
    payload: bytes
    source_name: str
    source_frame_index: int
    source_timestamp_ms: float | None
    capture_timestamp_ms: int
    encode_ms: float


def _encode_rgb(image: Image.Image, quality: int) -> tuple[bytes, float]:
    started = time.perf_counter()
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue(), (time.perf_counter() - started) * 1000.0


def _image_frames(path: Path, quality: int) -> Iterator[EncodedFrame]:
    with Image.open(path) as image:
        payload, encode_ms = _encode_rgb(image, quality)
    yield EncodedFrame(payload, path.name, 0, None, int(time.time() * 1000), encode_ms)


def _directory_frames(path: Path, quality: int) -> Iterator[EncodedFrame]:
    images = sorted(item for item in path.rglob("*") if item.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        raise ValueError(f"No JPEG or PNG images found under {path}")
    for index, image_path in enumerate(images):
        with Image.open(image_path) as image:
            payload, encode_ms = _encode_rgb(image, quality)
        yield EncodedFrame(
            payload, str(image_path.relative_to(path)), index, None,
            int(time.time() * 1000), encode_ms,
        )


def _video_frames(path: Path, quality: int, every_n: int) -> Iterator[EncodedFrame]:
    try:
        import cv2  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Video input requires opencv-python-headless") from exc
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"Cannot open video: {path}")
    source_index = 0
    try:
        while True:
            ok, bgr = capture.read()
            if not ok:
                break
            source_timestamp_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC))
            if source_index % every_n:
                source_index += 1
                continue
            started = time.perf_counter()
            encoded_ok, encoded = cv2.imencode(
                ".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            )
            encode_ms = (time.perf_counter() - started) * 1000.0
            if not encoded_ok:
                raise RuntimeError(f"JPEG encoding failed at video frame {source_index}")
            yield EncodedFrame(
                encoded.tobytes(), path.name, source_index, source_timestamp_ms,
                int(time.time() * 1000), encode_ms,
            )
            source_index += 1
    finally:
        capture.release()


def iter_frames(path: Path, quality: int, every_n: int) -> Iterator[EncodedFrame]:
    if path.is_dir():
        yield from _directory_frames(path, quality)
    elif path.suffix.lower() in IMAGE_SUFFIXES:
        yield from _image_frames(path, quality)
    elif path.suffix.lower() in VIDEO_SUFFIXES:
        yield from _video_frames(path, quality, every_n)
    else:
        raise ValueError(f"Unsupported input: {path}")


def build_metadata(frame: EncodedFrame, sequence_number: int, model_id: str,
                   selected_classes: list[str]) -> dict[str, Any]:
    return {
        "apiVersion": "1.0",
        "frameId": f"frame_{sequence_number:08d}_{uuid.uuid4().hex[:8]}",
        "sequenceNumber": sequence_number,
        "captureTimestampMs": frame.capture_timestamp_ms,
        "modelId": model_id,
        "selectedClasses": selected_classes,
    }


def _headers(token: str | None) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def run(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    base_url = args.server.rstrip("/")
    token = args.token or os.environ.get("PPE_BEARER_TOKEN")
    selected_classes = args.classes or list(CANONICAL_CLASSES)
    unknown = set(selected_classes) - set(CANONICAL_CLASSES)
    if unknown:
        raise ValueError(f"Unknown classes: {sorted(unknown)}")

    success_count = 0
    error_count = 0
    limits = httpx.Limits(max_connections=1, max_keepalive_connections=1)
    with httpx.Client(timeout=args.timeout, headers=_headers(token), limits=limits) as client:
        status_response = client.get(f"{base_url}/v1/status")
        status_response.raise_for_status()
        status = status_response.json()
        deployed_model = status.get("model", {}).get("modelId")
        if status.get("status") != "ready":
            raise RuntimeError(f"Server is not ready: {status}")
        if deployed_model != args.model_id:
            raise RuntimeError(
                f"Model mismatch: requested {args.model_id!r}, server exposes {deployed_model!r}"
            )
        print(json.dumps({"preflight": status}, ensure_ascii=False))

        with output_path.open("w", encoding="utf-8", newline="\n") as output:
            frames = iter_frames(input_path, args.jpeg_quality, args.every_n_frames)
            for sequence_number, frame in enumerate(frames):
                if args.max_frames is not None and sequence_number >= args.max_frames:
                    break
                metadata = build_metadata(frame, sequence_number, args.model_id, selected_classes)
                request_started_epoch_ms = int(time.time() * 1000)
                request_started = time.perf_counter()
                try:
                    response = client.post(
                        f"{base_url}/v1/inference",
                        files={"frame": ("frame.jpg", frame.payload, "image/jpeg")},
                        data={"metadata": json.dumps(metadata, separators=(",", ":"))},
                    )
                    round_trip_ms = (time.perf_counter() - request_started) * 1000.0
                    body = response.json()
                    response.raise_for_status()
                    server_ms = float(body["timing"]["totalServerMs"])
                    record = {
                        "recordType": "remoteInference",
                        "client": {
                            "source": frame.source_name,
                            "sourceFrameIndex": frame.source_frame_index,
                            "sourceTimestampMs": frame.source_timestamp_ms,
                            "encodedBytes": len(frame.payload),
                            "encodeMs": round(frame.encode_ms, 3),
                            "requestStartTimestampMs": request_started_epoch_ms,
                            "roundTripMs": round(round_trip_ms, 3),
                            "transportAndApiOverheadMs": round(max(0.0, round_trip_ms - server_ms), 3),
                            "sequentialRequest": True,
                        },
                        "response": body,
                    }
                    success_count += 1
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    round_trip_ms = (time.perf_counter() - request_started) * 1000.0
                    record = {
                        "recordType": "remoteInferenceError",
                        "client": {
                            "source": frame.source_name,
                            "sourceFrameIndex": frame.source_frame_index,
                            "sourceTimestampMs": frame.source_timestamp_ms,
                            "encodedBytes": len(frame.payload),
                            "encodeMs": round(frame.encode_ms, 3),
                            "requestStartTimestampMs": request_started_epoch_ms,
                            "roundTripMs": round(round_trip_ms, 3),
                            "sequentialRequest": True,
                        },
                        "request": metadata,
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                    }
                    error_count += 1
                    if args.fail_fast:
                        output.write(json.dumps(record, ensure_ascii=False) + "\n")
                        raise
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
                output.flush()
                if (success_count + error_count) % args.progress_every == 0:
                    print(f"frames={success_count + error_count} ok={success_count} errors={error_count}")

    print(f"Completed: ok={success_count}, errors={error_count}, output={output_path}")
    return 0 if success_count > 0 and error_count == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--input", required=True, help="JPEG/PNG, image directory or video")
    parser.add_argument("--output", required=True, help="JSONL output path (overwritten)")
    parser.add_argument("--token", help="Bearer token; PPE_BEARER_TOKEN is used when omitted")
    parser.add_argument("--classes", nargs="*", choices=CANONICAL_CLASSES)
    parser.add_argument("--jpeg-quality", type=int, default=85, choices=range(1, 101), metavar="1..100")
    parser.add_argument("--every-n-frames", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--progress-every", type=int, default=25)
    parser.add_argument("--fail-fast", action="store_true")
    args = parser.parse_args(argv)
    if args.every_n_frames < 1 or args.progress_every < 1:
        parser.error("--every-n-frames and --progress-every must be positive")
    if args.max_frames is not None and args.max_frames < 1:
        parser.error("--max-frames must be positive")
    return args


if __name__ == "__main__":
    try:
        raise SystemExit(run(parse_args()))
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
