# API service

Planned FastAPI service exposed to `PPEMobilePlatform` through the approved VPN path.

Responsibilities:

- health and readiness endpoints;
- request authentication and validation;
- frame size and media-type enforcement;
- stable `frameId` propagation;
- model selection from the deployed registry;
- inference-service invocation;
- canonical response and error serialization;
- request and server-stage timing metrics.

The API must not store frame payloads or load model weights directly unless profiling demonstrates that a separate inference process is unnecessary.
