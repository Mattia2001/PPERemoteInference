# Architecture

## Scope

The system receives individual encoded frames from `PPEMobilePlatform`, performs object detection on the remote GPU and returns detections using the mobile domain model. The request remains identifiable end to end through `frameId`.

## Logical components

### Reverse proxy

Future public entry point for TLS termination, authentication forwarding, request-size limits, timeouts and rate limiting. The development API will initially bind to a non-conflicting private port.

### API service

Owns the mobile-facing HTTP contract, validation, model selection, error mapping and response serialization. It must not reload a model for every request.

### Inference backend

Owns preprocessing, GPU execution, postprocessing, non-maximum suppression and conversion to canonical detections. The initial deployment keeps this boundary inside the API process to avoid an extra network hop; it may become a separate service only if profiling or multi-model scheduling justifies it.

### Mobile experiment recorder

`PPEMobilePlatform` is the sole authoritative recorder of per-frame experiment data. It merges local and remote results by `sequenceNumber` and `frameId`, then exports one ordered JSONL. The server does not persist frames, detections, confidences or per-frame timings.

### Observability stack

Prometheus collects low-cardinality operational metrics and Grafana visualizes them. NVIDIA DCGM Exporter, node exporter and container metrics describe GPU, host and service health. The baseline has no experiment database. None of these services should be reachable directly from the mobile network.

Prometheus labels must never contain `frameId`, client identifiers, bounding boxes or other unbounded values. Request counts, error classes, latency histograms, queue depth and model identity are acceptable bounded dimensions.

## Stateless inference invariant

- Model weights and configuration are loaded at startup and are deployment state, not experiment state.
- A request exists in memory only while it is queued or processed.
- A response contains all server-generated information required by the mobile JSONL.
- Standard logs exclude image bytes, detections, confidences and request metadata.
- Aggregate counters and histograms may outlive a request through Prometheus.
- Failed or late responses are handled by the mobile fallback and ordering policy.

## Deployment stages

### Stage 1: controlled baseline

- Docker Compose on the single server.
- Same CV model and input dimensions on Android and remote GPU.
- JPEG frame transfer with stable identifiers.
- Always-local and always-offload strategies.
- Mobile-owned ordered JSONL and automatic local fallback.

### Stage 2: heterogeneous inference

- Add a stronger remote model.
- Benchmark YOLO26s at 640/960 and YOLO26x at 640 before considering YOLO26x 960.
- Prefer TensorRT FP16, batch 1 and bounded concurrency for the latency path.
- Preserve model identity in every response and experiment record.
- Measure the accuracy/latency/bandwidth trade-off independently from the execution-segment decision.

### Stage 3: adaptive offloading

- Greedy policy baseline.
- Learned policy investigated only after deterministic baselines.
- Context may include network, device, confidence and scene-complexity features.

### Stage 4: shared server orchestration

- Evaluate Kubernetes, NVIDIA device plugin and Helm.
- Introduce namespaces, resource quotas and deployment ownership for future projects.
