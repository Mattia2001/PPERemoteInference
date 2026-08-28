# Operational clients and scripts

## Reference remote-inference client

`remote_inference_client.py` closes the first controlled end-to-end path:

```text
image or prerecorded video -> JPEG encoding -> VPN/LAN -> API v1
-> server GPU inference -> detections -> ordered local JSONL
```

It first calls `/v1/status`, verifies readiness and model identity, then sends
one frame at a time. Sequential operation is intentional for the initial
experiment: output order is deterministic and every response retains the
server timing plus client-side encoding, round-trip and transport/API overhead.
The server does not persist frames or detections.

Install on the Windows laptop:

```powershell
py -m venv .venv-client
.\.venv-client\Scripts\python -m pip install -r scripts\requirements-client.txt
```

Single image smoke test against YOLO26n 640:

```powershell
.\.venv-client\Scripts\python scripts\remote_inference_client.py `
  --server http://192.168.2.126:8081 `
  --model-id yolo26n-ppe-v2-640 `
  --input C:\path\to\frame.jpg `
  --output artifacts\remote-image-smoke.jsonl `
  --fail-fast
```

Prerecorded video test (send one frame every 15 decoded frames):

```powershell
.\.venv-client\Scripts\python scripts\remote_inference_client.py `
  --server http://192.168.2.126:8081 `
  --model-id yolo26n-ppe-v2-640 `
  --input C:\path\to\ppe-video.mp4 `
  --output artifacts\remote-video-smoke.jsonl `
  --every-n-frames 15 `
  --max-frames 100 `
  --fail-fast
```

Use port `8082` and model ID `yolo26n-ppe-v2-960` for the 960 service. If
authentication is enabled, set `PPE_BEARER_TOKEN` or pass `--token`. The JSONL
is an experiment artifact and must stay out of Git.

This validates transport and server computation, but does not draw boxes over
live Android camera frames. That requires the Android offloading client.
