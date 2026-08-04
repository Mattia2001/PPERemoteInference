# Docker Compose deployment

The first executable deployment will be defined here. It will use explicit image versions, health checks, private networks, persistent volumes and bounded CPU/memory resources.

The development API must avoid TCP port 8000 because it is occupied by the legacy Vaidio administration portal. The proposed temporary API port is 8080; the final client entry point will use HTTPS through a reverse proxy.
