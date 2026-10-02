# RecoLens Machine Learning Guide

This guide covers the actual scripts under `ml/`. ML retraining is optional for using RecoLens: the committed `ml/models/ewaste.onnx` is copied into the Java container at build time.

## 1. Current model and dependency set

`ml/requirements.txt` pins:

| Dependency | Pin | Actual use |
|---|---:|---|
| TensorFlow | 2.17.0 | Keras MobileNetV2 construction, training, evaluation, image pipeline. |
| scikit-learn | 1.5.2 | balanced class weights and accuracy/precision/recall/F1/confusion report generation. |
| NumPy | 1.26.4 | tensors, metric aggregation and export parity calculations. |
| Pillow | 10.4.0 | image reading, EXIF orientation/dHash and source dataset auditing/preparation. |
| tf2onnx | 1.16.1 | converts the trained Keras model to ONNX opset 17. |
| onnxruntime | 1.20.0 | validates the exported graph and compares predictions on CPU in Python. |

There is no OpenCV, pandas, or separate PyTorch dependency in this ML requirements file. The classifier is MobileNetV2 from TensorFlow/Keras. The checked-in evaluation report records Python 3.11.15, TensorFlow 2.17.0 and Keras 3.15.1. Use Python 3.11 for the pinned TensorFlow stack; the current host's Python 3.14 should not be presumed compatible.

## 2. Create the isolated environment

From the repository root:

```bash
python3.11 -m venv ml/.venv
ml/.venv/bin/python -m pip install --upgrade pip
ml/.venv/bin/python -m pip install -r ml/requirements.txt
ml/.venv/bin/python -c 'import tensorflow, sklearn, numpy, PIL, tf2onnx, onnxruntime; print(tensorflow.__version__, sklearn.__version__, numpy.__version__, PIL.__version__, tf2onnx.__version__, onnxruntime.__version__)'
```

The virtual environment is ignored by Git. If installation fails because platform wheels are unavailable, use a supported Python 3.11 environment; do not silently replace the pinned library versions and then describe it as the recorded training setup.

## 3. Dataset: source, license and expected files

The selected source is the [Custom Bangladeshi E-Waste Image Dataset, Mendeley Data V1](https://data.mendeley.com/datasets/77383kmdnw/1), DOI `10.17632/77383kmdnw.1`. The project recorded its license as CC BY 4.0 from the Mendeley record and archive README. Preserve attribution, the license link, and a note of modifications. The dataset is not bundled in Git. Per-image author/source provenance and physical-object identity are not supplied by the archive.

Download the archive from the dataset landing page, retain a copy of the license and attribution record for redistribution, then extract it outside Git into `ml/data/raw/roboflow_v5/`. `prepare_dataset.py` expects `data.yaml` and the Roboflow layout below. The source `data.yaml` must contain a JSON-like `names: [...]` line matching the source annotation class IDs.

```text
ml/data/raw/roboflow_v5/
├── data.yaml
├── train/{images,labels}/
├── valid/{images,labels}/
└── test/{images,labels}/
```

The class-map file `ml/class_mapping.json` selects the six source labels and fixes the model's output order:

| Output ID | Canonical name | Display name | Dataset source label |
|---:|---|---|---|
| 0 | `battery_waste` | Battery waste | `Battery_Waste` |
| 1 | `keyboard` | Keyboard | `Keyboard` |
| 2 | `light_bulb` | Light bulb | `Light_Bulb` |
| 3 | `mobile_phone` | Mobile phone | `Mobile` |
| 4 | `mouse` | Mouse | `Mouse` |
| 5 | `pcb` | Printed circuit board | `PCB` |

Other source classes are excluded from supported training. The source archive contained 2,157 images across 12 source classes. The recorded audit found 0 corrupt images, missing labels, exact duplicate groups, or source filename-family split leaks. These source classes do not necessarily represent 2,157 distinct physical objects.

### Audit source without preparing it

```bash
ml/.venv/bin/python ml/scripts/validate_dataset.py \
  --data-root ml/data/raw/roboflow_v5 \
  --report ml/reports/dataset_validation.json
```

This is read-only with respect to the source data. It verifies image readability, dimensions, source labels, exact file hashes, filename-family split leakage and perceptual-hash candidate pairs. It writes the report path, overwriting an existing report of the same name.

### Prepare the classification and OOD trees

```bash
ml/.venv/bin/python ml/scripts/prepare_dataset.py \
  --data-root ml/data/raw/roboflow_v5 \
  --classes ml/class_mapping.json \
  --output ml/data/processed/classification \
  --ood-output ml/data/processed/ood_test \
  --report ml/reports/dataset_report.json
```

The script reads YOLO annotation files and accepts an image only when its label file yields one unique class. It checks image validity, source-family grouping, exact hashes and 64-bit dHash near-duplicate candidates. Selected same-class families within dHash distance 3 are grouped, then a seeded, class-stratified 70/15/15 split is built. Augmented variants stay in training; held-out family groups retain one image. The original test images from excluded source classes are copied to the separate OOD tree. The script removes and recreates its `--output` and `--ood-output` directories before writing; back up anything there before rerunning.

Output layout expected by training:

```text
ml/data/processed/classification/
├── train/{battery_waste,keyboard,light_bulb,mobile_phone,mouse,pcb}/
├── validation/{battery_waste,keyboard,light_bulb,mobile_phone,mouse,pcb}/
└── test/{battery_waste,keyboard,light_bulb,mobile_phone,mouse,pcb}/
```

Recorded final counts: 523 train images, 60 validation images and 60 test images. The excluded-class tree is `ml/data/processed/ood_test/<source-label>/`. Current local dataset trees are not tracked; this structure must be recreated from the licensed source before retraining.

## 4. Preprocessing contract

Training and Java inference must remain aligned:

```text
encoded image
→ RGB decode (Java applies EXIF orientation)
→ bilinear stretch resize to 224×224 (no crop)
→ float32 conversion
→ each channel value = pixel / 127.5 - 1.0
→ NCHW tensor [1, 3, 224, 224]
→ ONNX logits [1, 6]
```

Training implements resize, RGB decode and normalization in `ml/training/train.py::make_dataset`; the dataset pipeline transposes NHWC to NCHW. Java performs the matching resize/channel loop in `backend/.../service/OnnxClassifier.java`. `ml/class_mapping.json` is shared as the canonical ordered label list. A preprocessing or order mismatch can make a structurally valid model return wrong names.

## 5. Train MobileNetV2

First ensure the checkpoint destination does not exist: training intentionally refuses to overwrite `best_model.keras`.

```bash
ml/.venv/bin/python ml/training/train.py \
  --data ml/data/processed/classification \
  --classes ml/class_mapping.json \
  --out ml/models \
  --frozen-epochs 12 \
  --fine-tune-epochs 8
```

Actual defaults and behavior from `train.py`:

- ImageNet MobileNetV2 backbone, initially frozen; ImageNet weights are fetched through Keras if not cached.
- Global average pooling → dropout 0.25 → dense logits layer sized from the class map.
- Fixed input 224×224 RGB, NCHW, float32; seed 42; batch size 16.
- Adam at `1e-3` in the frozen stage and `1e-5` in fine-tuning.
- Sparse categorical cross-entropy from logits; sparse categorical accuracy reported during fitting.
- Balanced class weights are calculated from the training labels.
- Training-time augmentation applies mild horizontal flips, small rotation (0.04), zoom (0.08), translation (0.04), and contrast (0.12). Augmentation is inactive at inference. Existing v1 ONNX weights are unchanged; it was used by the separate candidate-v2 experiment.
- Up to 12 frozen and 8 fine-tune epochs by default; early stopping monitors validation loss with patience 3; best validation-loss checkpoint is saved.
- The final 20 backbone layers are unfrozen for fine-tuning; batch-normalization layers remain frozen.

Outputs: `ml/models/best_model.keras`, `ml/models/training_report.json`, and `ml/models/model_metadata.json`. The script refuses an existing checkpoint to avoid silently replacing a prior training result. Choose a new `--out` directory for another run, then pass that checkpoint path explicitly to evaluation/export. Training produces validation loss/accuracy and history; the separate evaluation script computes held-out precision/recall/F1 and a confusion matrix.

## 6. Evaluate the selected checkpoint

`evaluate.py` refuses to overwrite an existing report path because the test set should be evaluated once for the selected experiment. Use a new report path for a new run:

```bash
ml/.venv/bin/python ml/scripts/evaluate.py \
  --data ml/data/processed/classification \
  --ood-data ml/data/processed/ood_test \
  --classes ml/class_mapping.json \
  --model ml/models/best_model.keras \
  --out ml/reports/evaluation-rerun.json
```

Implemented metrics: accuracy, macro and weighted precision, recall and F1, per-class classification report, confusion matrix, and a limited excluded-source-class forced-prediction characterization. It does not run a household-object open-set benchmark. The OOD calculation explicitly notes that this closed-set model always picks a supported class.

Recorded v1 run: 60 held-out test images, accuracy 0.9833, macro F1 0.9876, weighted F1 0.9834. The light-bulb test class had only 3 images. Source images do not have physical-object IDs, so reported estimates are uncertain and are not a field-performance guarantee. The threshold 0.66 was chosen from validation only (60 images); it is an initial decision floor, not a calibrated probability claim. The seven-class candidate-v2 result is separately documented in [`MODEL_IMPROVEMENT_REPORT.md`](MODEL_IMPROVEMENT_REPORT.md); it regressed e-waste recall and must not replace v1.

## 7. Export, validate, and test ONNX

Export directly to the filename consumed by the Java container:

```bash
ml/.venv/bin/python ml/scripts/export_onnx.py \
  --model ml/models/best_model.keras \
  --data ml/data/processed/classification \
  --classes ml/class_mapping.json \
  --out ml/models/ewaste.onnx \
  --report ml/reports/onnx_validation.json
```

The script converts to ONNX opset 17, runs `onnx.checker`, opens the model with Python ONNX Runtime's `CPUExecutionProvider`, checks one input/output and six outputs, and compares Keras/ONNX logits and argmax labels over up to four validation batches. It fails if max absolute logit difference exceeds `1e-4` or any argmax differs. Note: the script's default `--out` is `ml/models/onnx/ewaste_mobilenetv2.onnx`; specify `--out ml/models/ewaste.onnx` for the production artifact.

Run the full image-by-image parity/latency checker with a separately named report if preserving the existing report:

```bash
ml/.venv/bin/python ml/scripts/validate_onnx.py \
  --model ml/models/best_model.keras \
  --onnx ml/models/ewaste.onnx \
  --data ml/data/processed/classification \
  --classes ml/class_mapping.json \
  --report ml/reports/onnx-validation-rerun.json
```

Expected input is one float32 NCHW tensor `[N,3,224,224]`; output is float32 logits `[N,6]` in `class_mapping.json` order. The recorded artifact passed with 60/60 validation argmax agreements and maximum absolute logit difference `5.72e-05`. Python reports are evidence for the recorded artifact; rerun after replacing it.

## 8. Install model in the Java API

Production runtime paths are `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`, set by `backend/Dockerfile` and `render.yaml`. The container build copies the tracked ONNX and class map into the image; no mounted volume or object storage is used. Locally in Compose the same paths are used. The Java constructor checks files, contiguous class IDs, ONNX input shape, and output class count at startup.

- Missing files → `MODEL_UNAVAILABLE`; `/health` remains process-up and classification returns HTTP 503.
- Bad JSON, invalid tensor dimensions/output count, or session load failure → `MODEL_LOAD_ERROR`; `/health` reports it and classification returns HTTP 503.
- Replacing an artifact requires a backend image rebuild/redeploy and an inference check, not only copying a file to the host.

## 9. ML test command and status

```bash
ml/.venv/bin/python -m unittest discover -s ml/tests -v
```

The checked-in Python pipeline tests require a supported Python/TensorFlow environment and local dataset/model artifacts. In the Phase 7 run, candidate-v2 ONNX export and parity were run and passed; Java parity and production deployment were not run because the candidate failed offline e-waste regression. The recorded training, test-set evaluation, and ONNX parity reports are under `ml/reports/`; consult them for recorded—not newly regenerated—results.

## 10. Add or replace a category/model

Do not edit the class map alone. A new model output must have matching dataset labels, trained output dimension and class order.

1. Obtain a licensed dataset that contains the new category and document its license/provenance in `ml/DATASET_SOURCES.md`.
2. Update `datasetLabel` and ordered `{id,name,displayName,datasetLabel}` in `ml/class_mapping.json`; update source label parsing only if the source format changes.
3. Run `validate_dataset.py`, then `prepare_dataset.py`; inspect class/split counts and near-duplicate/source leakage reports.
4. Train a fresh model to a new output directory; review validation results and evaluate once on held-out test data. Improve/calibrate confidence behavior with appropriately sized validation data; do not reuse the current 0.66 threshold without review.
5. Export ONNX using the exact preprocessing and class order; run both ONNX checks.
6. Update the browser's `guides` data and `guideForCategory()` mapping in `app.js` if category-specific advice should be shown. The backend's current `guide` response is null; the frontend uses static guide data.
7. Replace/commit `ml/models/ewaste.onnx`, `ml/class_mapping.json`, metadata and reports only after verifying intended licensing and output parity.
8. Build/redeploy the API image, verify `/health` is `MODEL_READY`, submit representative positive/low-confidence images, verify category names, then verify the live frontend.

The model is a closed-set classifier: new classes do not make it capable of recognizing arbitrary unknown objects. Use a separate, suitable out-of-domain test set before presenting unknown detection as implemented.

### Rejected not-e-waste candidate

The isolated candidate recipe is:

```bash
ml/.venv/bin/python ml/scripts/build_reject_candidate.py
ml/.venv/bin/python ml/training/train.py \
  --data ml/data/candidates/reject_v2 \
  --classes ml/data/candidates/reject_v2/class_mapping.json \
  --out ml/models/candidate_v2
```

Candidate output paths are ignored and the builder refuses to overwrite existing candidate data. Its evaluation and parity command/results are recorded in `docs/MODEL_IMPROVEMENT_REPORT.md` and `ml/reports/candidate_v2_*.json`. It is intentionally not deployable: its e-waste-only test score regressed to 52/60 and a charger was rejected as not e-waste.
