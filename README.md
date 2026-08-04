# PPE Remote Inference

Remote GPU inference segment for the thesis **Adaptive Task Offloading for Mobile PPE Detection over 5G Networks**.

The repository will host the services deployed on the on-premise GPU server used by `PPEMobilePlatform`. The server is remote from the mobile network and must not be described as a real operator MEC node. It provides an edge-like experimental target reachable through the Idrotek private network and VPN.

## Current status

This repository currently contains the agreed architecture, service boundaries, API contract draft and deployment documentation. Executable services will be added after the mobile CV model artifacts and the first remote inference contract are consolidated.

The server preflight has confirmed:

- Ubuntu 22.04.5 LTS on x86-64;
- Intel Core Ultra 7 265K and 30.8 GiB RAM;
- NVIDIA GeForce RTX 3050 with 6 GiB VRAM;
- Docker, Compose and NVIDIA Container Toolkit operational;
- successful CUDA 12.2 container access to the GPU;
- approximately 814 GiB of free NVMe storage.

See [docs/server-baseline.md](docs/server-baseline.md) for the complete deployment baseline.

## Repository layout

```text
PPERemoteInference/
├── services/
│   ├── api/                 # Mobile-facing HTTP API
│   ├── inference/           # GPU model loading and inference
│   └── telemetry/           # Experiment telemetry ingestion
├── observability/
│   ├── prometheus/          # Operational metrics
│   ├── grafana/             # Dashboards
│   └── influxdb/            # Time-series experiment data
├── deploy/
│   ├── compose/             # Initial single-server deployment
│   ├── kubernetes/          # Planned multi-workload deployment
│   └── helm/                # Planned Kubernetes packaging
├── models/                  # Model registry documentation, no weights
├── docs/
│   └── decisions/           # Architecture decision records
├── scripts/                 # Future operational utilities
└── tests/                   # Future integration and performance tests
```

## Planned request flow

1. The mobile application assigns a stable `frameId` and decides to offload.
2. The encoded frame and request metadata are sent through the VPN.
3. The API validates the request and forwards it to the inference service.
4. The selected model executes on the GPU.
5. The API returns normalized person and PPE detections associated with the same `frameId`.
6. Telemetry is recorded separately from the critical response path.

Only frames and metadata are transferred. Application code, containers and neural-network partitions are out of scope.

## Related repositories

- [`Mattia2001/PPEMobilePlatform`](https://github.com/Mattia2001/PPEMobilePlatform): Android acquisition, local inference and offloading client.
- [`Mattia2001/PPEBenchmark`](https://github.com/Mattia2001/PPEBenchmark): dataset preparation, model training, evaluation and export.

## Initial delivery plan

1. Implement health and readiness probes.
2. Define and test the versioned inference API.
3. Load the same baseline model used on Android for a controlled local/offload comparison.
4. Package API and inference in Docker Compose.
5. Benchmark latency, throughput and GPU memory.
6. Add Prometheus, Grafana and InfluxDB.
7. Introduce a stronger remote model as a separate experiment.
8. Evaluate Kubernetes and Helm when the server must host multiple projects.

## Data and model policy

Model binaries, datasets, captured frames and experiment artifacts are intentionally excluded from Git. Their provenance, hashes and deployment metadata will be recorded in versioned manifests.
