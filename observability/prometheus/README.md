# Prometheus

The API already exposes `/metrics` with bounded request outcomes, total server latency, queue wait and in-flight requests. The Compose observability milestone will scrape these metrics and add node/container/NVIDIA exporters for host and GPU state.

Labels must never include frame IDs, clients, boxes or classes derived from individual detections. Prometheus remains reachable only inside the deployment network.
