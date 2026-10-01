# Training and evaluation report

Run date: 2026-10-02 (local project date). Framework: TensorFlow 2.17.0 / Keras 3.15.1. Python: 3.11.15. Device: CPU on macOS-26.6.2-arm64-arm-64bit.

## Training setup

- Architecture: ImageNet MobileNetV2 feature extractor, GlobalAveragePooling2D, Dropout(0.25), Dense logits head; last 20 backbone layers fine-tuned with BatchNorm frozen.
- Initialization: MobileNetV2 ImageNet weights (Keras official weights).
- Seed: 42; batch size: 16; training time: 67.5s.
- Frozen phase: up to 12 epochs at 0.001; fine-tune phase: up to 8 epochs at 1e-05; early stopping and best checkpoint selected by validation loss (patience 3).
- Train images: 523; validation: 60; test: 60.
- Selected validation checkpoint: loss 0.018006, accuracy 1.0000.

## Untouched held-out test

| Metric | Value |
|---|---:|
| Accuracy | 0.9833 |
| Macro precision | 0.9872 |
| Macro recall | 0.9889 |
| Macro F1 | 0.9876 |
| Weighted precision | 0.9846 |
| Weighted recall | 0.9833 |
| Weighted F1 | 0.9834 |

Per-class precision/recall/F1 (support):

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| battery_waste | 1.000 | 0.933 | 0.966 | 15 |
| keyboard | 1.000 | 1.000 | 1.000 | 8 |
| light_bulb | 1.000 | 1.000 | 1.000 | 3 |
| mobile_phone | 0.923 | 1.000 | 0.960 | 12 |
| mouse | 1.000 | 1.000 | 1.000 | 6 |
| pcb | 1.000 | 1.000 | 1.000 | 16 |

Confusion matrix (rows=true, columns=predicted; class order in header):

| True \ Predicted | battery_waste | keyboard | light_bulb | mobile_phone | mouse | pcb |
|---|---|---|---|---|---|---|
| battery_waste | 14 | 0 | 0 | 1 | 0 | 0 |
| keyboard | 0 | 8 | 0 | 0 | 0 | 0 |
| light_bulb | 0 | 0 | 3 | 0 | 0 | 0 |
| mobile_phone | 0 | 0 | 0 | 12 | 0 | 0 |
| mouse | 0 | 0 | 0 | 0 | 6 | 0 |
| pcb | 0 | 0 | 0 | 0 | 0 | 16 |

One error: battery_waste → mobile_phone, predicted confidence 0.5203. Small test supports, especially 3 light_bulb images, make per-class estimates imprecise.

## Confidence policy

The API minimum confidence is 0.66. On the 60 validation images, the selected checkpoint classified all 60 correctly and the minimum top-class confidence was 0.651542. The threshold was rounded upward to 0.66 using validation only. The held-out test error had 0.5203 Keras confidence (Java/ONNX preprocessing yielded about 0.5655 in the previous direct inference check), so the API reports `UNSURE` and suppresses category-specific guidance for that example. With only 60 validation images, this is an initial operating threshold, not a statistical calibration guarantee.

## Excluded-class images / unknown behavior

The model forced a supported-class prediction on 205 held-aside images from six excluded waste classes within the same dataset project. Mean maximum confidence was 0.7837; 92 predictions had confidence ≥0.85. This is not the requested external set of household objects such as bottles, books, shoes, food, chairs, people, and vehicles. The closed-set classifier is not an unknown detector; evaluation on an independently sourced non-e-waste set remains outstanding. Full counts are in evaluation.json.

## Runtime observations

The running Spring service reported 1,063 ms to load and validate the ONNX model and class map. A 30-request sequential HTTP sample using a real held-out mobile-phone image measured 11.31 ms median and 13.87 ms p95 (15.46 ms max; local machine, includes multipart upload and HTTP handling). The browser interval is 1,000 ms and one request may be in flight, giving a nominal cadence near one frame per second; camera capture/encoding was not separately instrumented. These local measurements do not predict Render performance. Process memory and a Docker-contained runtime were not measured.
