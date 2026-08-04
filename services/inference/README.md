# Inference service

Planned GPU-backed computer-vision service.

Responsibilities:

- load each configured model once at startup;
- expose model identity, version and readiness;
- decode and preprocess frames;
- execute inference on CUDA with an explicit CPU fallback policy;
- perform postprocessing and non-maximum suppression;
- associate PPE detections with people;
- emit normalized bounding boxes and timing information;
- reject unsupported model requests deterministically.

The first deployment will use the same model as the Android baseline. A stronger remote model will be introduced as a separately versioned experiment.
