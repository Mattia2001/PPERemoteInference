# Prometheus

Prometheus is deployed by `deploy/compose/compose.observability.yaml` and stores
only aggregate operational time series. The default laboratory scrape interval
is two seconds and retention is bounded to seven days or 2 GB, whichever is
reached first.

Scrape targets:

- `inference-api:8080/metrics`: request outcomes, server latency, queue wait and
  depth, concurrency, encoded payload size, warm-up and model stages;
- `node-exporter:9100`: host CPU, RAM, filesystem and network interfaces;
- `cadvisor:8080`: Docker container state, CPU, memory and network traffic;
- `dcgm-exporter:9400`: NVIDIA utilization, framebuffer memory, temperature,
  power and clocks.

Open `http://127.0.0.1:9090/targets` through the documented SSH tunnel to verify
that all five targets are `UP`. Rules in `alerts.yml` flag API/exporter outages,
queue backlog, excessive server latency and high GPU temperature.

Labels never include frame IDs, clients, boxes, confidences or classes derived
from detections. Prometheus is bound to loopback by default and must not be
published to the mobile network.
