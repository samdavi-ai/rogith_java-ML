# Model card — E-waste MobileNetV2 classifier

## Intended use

Experimental image classifier for six visually identifiable categories from uploaded photos or camera frames: battery waste, keyboard, light bulb, mobile phone, mouse, and printed circuit board. It returns one of these classes plus confidence. It is a prototype for human-reviewed recycling guidance, not a safety or disposal authority.

## Model and data

- MobileNetV2 ImageNet transfer learning; input 224×224 RGB float32, NCHW, bilinear stretch, pixel normalization `x / 127.5 - 1`.
- Class mapping is authoritative in [classes.json](classes.json); model output is six logits.
- Training/evaluation dataset source, attribution, license, and split limitations: [DATASET_REPORT.md](reports/DATASET_REPORT.md) and [DATASET_SOURCES.md](DATASET_SOURCES.md).
- Held-out test: 60 images, accuracy 0.983, macro F1 0.988; use caution due to small class supports.

## Limitations

- Test images come from the same dataset project as training but were regrouped by filename families and same-class dHash similarity. No physical-object IDs are available, so object-level independence cannot be guaranteed.
- The bulb class has only 3 test images; reported metrics are highly uncertain.
- OOD experiment shows confident forced predictions among excluded waste classes. The classifier cannot identify unknown objects and must not imply otherwise.
- ImageNet initialization and dataset collection conditions may not transfer to diverse real-world settings. Lighting, occlusion, damaged devices, multiple objects, and visually similar materials need broader external testing.
- An unspecified live room frame returned “Light bulb” at 89.4% confidence. Because no target object was deliberately presented, this is not a ground-truth accuracy result.
- Recycling/disposal advice requires region-specific expert validation.

## Artifact

ONNX: `ml/models/ewaste.onnx`; opset 17; input `[N,3,224,224]` float32; output `[N,6]` float32 logits. Keras/ONNX parity: 60/60 validation argmax agreements, max absolute logit difference 5.72e-05 (see `reports/onnx_validation.json`).
