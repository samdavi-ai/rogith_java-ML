# Model card — E-waste MobileNetV2 classifier

## Intended use

Experimental image classifier for six visually identifiable categories from uploaded photos or camera frames: battery waste, keyboard, light bulb, mobile phone, mouse, and printed circuit board. It returns a supported category only above the configured minimum confidence, otherwise `UNSURE`. It is a prototype for human-reviewed recycling guidance, not a safety or disposal authority.

## Model and data

- Version 1.0.0; evaluated and documented 2026-10-02.
- MobileNetV2 ImageNet transfer learning; input 224×224 RGB float32, NCHW, bilinear stretch, pixel normalization `x / 127.5 - 1`.
- Class mapping is authoritative in [class_mapping.json](class_mapping.json); model output is six logits.
- Parameters: 2,265,670. Version: 1.0.0. Training used seed 42, batch size 16, up to 12 frozen-backbone and 8 fine-tuning epochs, Adam at 0.001 then 0.00001, early stopping by validation loss.
- Minimum confidence: 0.66, calibrated from the 60-image validation set (minimum correctly classified confidence 0.6515, rounded upward to 0.66). This is a small-sample operating threshold, not a calibrated probability guarantee. Below it the API returns `UNSURE` and withholds category-specific guidance.
- Training/evaluation dataset source, attribution, license, and split limitations: [dataset report](reports/dataset_report.md) and [DATASET_SOURCES.md](DATASET_SOURCES.md).
- Held-out test: 60 images, accuracy 0.983, macro F1 0.988; weighted precision 0.985, weighted recall 0.983, weighted F1 0.983. Use caution due to small class supports.

## Limitations

- Test images come from the same dataset project as training but were regrouped by filename families and same-class dHash similarity. No physical-object IDs are available, so object-level independence cannot be guaranteed.
- The bulb class has only 3 test images; reported metrics are highly uncertain.
- OOD experiment shows confident forced predictions among excluded waste classes. The classifier cannot identify unknown objects and must not imply otherwise.
- User screenshot challenge crops (evaluation-only) show production-model errors: bottle→Mouse, laptop/keyboard scene→Keyboard, and adapter→Light bulb. Exact original camera frames were unavailable; local screenshot-crop replays and candidate comparison are documented in [the model improvement report](../docs/MODEL_IMPROVEMENT_REPORT.md).
- An experimental seven-class candidate added `not_ewaste` from four general-waste source labels. It improved rejection on its mixed test set but reduced accuracy on the same six-class e-waste test subset from 59/60 to 52/60 and mislabeled the adapter as not e-waste. It was rejected and is not part of this model card's deployable artifact.
- Candidate ONNX parity was verified in Python, but candidate Java integration was not performed. Production remains model v1.0.0.
- ImageNet initialization and dataset collection conditions may not transfer to diverse real-world settings. Lighting, occlusion, damaged devices, multiple objects, and visually similar materials need broader external testing.
- An unspecified live room frame returned “Light bulb” at 89.4% confidence. Because no target object was deliberately presented, this is not a ground-truth accuracy result.
- Recycling/disposal advice requires region-specific expert validation.

## Artifact

ONNX: `ml/models/ewaste.onnx`; opset 17; input `[N,3,224,224]` float32; output `[N,6]` float32 logits. Keras/ONNX parity: 60/60 validation argmax agreements, max absolute logit difference 5.72e-05 (see `reports/onnx_validation.json`).
