# Telemetry service — deferred

No telemetry-ingestion service is part of the baseline architecture.

`PPEMobilePlatform` owns the ordered per-frame experiment log and exports the unified JSONL containing both local and remote results. The server must not persist:

- frames or encoded payloads;
- `frameId` or `sequenceNumber` event streams;
- bounding boxes or confidences;
- per-frame inference records.

The remote deployment exposes only aggregate operational metrics to Prometheus: request/error counts, latency histograms, in-flight work, queue depth, model identity and host/GPU/network health. A future event store requires a new architecture decision and an explicit retention/privacy policy.
