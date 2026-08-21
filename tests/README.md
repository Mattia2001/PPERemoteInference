# Tests

The executable API contract tests currently live in `services/api/tests` and run against the stateless mock backend:

```bash
pytest services/api/tests
```

They verify liveness/readiness, identity echo, image dimensions and stable failures. Future suites should add real-model golden images, overload behavior, Android/server serialization compatibility and end-to-end latency on the remote host.
