# Telemetry service

Planned ingestion boundary for experiment and runtime measurements.

Telemetry must remain outside the latency-critical inference response path. Candidate records include:

- request and frame identifiers;
- selected model and processing segment;
- encoded payload size;
- queue, preprocessing, inference and postprocessing time;
- end-to-end latency reported by the mobile client;
- GPU utilization and memory;
- network and experiment metadata.

Raw image data must not be included in ordinary logs or metrics.
