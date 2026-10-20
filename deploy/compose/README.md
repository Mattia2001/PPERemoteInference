# Docker Compose deployment

The baseline starts the stateless API on host port `8080`, avoiding the legacy Vaidio portal on `8000`.

Contract-only smoke deployment:

```bash
docker compose -f deploy/compose/compose.yaml up --build
curl http://127.0.0.1:8080/health
```

Real GPU inference:

1. place a deployment checkpoint under `models/` (weights are ignored by Git);
2. copy one of the versioned `*.env.example` model configurations to an untracked `.env` file;
3. verify NVIDIA Container Toolkit with a CUDA `nvidia-smi` container;
4. start with both Compose files:

```bash
docker compose --env-file .env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml up --build
```

The API has no data volume. The model mount is read-only. The Compose bridge
must not be marked `internal`: an internally isolated Docker network prevents
the host publication required by the controlled VPN/LAN smoke test. Exposure
remains restricted by `PPE_BIND_ADDRESS`, whose safe default is loopback.
HTTPS and authentication are mandatory before phone traffic is admitted; they
belong to the following reverse-proxy milestone.

## Deploying the existing YOLO26n 640 and 960 models

The server needs the original PyTorch `best.pt` checkpoints, not the Android TFLite exports. Download these two Drive artifacts and rename/copy them on the server as:

```text
models/yolo26n_sh17_pictor_construction_v2_640_best.pt
models/yolo26n_sh17_pictor_construction_v2_960_best.pt
```

Expected Drive experiment directories:

```text
PPEBenchmark/experiments/sh17_pictor_construction_v2_yolo26n_v1_fastio/weights/best.pt
PPEBenchmark/experiments/sh17_pictor_construction_v2_yolo26n_960_v1_fastio/weights/best.pt
```

Create two untracked environment files:

```bash
cp deploy/compose/yolo26n-640.env.example deploy/compose/yolo26n-640.env
cp deploy/compose/yolo26n-960.env.example deploy/compose/yolo26n-960.env
```

Start two independent projects sharing the same built image:

```bash
docker compose -p ppe-yolo26n-640 \
  --env-file deploy/compose/yolo26n-640.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml up -d --build

docker compose -p ppe-yolo26n-960 \
  --env-file deploy/compose/yolo26n-960.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml up -d
```

They bind to loopback ports `8081` and `8082`. This is the safe default for the upcoming reverse proxy. For a short VPN/LAN-only test before the proxy exists, set `PPE_BIND_ADDRESS=192.168.2.126` in both untracked environment files and allow only the approved private network path. Do not use `0.0.0.0` on an untrusted interface.

Verify:

```bash
curl http://127.0.0.1:8081/v1/status
curl http://127.0.0.1:8082/v1/status
docker compose -p ppe-yolo26n-640 -f deploy/compose/compose.yaml logs --tail=100
```

The Android model selector discovers each saved `host:port` endpoint through
`/v1/status` and requires the ready model's `modelSha256`. Rebuild the API
container after pulling this change; older containers lack that field and are
not selectable in the new app. A model at another port can be added in the
phone's Settings without changing the API contract. Deploy larger models one
at a time initially; check RTX 3050 memory and latency before co-residency.

## Live observability deployment

The observability overlay adds Prometheus, Grafana, node-exporter, cAdvisor and
NVIDIA DCGM Exporter to the same Compose project. It persists bounded aggregate
time series in named Docker volumes, never frames, frame IDs, detections,
confidences or bounding boxes.

From the repository root on the server, create the untracked configuration once:

```bash
cp deploy/compose/observability.env.example deploy/compose/observability.env
nano deploy/compose/observability.env
```

Replace `PPE_GRAFANA_ADMIN_PASSWORD` with a long unique password. Keep
`PPE_OBSERVABILITY_BIND_ADDRESS=127.0.0.1`; the dashboards are a management
surface and must not be exposed to the phone, LAN or public Internet.

Update the existing YOLO26n 640 deployment and start telemetry:

```bash
docker compose -p ppe-yolo26n-640 \
  --env-file deploy/compose/yolo26n-640.env \
  --env-file deploy/compose/observability.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml \
  -f deploy/compose/compose.observability.yaml \
  up -d --build
```

Check container state and scrape targets on the server:

```bash
docker compose -p ppe-yolo26n-640 \
  --env-file deploy/compose/yolo26n-640.env \
  --env-file deploy/compose/observability.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml \
  -f deploy/compose/compose.observability.yaml \
  ps

curl -fsS http://127.0.0.1:9090/-/ready
curl -fsS http://127.0.0.1:9090/api/v1/targets
curl -fsS http://127.0.0.1:3000/api/health
curl -fsS http://127.0.0.1:8081/metrics | grep '^ppe_'
```

The observability project now creates a shared Docker bridge named
`ppe-observability`. Attach the other five running inference projects to it,
without changing their published API ports or model configuration. For each
pair below, run the command from the repository root, substituting the project
and environment-file stem:

| Compose project | Environment-file stem |
| --- | --- |
| `ppe-yolo26n-960` | `yolo26n-960` |
| `ppe-yolo26s-640` | `yolo26s-640` |
| `ppe-yolo26m-640` | `yolo26m-640` |
| `ppe-yolo26l-640` | `yolo26l-640` |
| `ppe-yolo26x-640` | `yolo26x-640` |

```bash
docker compose -p ppe-yolo26s-640 \
  --env-file deploy/compose/yolo26s-640.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml \
  -f deploy/compose/compose.monitoring-client.yaml \
  up -d --no-deps inference-api
```

Run this only after the YOLO26n-640 observability project is up. Include the
monitoring-client overlay in subsequent updates of each model project;
otherwise Compose may disconnect its API from the shared bridge. All APIs
remain on their private Compose networks too. The shared bridge exposes
container-internal `/metrics` to Prometheus, not another host port.

Prometheus now has six `inference-api` targets, each with a stable
`model_service` label, plus node-exporter, cAdvisor, DCGM and Prometheus.
Verify that **all ten targets** are `UP` after the API containers are healthy.
During rollout, unattached model targets will temporarily show `DOWN`.
The RTX 3050 supports DCGM field watches, although some datacenter-only
counters may be absent.

From Windows, while the VPN is active, open an SSH tunnel and leave it running:

```powershell
ssh -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 superuser@192.168.2.126
```

Then open:

- Grafana: `http://127.0.0.1:3000`;
- Prometheus targets: `http://127.0.0.1:9090/targets`.

Grafana provisions the Prometheus datasource and the **PPE Remote Inference —
Selected Service and Global GPU** dashboard automatically. Choose the
`Inference service` dropdown to match the model/port selected on the phone,
then use a short range such as “Last 15 minutes”. API latency, queue, requests
and API-container CPU/RAM/network are filtered to that service. Target health
shows all services. Host CPU/network and DCGM GPU utilization, VRAM,
temperature and power are **global to the server**, not attributable to the
selected model. The cAdvisor memory panel is container RAM, not GPU VRAM.
Five idle CUDA processes can occupy VRAM even while GPU utilization is zero;
for clean model-specific latency measurements, ensure no other client sends
work to the other resident APIs and record co-residency in the test metadata.

If one exporter fails, inspect only its logs without stopping inference:

```bash
docker compose -p ppe-yolo26n-640 \
  --env-file deploy/compose/yolo26n-640.env \
  --env-file deploy/compose/observability.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml \
  -f deploy/compose/compose.observability.yaml \
  logs --tail=200 dcgm-exporter cadvisor prometheus grafana
```

Stopping the stack does not delete time series. Do not add `-v` unless deletion
of the Prometheus and Grafana named volumes is explicitly intended.
