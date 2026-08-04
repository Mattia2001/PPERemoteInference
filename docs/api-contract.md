# Remote inference API contract draft

The contract is versioned under `/v1`. Field names follow the Android domain model where practical. This document is a draft until shared serialization tests exist in both repositories.

## Health

`GET /health`

Confirms that the API process is alive. It must not require the GPU to be ready.

```json
{
  "status": "ok"
}
```

## Readiness

`GET /ready`

Confirms that the selected model is loaded and the inference runtime can accept work.

```json
{
  "status": "ready",
  "device": "cuda:0",
  "modelId": "yolo11n-sh17-baseline",
  "modelVersion": "1"
}
```

## Inference

`POST /v1/inference`

Initial transport: `multipart/form-data`.

| Part | Type | Required | Description |
|---|---|---:|---|
| `frame` | JPEG binary | yes | Encoded source frame |
| `metadata` | JSON | yes | Request identity and inference configuration |

Example metadata:

```json
{
  "frameId": "frame_000001",
  "timestampGeneration": 1782900984463,
  "modelId": "yolo11n-sh17-baseline",
  "selectedPPEs": ["HELMET", "SAFETY_VEST", "GLOVES", "SHOES"]
}
```

Example successful response:

```json
{
  "frameId": "frame_000001",
  "modelId": "yolo11n-sh17-baseline",
  "modelVersion": "1",
  "serverTiming": {
    "queueTimeMs": 0.8,
    "preprocessTimeMs": 2.1,
    "inferenceTimeMs": 8.4,
    "postprocessTimeMs": 1.7,
    "totalServerTimeMs": 13.0
  },
  "detectionResult": {
    "frameWidth": 1920,
    "frameHeight": 1080,
    "persons": [
      {
        "personId": "person_0",
        "globalConfidence": 0.94,
        "personBox": {
          "x": 0.2,
          "y": 0.18,
          "width": 0.55,
          "height": 0.7
        },
        "ppeDetections": [
          {
            "ppeType": "HELMET",
            "confidence": 0.91,
            "boundingBox": {
              "x": 0.35,
              "y": 0.2,
              "width": 0.22,
              "height": 0.14
            }
          }
        ]
      }
    ]
  }
}
```

Bounding-box coordinates are normalized to `[0, 1]`, with `x` and `y` representing the top-left corner. Responses must echo the request `frameId`, including error responses where parsing reached that field.

## Error principles

- Use stable machine-readable error codes.
- Distinguish invalid image, unsupported model, overload and internal failure.
- Reject oversized or unsupported payloads before inference.
- Include no image data in errors or standard logs.
