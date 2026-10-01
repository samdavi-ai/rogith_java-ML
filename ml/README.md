# MobileNetV2 training and serving

The real dataset source and license rationale are in `DATASET_SOURCES.md`. The dataset archive and generated classification trees remain local and are excluded from Git. `classes.json` is the authoritative six-class, zero-based mapping shared by Python and Java.

## Rebuild the dataset

```bash
python3.11 -m venv ml/.venv
ml/.venv/bin/pip install -r ml/requirements.txt
ml/.venv/bin/python ml/scripts/prepare_dataset.py --data-root ml/data/raw/roboflow_v5
```

The preparation script audits labels, corrupt images, exact duplicates, source filename families and dHash near-duplicate candidates. It groups selected-class near-duplicate families before deterministic train/validation/test assignment and keeps train-only variants in the training split. See `reports/DATASET_REPORT.md` for the observed split and known provenance limitations.

## Train, evaluate and export

```bash
ml/.venv/bin/python ml/training/train.py --data ml/data/processed/classification --out ml/models
ml/.venv/bin/python ml/scripts/export_onnx.py --model ml/models/best_model.keras --out ml/models/ewaste.onnx
ml/.venv/bin/python ml/scripts/evaluate.py --model ml/models/best_model.keras --out ml/reports/evaluation.json
```

Checkpoint selection uses validation loss. The test script refuses to overwrite a previous report and evaluates the held-out test and excluded-class OOD trees once. These scripts do not create fabricated results.

The committed production artifact is `models/ewaste.onnx`. The larger intermediate Keras checkpoint and raw images are ignored. `reports/onnx_validation.json`, `reports/evaluation.json`, `reports/DATASET_REPORT.md`, and `reports/TRAINING_REPORT.md` record the actual run.

## Inference contract

- Input: RGB float32 NCHW `[1,3,224,224]`
- Resize: bilinear stretch to 224×224
- Normalize: `pixel / 127.5 - 1`
- Output: six logits in `classes.json` order
- Export: ONNX opset 17, CPUExecutionProvider validation

Java keeps one `OrtSession` for application lifetime and reads display names from the same `ml/classes.json`. Missing model artifacts still cause `MODEL_UNAVAILABLE`; the API does not substitute mock predictions.
