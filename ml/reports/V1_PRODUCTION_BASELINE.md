# Frozen V1 production baseline — Phase 11

Audit date: 2026-10-02. Reference commit: `a7bb435821e6496adf7a22304b52c5630f427c53`.

## Artifact identity

| Field | Verified value |
|---|---|
| Active local ONNX path | `ml/models/ewaste.onnx` |
| Archived production ONNX path | `ml/models/archive/recolens-v1-production.onnx` |
| Active / archive SHA-256 | `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5` (both match) |
| Local Keras checkpoint | `ml/models/best_model.keras` |
| Class map | `ml/class_mapping.json`, version `1.0.0`, 6 contiguous IDs |
| Classes in output order | Battery waste, Keyboard, Light bulb, Mobile phone, Mouse, Printed circuit board |
| Input | float32 RGB, NCHW `[N,3,224,224]`; bilinear stretch; no crop/pad; `pixel / 127.5 - 1.0`; ImageIO stored orientation (no EXIF auto-rotation) |
| ONNX producer | `tf2onnx 1.16.1 15c810` |
| ONNX IR / opsets | IR 8; ONNX opset 17; `ai.onnx.ml` opset 2 |
| ONNX input/output | `image`: dynamic N, `[N,3,224,224]`, float32; `logits`: dynamic N, `[N,6]`, float32 |
| ONNX embedded metadata | None; class and preprocessing metadata are external in `ml/models/model_metadata.json` and `ml/class_mapping.json` |

The production ONNX artifact was not changed in Phase 11. The matching local/archive hash does not reveal the hash currently loaded by the hosted service.

## Reproducibility check

Command executed against the existing V1 held-out tree:

```bash
ml/.venv/bin/python ml/scripts/evaluate.py \
  --data ml/data/processed/classification \
  --ood-data ml/data/processed/ood_test \
  --classes ml/class_mapping.json \
  --model ml/models/best_model.keras \
  --out /tmp/phase11_v1_evaluation.json
```

It reproduces **59/60 = 98.33%** accuracy. Macro precision is 98.72%, macro recall 98.89%, macro F1 98.76%; weighted precision 98.46%, weighted recall 98.33%, weighted F1 98.34%. The sole error is a battery-waste image predicted as mobile phone at confidence 0.57193.

ONNX comparison on the same 60 test images passed: argmax 60/60, maximum absolute logit difference `6.48499e-5`, maximum probability difference `7.24196e-6`. ONNX Runtime single-image timing in this run: median 6.65 ms, p95 7.58 ms, max 9.76 ms (model-only, local CPU). These values do not provide real-world camera performance.

## Production disposition

V1 remains the frozen regression reference. Do not overwrite either ONNX artifact or its class map during data collection. The Phase 11 real-world baseline is pending until actual camera images are collected; the 59/60 laboratory value must not be described as camera-set performance.
