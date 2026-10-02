# Production V1 model baseline — Phase 11A

Audit date: 2026-10-03 (Asia/Kolkata).

| Field | Verified value |
|---|---|
| Model in repository | `ml/models/ewaste.onnx` |
| Repository artifact SHA-256 | `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5` |
| Class mapping | `ml/class_mapping.json`, version `1.0.0` |
| Class order | Battery waste, Keyboard, Light bulb, Mobile phone, Mouse, PCB |
| Production configuration | Render API uses `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`; frontend points to `https://rogith-ewaste-api.onrender.com` |
| Current hosted readiness | `GET /health`: HTTP 200, `status=UP`, `modelStatus=MODEL_READY`, `modelLoadTimeMs=3196` on 2026-10-03 Asia/Kolkata |
| Hosted artifact hash | Not exposed by the health endpoint; cannot independently compare remote bytes to the local digest |
| V1 evaluation baseline | 59/60 = 98.33% on the existing lab held-out set; not a field-accuracy claim |
| V2 status | Not deployed; no V2 model changes in this hosting phase |

No model file, model metadata, class map, or ML serving artifact was modified for Phase 11A. The production API health response confirms that a model is loaded; it does not expose a model version or hash. The documented 59/60 score is the existing laboratory baseline, not a claim about production camera accuracy.
