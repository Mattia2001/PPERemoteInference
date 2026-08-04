# Architecture

## Scope

The system receives individual encoded frames from `PPEMobilePlatform`, performs object detection on the remote GPU and returns detections using the mobile domain model. The request remains identifiable end to end through `frameId`.

## Logical components

### Reverse proxy

Future public entry point for TLS termination, authentication forwarding, request-size limits, timeouts and rate limiting. The development API will initially bind to a non-conflicting private port.

### API service

Owns the mobile-facing HTTP contract, validation, model selection, error mapping and response serialization. It must not reload a model for every request.

### Inference service

Owns preprocessing, GPU execution, postprocessing, non-maximum suppression and conversion to canonical detections. It exposes model health and model metadata to the API service.

### Telemetry service

Persists experiment measurements outside the inference response path. Telemetry failures must not invalidate an otherwise successful detection response.

### Observability stack

Prometheus collects operational metrics, Grafana visualizes them and InfluxDB stores experiment time series where appropriate. None of these services should be reachable directly from the mobile network.

## Deployment stages

### Stage 1: controlled baseline

- Docker Compose on the single server.
- Same CV model and input dimensions on Android and remote GPU.
- JPEG frame transfer with stable identifiers.
- Always-local and always-offload strategies.

### Stage 2: heterogeneous inference

- Add a stronger remote model.
- Preserve model identity in every response and experiment record.
- Measure the accuracy/latency/bandwidth trade-off independently from the execution-segment decision.

### Stage 3: adaptive offloading

- Greedy policy baseline.
- Learned policy investigated only after deterministic baselines.
- Context may include network, device, confidence and scene-complexity features.

### Stage 4: shared server orchestration

- Evaluate Kubernetes, NVIDIA device plugin and Helm.
- Introduce namespaces, resource quotas and deployment ownership for future projects.
