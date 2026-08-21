# Model registry

Model binaries are not committed to Git. Each deployable model will have a small versioned manifest containing:

- stable model identifier and version;
- source benchmark run;
- artifact filename and SHA-256 hash;
- architecture and input dimensions;
- canonical class mapping;
- confidence and NMS thresholds;
- runtime and precision;
- expected preprocessing contract;
- validation metrics and dataset references.

Weights will be supplied to the deployment through an external artifact location or a protected server volume.

The first two expected deployment filenames are:

```text
yolo26n_sh17_pictor_construction_v2_640_best.pt
yolo26n_sh17_pictor_construction_v2_960_best.pt
```

They are intentionally ignored by Git and must be transferred to this directory after cloning. Record and verify their SHA-256 hashes before treating a deployment as reproducible.
