from __future__ import annotations

import asyncio
import io
import json
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass

import numpy as np
from fastapi import Depends, FastAPI, File, Form, Header, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest
from pydantic import ValidationError

from .backend import Prediction, create_backend, gpu_snapshot
from .config import Settings
from .schemas import (
    CANONICAL_CLASSES,
    Box,
    Detection,
    ErrorDetail,
    ErrorResponse,
    ImageInfo,
    InferenceMetadata,
    InferenceResponse,
    ModelInfo,
    Timing,
)

REQUESTS = Counter("ppe_inference_requests_total", "Inference requests", ["outcome"])
LATENCY = Histogram("ppe_inference_server_seconds", "Total server request latency")
QUEUE = Histogram("ppe_inference_queue_seconds", "Inference queue wait")
IN_FLIGHT = Gauge("ppe_inference_in_flight", "Inference requests currently executing")
QUEUE_DEPTH = Gauge("ppe_inference_queue_depth", "Inference requests waiting for an execution slot")
MAX_CONCURRENCY = Gauge("ppe_inference_max_concurrency", "Configured inference execution slots")
WARMUP = Gauge("ppe_inference_warmup_seconds", "Model warm-up duration at service startup")
MODEL = Info("ppe_inference_model", "Currently deployed inference model")
REQUEST_BYTES = Histogram(
    "ppe_inference_request_bytes",
    "Encoded image payload size",
    buckets=(65536, 131072, 262144, 393216, 524288, 786432, 1048576, 2097152, 4194304, 8388608),
)
STAGE_BUCKETS = (0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5)
DECODE = Histogram("ppe_inference_decode_seconds", "Image decode latency", buckets=STAGE_BUCKETS)
PREPROCESS = Histogram("ppe_inference_preprocess_seconds", "Model preprocess latency", buckets=STAGE_BUCKETS)
MODEL_LATENCY = Histogram("ppe_inference_model_seconds", "Model inference latency", buckets=STAGE_BUCKETS)
POSTPROCESS = Histogram("ppe_inference_postprocess_seconds", "Model postprocess latency", buckets=STAGE_BUCKETS)


@dataclass
class ApiError(Exception):
    status_code: int
    code: str
    message: str
    retryable: bool = False
    frame_id: str | None = None
    sequence_number: int | None = None


def _now_ms() -> int:
    return int(time.time() * 1000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    settings.validate()
    app.state.settings = settings
    app.state.backend = create_backend(settings)
    warmup_started = time.perf_counter()
    await asyncio.to_thread(app.state.backend.warm_up, settings.warmup_runs)
    warmup_ms = (time.perf_counter() - warmup_started) * 1000.0
    app.state.warmup = {
        "runs": settings.warmup_runs,
        "durationMs": round(warmup_ms, 3),
        "completed": True,
    }
    WARMUP.set(warmup_ms / 1000.0)
    app.state.semaphore = asyncio.Semaphore(settings.max_concurrency)
    MAX_CONCURRENCY.set(settings.max_concurrency)
    MODEL.info(
        {
            "model_id": settings.model_id,
            "model_version": settings.model_version,
            "runtime": "mock" if settings.backend == "mock" else settings.runtime,
            "device": "cpu" if settings.backend == "mock" else settings.device,
            "input_size": str(settings.input_size),
        }
    )
    yield


app = FastAPI(title="PPE Remote Inference", version="1.0", lifespan=lifespan)


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    REQUESTS.labels(outcome=exc.code.lower()).inc()
    payload = ErrorResponse(
        apiVersion="1.0",
        error=ErrorDetail(code=exc.code, message=exc.message, retryable=exc.retryable),
        frameId=exc.frame_id,
        sequenceNumber=exc.sequence_number,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(by_alias=True))


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    error = ErrorResponse(
        apiVersion="1.0",
        error=ErrorDetail(code="INVALID_REQUEST", message="Invalid multipart request", retryable=False),
    )
    REQUESTS.labels(outcome="invalid_request").inc()
    return JSONResponse(status_code=422, content=error.model_dump(by_alias=True))


@app.exception_handler(Exception)
async def internal_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = ErrorResponse(
        apiVersion="1.0",
        error=ErrorDetail(code="INTERNAL_ERROR", message="Internal inference service error", retryable=True),
    )
    REQUESTS.labels(outcome="internal_error").inc()
    return JSONResponse(status_code=500, content=error.model_dump(by_alias=True))


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def authorize(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if settings.bearer_token is None:
        return
    if authorization != f"Bearer {settings.bearer_token}":
        raise ApiError(401, "UNAUTHORIZED", "Invalid or missing bearer token")


def _parse_metadata(raw: str, settings: Settings) -> InferenceMetadata:
    try:
        metadata = InferenceMetadata.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ApiError(422, "INVALID_METADATA", "Metadata does not match API v1") from exc
    identity = {"frame_id": metadata.frame_id, "sequence_number": metadata.sequence_number}
    if metadata.api_version != settings.api_version:
        raise ApiError(400, "API_VERSION_MISMATCH", "Unsupported API version", False, **identity)
    if metadata.model_id != settings.model_id:
        raise ApiError(409, "MODEL_MISMATCH", "Requested model is not deployed", False, **identity)
    return metadata


def _decode_image(payload: bytes) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.load()
            return np.asarray(image.convert("RGB"))
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ApiError(422, "INVALID_IMAGE", "Frame is not a valid JPEG or PNG") from exc


def _model_info(settings: Settings) -> ModelInfo:
    runtime = "mock" if settings.backend == "mock" else settings.runtime
    device = "cpu" if settings.backend == "mock" else settings.device
    return ModelInfo(
        modelId=settings.model_id,
        modelVersion=settings.model_version,
        runtime=runtime,
        device=device,
        inputSize=settings.input_size,
    )


def _serialize_detections(
    prediction: Prediction,
    width: int,
    height: int,
    selected: set[str],
) -> list[Detection]:
    visible = [item for item in prediction.detections if not selected or item.class_name in selected]
    person_indices = [index for index, item in enumerate(visible) if item.class_name == "person"]
    person_ids = {index: f"det_person_{position}" for position, index in enumerate(person_indices)}
    output: list[Detection] = []
    for index, item in enumerate(visible):
        x1, y1, x2, y2 = item.xyxy
        associated: str | None = person_ids.get(index)
        if item.class_name != "person":
            center_x, center_y = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            containing: list[tuple[float, int]] = []
            for person_index in person_indices:
                px1, py1, px2, py2 = visible[person_index].xyxy
                if px1 <= center_x <= px2 and py1 <= center_y <= py2:
                    containing.append(((px2 - px1) * (py2 - py1), person_index))
            if containing:
                associated = person_ids[min(containing)[1]]
        output.append(
            Detection(
                detectionId=person_ids.get(index, f"det_{index}"),
                classId=item.class_id,
                className=item.class_name,
                confidence=item.confidence,
                boxNormalized=Box(x=x1 / width, y=y1 / height, width=(x2 - x1) / width, height=(y2 - y1) / height),
                boxPixels=Box(x=x1, y=y1, width=x2 - x1, height=y2 - y1),
                associatedPersonId=associated,
            )
        )
    return output


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
@app.get("/v1/ready")
async def ready(request: Request) -> dict[str, object]:
    if not request.app.state.backend.ready:
        raise ApiError(503, "NOT_READY", "Inference backend is not ready", True)
    return {"status": "ready", "apiVersion": request.app.state.settings.api_version, "model": _model_info(request.app.state.settings).model_dump(by_alias=True)}


@app.get("/v1/capabilities", dependencies=[Depends(authorize)])
async def capabilities(request: Request) -> dict[str, object]:
    return {
        "apiVersion": request.app.state.settings.api_version,
        "model": _model_info(request.app.state.settings).model_dump(by_alias=True),
        "classes": list(CANONICAL_CLASSES),
        "transports": ["http-multipart"],
    }


@app.get("/v1/status", dependencies=[Depends(authorize)])
async def status(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    semaphore = request.app.state.semaphore
    return {
        "apiVersion": settings.api_version,
        "status": "ready" if request.app.state.backend.ready else "not_ready",
        "model": _model_info(settings).model_dump(by_alias=True),
        "queue": {"maxConcurrency": settings.max_concurrency, "availableSlots": semaphore._value},
        "warmUp": request.app.state.warmup,
        "gpu": gpu_snapshot(),
    }


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/inference", response_model=InferenceResponse, dependencies=[Depends(authorize)])
async def inference(
    request: Request,
    frame: UploadFile = File(...),
    metadata: str = Form(...),
) -> InferenceResponse:
    started = time.perf_counter()
    received_ms = _now_ms()
    settings = request.app.state.settings
    parsed = _parse_metadata(metadata, settings)
    identity = {"frame_id": parsed.frame_id, "sequence_number": parsed.sequence_number}
    if not request.app.state.backend.ready:
        raise ApiError(503, "NOT_READY", "Inference backend is not ready", True, **identity)
    if frame.content_type not in {"image/jpeg", "image/png"}:
        raise ApiError(415, "UNSUPPORTED_MEDIA_TYPE", "Only JPEG and PNG are supported", False, **identity)
    payload = await frame.read(settings.max_payload_bytes + 1)
    REQUEST_BYTES.observe(len(payload))
    if len(payload) > settings.max_payload_bytes:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "Frame exceeds configured payload limit", False, **identity)

    decode_started = time.perf_counter()
    try:
        image = await asyncio.to_thread(_decode_image, payload)
    except ApiError as exc:
        exc.frame_id = parsed.frame_id
        exc.sequence_number = parsed.sequence_number
        raise
    decode_ms = (time.perf_counter() - decode_started) * 1000.0
    DECODE.observe(decode_ms / 1000.0)
    height, width = image.shape[:2]

    queue_started = time.perf_counter()
    QUEUE_DEPTH.inc()
    try:
        await asyncio.wait_for(
            request.app.state.semaphore.acquire(),
            timeout=settings.queue_timeout_ms / 1000.0,
        )
    except TimeoutError as exc:
        QUEUE.observe(time.perf_counter() - queue_started)
        raise ApiError(503, "OVERLOADED", "Inference queue deadline exceeded", True, **identity) from exc
    finally:
        QUEUE_DEPTH.dec()
    queue_ms = (time.perf_counter() - queue_started) * 1000.0
    QUEUE.observe(queue_ms / 1000.0)
    IN_FLIGHT.inc()
    try:
        prediction = await asyncio.to_thread(request.app.state.backend.predict, image)
    finally:
        IN_FLIGHT.dec()
        request.app.state.semaphore.release()

    detections = _serialize_detections(prediction, width, height, set(parsed.selected_classes))
    PREPROCESS.observe(prediction.preprocess_ms / 1000.0)
    MODEL_LATENCY.observe(prediction.inference_ms / 1000.0)
    POSTPROCESS.observe(prediction.postprocess_ms / 1000.0)
    total_ms = (time.perf_counter() - started) * 1000.0
    LATENCY.observe(total_ms / 1000.0)
    REQUESTS.labels(outcome="success").inc()
    return InferenceResponse(
        apiVersion=settings.api_version,
        frameId=parsed.frame_id,
        sequenceNumber=parsed.sequence_number,
        captureTimestampMs=parsed.capture_timestamp_ms,
        serverReceiveTimestampMs=received_ms,
        serverCompleteTimestampMs=_now_ms(),
        model=_model_info(settings),
        image=ImageInfo(width=width, height=height),
        detections=detections,
        timing=Timing(
            queueMs=queue_ms,
            decodeMs=decode_ms,
            preprocessMs=prediction.preprocess_ms,
            inferenceMs=prediction.inference_ms,
            postprocessMs=prediction.postprocess_ms,
            totalServerMs=total_ms,
        ),
    )
