# Prometheus

Prometheus is deployed by `deploy/compose/compose.observability.yaml` and stores
only aggregate operational time series. The default laboratory scrape interval
is two seconds and retention is bounded to seven days or 2 GB, whichever is
reached first.

Scrape targets:

- five `inference-api` targets on the `ppe-observability` bridge, labeled by
  `model_service`: request outcomes, server latency, queue wait and depth,
  concurrency, encoded payload size, warm-up and model stages;
- `node-exporter:9100`: host CPU, RAM, filesystem and network interfaces;
- `cadvisor:8080`: Docker container state, CPU, memory and network traffic;
- `dcgm-exporter:9400`: NVIDIA utilization, framebuffer memory, temperature,
  power and clocks.

Open `http://127.0.0.1:9090/targets` through the documented SSH tunnel to verify
that all nine targets are `UP`. The five API instances remain distinct; only
host, container and GPU exporters are shared. Rules in `alerts.yml` flag
per-model API outages, queue backlog and excessive server latency, as well as
exporter outages and global GPU temperature.

Labels never include frame IDs, clients, boxes, confidences or classes derived
from detections. Prometheus is bound to loopback by default and must not be
published to the mobile network.
