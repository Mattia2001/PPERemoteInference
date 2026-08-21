# Security notes

The remote inference service processes camera frames from workplace experiments. Security and privacy controls are part of the system design, not optional deployment details.

## Baseline requirements

- Reach the service only through an approved VPN path.
- Terminate TLS at the reverse proxy.
- Authenticate every mobile client request.
- Apply request size, rate and timeout limits.
- Keep databases and monitoring backends off the externally reachable interface.
- Never commit passwords, VPN material, tokens, certificates or private keys.
- Do not persist frames, detections, confidences or bounding boxes on the inference server.
- Record bounded aggregate service metrics; keep per-frame experiment records exclusively on the phone.
- Record model version and request identifier without logging image payloads or inference results.

## Current server constraints

The legacy Vaidio administration portal still occupies TCP port 8000 and PostgreSQL listens locally on port 5433. These services must not be modified until their ownership and retention requirements are confirmed.

The host firewall is currently inactive. Firewall and SSH hardening must be coordinated with Idrotek IT to avoid losing remote access.
