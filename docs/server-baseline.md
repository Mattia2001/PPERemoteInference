# Remote server baseline

Captured on 4 August 2026 before development of the remote inference service.

## Hardware

| Resource | Value |
|---|---|
| System | Dell Pro Max Tower T2 FCT2250 |
| CPU | Intel Core Ultra 7 265K, 20 logical CPUs |
| RAM | 30.8 GiB |
| GPU | NVIDIA GeForce RTX 3050 |
| VRAM | 6144 MiB |
| GPU compute capability | 8.6 |
| GPU power limit | 70 W |
| Storage | 1 TB NVMe, approximately 814 GiB free |

## Software

| Component | Value |
|---|---|
| Operating system | Ubuntu 22.04.5 LTS |
| Active kernel | 5.19.0-32-generic |
| Docker Engine | 27.2.0 |
| Docker Compose | 5.0.0 |
| NVIDIA driver | 535.274.02 |
| Driver CUDA capability | 12.2 |
| NVIDIA Container Toolkit | 1.17.7 |
| Python | 3.10.12 system default |

GPU access was validated from `nvidia/cuda:12.2.2-base-ubuntu22.04` using `docker run --gpus all`.

## Existing services

- SSH listens on TCP 22.
- Legacy Vaidio admin portal listens on TCP 8000 outside Docker.
- PostgreSQL 14 listens only on `127.0.0.1:5433`.
- Docker and containerd are enabled and active.
- The host firewall is inactive.
- Kubernetes and Helm are not installed.

## Operational constraints

- Do not use port 8000 for the new API while the Vaidio portal remains active.
- Do not remove legacy containers, images, database volume or native PostgreSQL until retention is agreed.
- Docker, containerd and NVIDIA Container Toolkit packages are held and must not be upgraded casually.
- Kernel or NVIDIA driver changes require a planned maintenance window and recovery access.
- Training remains on Google Colab; this server is the inference deployment target.
