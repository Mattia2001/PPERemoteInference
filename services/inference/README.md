# Inference backend

The first backend is implemented in-process in `services/api/app/backend.py`. On the current single-GPU host, a separate inference microservice would add serialization and network overhead without providing isolation that is yet justified by measurements.

The backend contract is intentionally small: load one deployment model at startup and return canonical detections plus stage timing. `mock` and `ultralytics` implementations exist. TensorRT can be introduced behind the same interface after exporting and validating an engine on the RTX 3050.

Split this into a separate service only if profiling or multi-model scheduling demonstrates a concrete need.
