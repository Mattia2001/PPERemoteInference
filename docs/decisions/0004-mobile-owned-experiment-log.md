# ADR 0004: Mobile-owned experiment log

## Status

Accepted — 2026-08-20.

## Context

Local and remote inference results must form one temporally ordered experiment trace. Persisting a second per-frame event stream on the server would create two competing sources of truth, require reconciliation and add privacy, retention and operational complexity.

## Decision

`PPEMobilePlatform` is the authoritative owner of the experiment trace. Every remote request carries `frameId`, `sequenceNumber` and capture time; every response echoes them. The phone merges results by capture order and exports one JSONL.

The remote service is stateless with respect to experiment events. It does not persist frames, detections, confidences or per-frame timings. Prometheus retains only aggregate, low-cardinality operational metrics.

## Consequences

- Late and out-of-order remote responses are resolved on the phone.
- Loss of a response is visible as an explicit timeout/fallback event in the mobile trace.
- Grafana describes service and hardware health, not experiment ground truth.
- `frameId` and other unbounded identifiers are forbidden as Prometheus labels.
- Any future server-side experiment store requires a new ADR.
