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

The API has no data volume. The model mount is read-only. HTTPS and authentication are mandatory before phone traffic is admitted; they belong to the following reverse-proxy milestone.

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
