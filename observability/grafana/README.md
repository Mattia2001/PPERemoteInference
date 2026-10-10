# Grafana

The provisioned dashboard **PPE Remote Inference — Selected Service and Global
GPU** is loaded automatically at startup. Its `Inference service` dropdown
selects one of the five model deployments. It displays:

- API availability, request/error rate and server P50/P95/P99;
- decode, preprocess, model, postprocess and queue P95;
- request payload size, active executions, capacity and queue depth;
- host CPU/RAM/network and the selected API container's CPU/RAM/network;
- NVIDIA compute and VRAM utilization, temperature and power for the whole GPU.

Container RAM is not GPU VRAM; DCGM GPU metrics are shared across all resident
CUDA processes. The target-health panel intentionally shows all scrape targets
so an inactive or unreachable model remains visible even when another model is
selected. The dropdown is manual and is not synchronized with the Android app.

Grafana is authenticated, disables anonymous access and binds to loopback by
default. Use an SSH local-forwarding tunnel and browse to
`http://127.0.0.1:3000`; do not expose port 3000 to the phone or public network.

Per-frame experiment comparisons remain a mobile-export/offline-analysis
concern and are never populated from the inference server.
