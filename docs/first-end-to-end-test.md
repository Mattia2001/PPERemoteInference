# First end-to-end remote inference test

## Readiness boundary

The repository supports a complete **laptop-controlled** inference round trip:
a real image/video frame is encoded, crosses the VPN/LAN, executes on the
server GPU, and returns detections that are written in sequence to JSONL.

It does not yet support a complete **Android camera-overlay** round trip. USB
VPN sharing can make the server routable from the phone, but it cannot replace
the missing Android HTTP sender, response reordering and overlay integration.

Reverse proxy, TLS, Prometheus/Grafana deployment and Kubernetes are not needed
for this private-network smoke test. They remain necessary before a durable or
broader deployment.

## Server procedure

Clone the implementation branch until it is merged:

```bash
git clone --branch feat/stateless-inference-api-v1 --single-branch \
  https://github.com/Mattia2001/PPERemoteInference.git
cd PPERemoteInference
```

Transfer at least the 640 checkpoint to `models/` using the exact name in the
Compose guide. Verify it before starting the container:

```bash
ls -lh models/yolo26n_sh17_pictor_construction_v2_640_best.pt
sudo docker run --rm --gpus all nvidia/cuda:12.2.2-base-ubuntu22.04 nvidia-smi
cp deploy/compose/yolo26n-640.env.example deploy/compose/yolo26n-640.env
```

For the temporary private VPN/LAN test only, change the untracked environment
file to `PPE_BIND_ADDRESS=192.168.2.126`, then start one model:

```bash
sudo docker compose -p ppe-yolo26n-640 \
  --env-file deploy/compose/yolo26n-640.env \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml up -d --build

curl http://127.0.0.1:8081/v1/status
sudo docker compose -p ppe-yolo26n-640 \
  -f deploy/compose/compose.yaml \
  -f deploy/compose/compose.gpu.yaml logs --tail=100
```

Do not start both models for the first test. One known workload removes
avoidable RTX 3050 VRAM pressure and diagnosis ambiguity.

The Compose network is a normal bridge rather than an `internal` network.
Binding the published port to the explicitly selected host address provides
the restriction for this smoke test; an internal Docker network would suppress
the host-facing publication entirely.

## Laptop procedure

1. Connect the DrayTek VPN.
2. Check routing: `ping 192.168.2.126` (if ICMP is allowed).
3. Check the API: `curl.exe http://192.168.2.126:8081/v1/status`.
4. Run the image smoke test documented in `scripts/README.md`.
5. Only after one successful image, run a short prerecorded video.

Compare `client.roundTripMs`, `response.timing.totalServerMs`, `inferenceMs`
and `client.transportAndApiOverheadMs`. Laptop timestamps are diagnostic, not
a formal one-way delay measurement because clocks are not synchronized.

## Success criteria

- `/v1/status` reports the expected model and `cuda:0`;
- at least one real frame returns HTTP 200 and canonical detections;
- output `sequenceNumber` is monotonic and matches the request;
- JSONL stays client-side and server logs contain no frame/detection data;
- repeated requests do not increase GPU memory without bound;
- failures use the versioned API error envelope.

After this passes, implement the Android client with configurable server URL,
reachability/capability checks, bounded requests, stale-result policy, sequence
restoration and integration with the unified mobile experiment JSONL.
