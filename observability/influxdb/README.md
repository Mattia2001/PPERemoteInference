# InfluxDB — not in the baseline

InfluxDB is deliberately deferred. Per-frame experiment data is returned to and persisted by `PPEMobilePlatform`, which produces the authoritative ordered JSONL.

The first remote deployment uses Prometheus only for aggregate operational monitoring. Introducing any server-side event store requires a separate architecture decision, retention limit, privacy review and evidence that mobile-owned logging is insufficient.
