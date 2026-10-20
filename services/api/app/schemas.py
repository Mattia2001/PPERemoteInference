from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


CANONICAL_CLASSES = ("person", "helmet", "safety_vest", "gloves", "safety_boots")


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class InferenceMetadata(ApiModel):
    api_version: str = Field(alias="apiVersion")
    frame_id: str = Field(alias="frameId", min_length=1, max_length=128)
    sequence_number: int = Field(alias="sequenceNumber", ge=0)
    capture_timestamp_ms: int = Field(alias="captureTimestampMs", ge=0)
    model_id: str = Field(alias="modelId", min_length=1)
    selected_classes: list[str] = Field(default_factory=list, alias="selectedClasses")

    @field_validator("selected_classes")
    @classmethod
    def canonical_classes_only(cls, values: list[str]) -> list[str]:
        unknown = set(values) - set(CANONICAL_CLASSES)
        if unknown:
            raise ValueError(f"unknown selected classes: {sorted(unknown)}")
        return list(dict.fromkeys(values))


class Box(ApiModel):
    x: float
    y: float
    width: float
    height: float


class Detection(ApiModel):
    detection_id: str = Field(alias="detectionId")
    class_id: int = Field(alias="classId")
    class_name: str = Field(alias="className")
    confidence: float
    box_normalized: Box = Field(alias="boxNormalized")
    box_pixels: Box = Field(alias="boxPixels")
    associated_person_id: str | None = Field(default=None, alias="associatedPersonId")


class ModelInfo(ApiModel):
    model_id: str = Field(alias="modelId")
    model_version: str = Field(alias="modelVersion")
    model_sha256: str | None = Field(default=None, alias="modelSha256")
    runtime: str
    device: str
    input_size: int = Field(alias="inputSize")


class ImageInfo(ApiModel):
    width: int
    height: int


class Timing(ApiModel):
    queue_ms: float = Field(alias="queueMs")
    decode_ms: float = Field(alias="decodeMs")
    preprocess_ms: float = Field(alias="preprocessMs")
    inference_ms: float = Field(alias="inferenceMs")
    postprocess_ms: float = Field(alias="postprocessMs")
    total_server_ms: float = Field(alias="totalServerMs")


class PostprocessInfo(ApiModel):
    confidence_threshold: float = Field(alias="confidenceThreshold")
    iou_threshold: float = Field(alias="iouThreshold")
    max_detections: int = Field(alias="maxDetections")
    output_limit_reached: bool = Field(alias="outputLimitReached")


class InferenceResponse(ApiModel):
    api_version: str = Field(alias="apiVersion")
    frame_id: str = Field(alias="frameId")
    sequence_number: int = Field(alias="sequenceNumber")
    capture_timestamp_ms: int = Field(alias="captureTimestampMs")
    server_receive_timestamp_ms: int = Field(alias="serverReceiveTimestampMs")
    server_complete_timestamp_ms: int = Field(alias="serverCompleteTimestampMs")
    model: ModelInfo
    image: ImageInfo
    detections: list[Detection]
    all_detections: list[Detection] = Field(alias="allDetections")
    postprocess: PostprocessInfo
    timing: Timing


class ErrorDetail(ApiModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(ApiModel):
    api_version: str = Field(alias="apiVersion")
    error: ErrorDetail
    frame_id: str | None = Field(default=None, alias="frameId")
    sequence_number: int | None = Field(default=None, alias="sequenceNumber")
