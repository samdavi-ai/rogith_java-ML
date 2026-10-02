# MobileNetV2 training and serving

The real dataset source and license rationale are in `DATASET_SOURCES.md`. The dataset archive and generated classification trees remain local and are excluded from Git. `class_mapping.json` is the authoritative six-class, zero-based mapping shared by Python and Java. The latest dataset/model audit, including a rejected negative-class experiment, is documented in `../docs/ML_AUDIT.md` and `../docs/MODEL_IMPROVEMENT_REPORT.md`.

## Rebuild the dataset

```bash
python3.11 -m venv ml/.venv
ml/.venv/bin/pip install -r ml/requirements.txt
ml/.venv/bin/python ml/scripts/prepare_dataset.py --data-root ml/data/raw/roboflow_v5
```

The preparation script audits labels, corrupt images, exact duplicates, source filename families and dHash near-duplicate candidates. It groups selected-class near-duplicate families before deterministic train/validation/test assignment and keeps train-only variants in the training split. See `reports/dataset_report.md` for the source class inventory, observed split, and known provenance limitations.

Use `ml/.venv/bin/python ml/scripts/validate_dataset.py --data-root ml/data/raw/roboflow_v5` for a non-mutating audit. It checks readability, source-label presence, exact hashes, source-family split leakage, and records cross-split dHash candidates.

## Train, evaluate and export

```bash
ml/.venv/bin/python ml/training/train.py --data ml/data/processed/classification --out ml/models
ml/.venv/bin/python ml/scripts/export_onnx.py --model ml/models/best_model.keras --out ml/models/ewaste.onnx
ml/.venv/bin/python ml/scripts/evaluate.py --model ml/models/best_model.keras --out ml/reports/evaluation.json
ml/.venv/bin/python ml/scripts/validate_onnx.py
```

Checkpoint selection uses validation loss. The test script refuses to overwrite a previous report and evaluates the held-out test and excluded-class OOD trees once. These scripts do not create fabricated results.

The committed production artifact is `models/ewaste.onnx`. The larger intermediate Keras checkpoint and raw images are ignored. `reports/onnx_validation.json`, `reports/evaluation.json`, `reports/dataset_report.md`, and `reports/TRAINING_REPORT.md` record the baseline run. The default confidence floor is 0.66, selected using validation only; the small validation set makes this an initial threshold, not a probability calibration guarantee. Candidate-v2 files are experimental, locally ignored, and were not promoted because e-waste test recall regressed.

## Inference contract

- Input: RGB float32 NCHW `[1,3,224,224]`
- Resize: bilinear stretch to 224×224
- Normalize: `pixel / 127.5 - 1`
- Output: six logits in `class_mapping.json` order
- Export: ONNX opset 17, CPUExecutionProvider validation

Java keeps one `OrtSession` for application lifetime and reads display names from the same `ml/class_mapping.json`. `/health` returns `MODEL_READY`, `MODEL_UNAVAILABLE`, or `MODEL_LOAD_ERROR` without disclosing model paths. Low-confidence results return `UNSURE` and no class name; the UI suppresses class-specific advice for these predictions. The API does not substitute mock predictions.
