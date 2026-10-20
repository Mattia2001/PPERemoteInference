# Remote inference API contract v1

The first stable HTTP contract is versioned under `/v1`. JSON field names use `camelCase`; coordinates are returned both normalized and in source-image pixels. The service is stateless: the response is returned to the phone and is not persisted server-side.

## Ordering and ownership

Every request carries three independent identifiers:

- `frameId`: unique opaque frame identifier;
- `sequenceNumber`: monotonically increasing experiment sequence used by the phone to restore order;
- `captureTimestampMs`: phone capture timestamp (Unix epoch milliseconds).

The server echoes all three fields. Server completion order is not guaranteed. The Android client is the sole owner of the ordered experiment JSONL.

## Liveness and readiness

`GET /health` checks only the API process. `GET /v1/ready` checks that the configured inference backend and model are ready. `/ready` is retained as a convenience alias.

## Capabilities and status

`GET /v1/capabilities` returns API version, model identity, canonical classes, input size, runtime and device. `GET /v1/status` additionally returns bounded operational state such as queue capacity and a best-effort GPU snapshot. These responses are intended for the mobile dashboard and offloading eligibility checks.

For an Ultralytics backend, every model object in readiness, capabilities,
status and successful inference now includes `modelSha256`: the SHA-256 of the
checkpoint file loaded at startup. The mock backend reports `null`. This
additive v1 field allows the mobile client to reject responses from a changed
checkpoint. An existing container must be rebuilt to expose it; the filename
and mutable `modelVersion` label alone are insufficient artifact evidence.
Each service instance exposes one model. Multiple models require separately
configured endpoints and GPU-memory validation.

The status payload also reports the startup warm-up result. With the default
`PPE_WARMUP_RUNS=1`, one synthetic portrait inference completes before readiness.
`PPE_WARMUP_FRAME_WIDTH` and `PPE_WARMUP_FRAME_HEIGHT` should match the mobile
acquisition profile so the first user frame does not pay a new Ultralytics input
shape initialization cost.

## Inference

`POST /v1/inference` uses `multipart/form-data`.

| Part | Type | Required | Description |
|---|---|---:|---|
| `frame` | JPEG or PNG binary | yes | Encoded source frame |
| `metadata` | JSON string | yes | Request identity and inference configuration |

Example metadata:

```json
{
  "apiVersion": "1.0",
  "frameId": "frame_000001",
  "sequenceNumber": 1,
  "captureTimestampMs": 1782900984463,
  "modelId": "yolo26n-ppe-v2-960",
  "selectedClasses": ["person", "helmet", "safety_vest", "gloves", "safety_boots"]
}
```

Successful response (abridged):

```json
{
  "apiVersion": "1.0",
  "frameId": "frame_000001",
  "sequenceNumber": 1,
  "captureTimestampMs": 1782900984463,
  "serverReceiveTimestampMs": 1782900984510,
  "serverCompleteTimestampMs": 1782900984524,
  "model": {
    "modelId": "yolo26n-ppe-v2-960",
    "modelVersion": "1",
    "modelSha256": "<64-character SHA-256 of deployed best.pt>",
    "runtime": "ultralytics",
    "device": "cuda:0",
    "inputSize": 960
  },
  "image": {"width": 1920, "height": 1080},
  "detections": [
    {
      "detectionId": "det_0",
      "classId": 1,
      "className": "helmet",
      "confidence": 0.91,
      "boxNormalized": {"x": 0.35, "y": 0.20, "width": 0.22, "height": 0.14},
      "boxPixels": {"x": 672, "y": 216, "width": 422, "height": 151},
      "associatedPersonId": "det_person_0"
    }
  ],
  "allDetections": ["the same detection objects before selectedClasses filtering"],
  "postprocess": {
    "confidenceThreshold": 0.25,
    "iouThreshold": 0.45,
    "maxDetections": 300,
    "outputLimitReached": false
  },
  "timing": {
    "queueMs": 0.8,
    "decodeMs": 2.1,
    "preprocessMs": 0.4,
    "inferenceMs": 8.4,
    "postprocessMs": 1.7,
    "totalServerMs": 13.4
  }
}
```

`selectedClasses` filters only `detections`, not `allDetections`; it is not a
request for a different model. An empty or omitted list means all canonical
classes. `allDetections` and `postprocess` are additive v1 fields for the mobile
schema-10 quality-state export. They are required for a *complete* quality
observation, so a phone talking to an older server must explicitly mark that
observation unavailable. A response at `maxDetections` is marked capped; the
server cannot report the pre-cap count from the Ultralytics predictor.

## Errors

Errors use a stable envelope and HTTP status:

```json
{
  "apiVersion": "1.0",
  "error": {
    "code": "MODEL_MISMATCH",
    "message": "Requested model is not deployed",
    "retryable": false
  },
  "frameId": "frame_000001",
  "sequenceNumber": 1
}
```

Initial codes include `INVALID_METADATA`, `INVALID_IMAGE`, `PAYLOAD_TOO_LARGE`, `UNSUPPORTED_MEDIA_TYPE`, `MODEL_MISMATCH`, `NOT_READY`, `OVERLOADED` and `INTERNAL_ERROR`.

## Privacy and observability invariant

- Frame bytes and detections are held only for the request lifetime.
- Standard logs must not contain images, bounding boxes or confidences.
- Prometheus exposes aggregate counters and latency histograms only, with bounded labels.
- A future streaming/WebSocket transport must preserve the same identity, ordering and error semantics.
