# Grafana

The provisioned dashboard **PPE Remote Inference — Live Operations** is loaded
automatically at startup. It displays:

- API availability, request/error rate and server P50/P95/P99;
- decode, preprocess, model, postprocess and queue P95;
- request payload size, active executions, capacity and queue depth;
- host and per-container CPU, RAM and RX/TX traffic;
- NVIDIA compute and VRAM utilization, temperature and power.

Grafana is authenticated, disables anonymous access and binds to loopback by
default. Use an SSH local-forwarding tunnel and browse to
`http://127.0.0.1:3000`; do not expose port 3000 to the phone or public network.

Per-frame experiment comparisons remain a mobile-export/offline-analysis
concern and are never populated from the inference server.
