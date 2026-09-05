# Stateless inference API

This directory contains the first executable remote inference service. A single FastAPI process owns request validation and a loaded inference backend; this avoids an unnecessary internal network hop on the current single-GPU server.

Implemented endpoints:

- `GET /health`, `GET /ready`, `GET /v1/ready`;
- `GET /v1/capabilities`, `GET /v1/status`;
- `POST /v1/inference`;
- `GET /metrics` (aggregate Prometheus metrics only).

The default `mock` backend makes contract and deployment tests possible without model weights or a GPU. Set `PPE_BACKEND=ultralytics` and mount a `.pt` or `.engine` model for real inference.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r services/api/requirements-dev.txt
uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port 8080
pytest services/api/tests
```

No frame or detection persistence is implemented by design. See [the API contract](../../docs/api-contract.md) and [ADR 0004](../../docs/decisions/0004-mobile-owned-experiment-log.md).

Operational metrics contain no request identifiers or detection values. They
cover request outcomes, encoded payload size, server and model-stage latency,
queueing, concurrency, warm-up and deployed model identity. The representative
warm-up frame defaults to portrait 1080x1920 so the first mobile request uses
the same Ultralytics input shape; change `PPE_WARMUP_FRAME_WIDTH` and
`PPE_WARMUP_FRAME_HEIGHT` when the acquisition profile changes.
