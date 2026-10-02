# RecoLens model improvement report

Date: 2026-10-02. This report distinguishes the production baseline (`v1.0.0`) from an offline, rejected seven-class candidate (`candidate-v2`). No candidate artifact was promoted or deployed.

## Root cause assessment

The deployed taxonomy consists of six classes: battery waste, keyboard, light bulb, mobile phone, mouse, and PCB. A charger, laptop, or ordinary plastic bottle is not represented. The v1 model must return one of its six labels for every image; the API's confidence floor only rejects low-confidence results and cannot detect an unsupported object. This explains why the examples can be confidently misclassified without proving any one training defect. Small supports, limited collection diversity, and phone-camera/background domain shift are additional plausible causes. The screenshots do not establish a Java preprocessing mismatch; Python Keras-to-ONNX parity is measured, while Java pixel-array parity still needs a direct fixture comparison.

## Dataset decision and audit

The local archive audit found 2,157 images in 12 labels, with no corrupt images, missing labels, exact duplicate groups, or source filename-family split leakage. The class inventory and counts are in [`ml/reports/dataset_report.md`](../ml/reports/dataset_report.md) and JSON. Selected v1 classes were grouped by filename families and same-class dHash candidates before a deterministic 70/15/15 split. The final six-class split has 523 train, 60 validation, and 60 test images. Test data was not used to select the checkpoint.

For the experiment, four general-waste labels (Plastic, Paper, Glass, Organic) formed `not_ewaste`; Metal and Medical were excluded because they can include electronic materials/items. Their original source train/valid/test partitions were preserved. The candidate held 597 negative training images, 113 validation images, and 115 negative test images. The existing selected-class test set remained unchanged. The three screenshot crops were evaluation-only and not included in any split.

## Model and training changes

The production v1 model, weights, class map, ONNX, Java behavior, and live Render deployment were left unchanged. The training script now has mild, training-only augmentation: horizontal flip, small rotation, zoom, translation, and contrast changes. An isolated candidate was trained with the existing MobileNetV2 ImageNet backbone, 224×224 NCHW RGB input, balanced class weights, batch size 16, seed 42, Adam at 1e-3 then 1e-5, up to 12 frozen and 8 fine-tuning epochs, validation-loss checkpoint selection and patience 3. Candidate training took 156.8 seconds on CPU. The candidate checkpoint is ignored by Git and remains local.

## Same-test-set comparison

Both models were run against the same 175 candidate-v2 test images with repository TensorFlow preprocessing. V1 can only emit one of its six electronics classes, so it necessarily fails every `not_ewaste` example. Metrics below are an experiment-specific comparison, not field accuracy.

| Metric | v1 baseline | Candidate-v2 | Samples |
|---|---:|---:|---:|
| Accuracy | 33.71% | 92.57% | 175 |
| Macro precision | 42.80% | 89.75% | 175 |
| Macro recall | 84.76% | 90.81% | 175 |
| Macro F1 | 52.16% | 89.89% | 175 |
| Weighted F1 | 20.92% | 92.61% | 175 |

The aggregate score conceals an unacceptable regression: on the same 60 supported e-waste examples, v1 classified 59/60 correctly (98.3%), while candidate-v2 classified 52/60 (86.7%). Candidate-v2's per-class F1 was battery 0.786, keyboard 1.000, light bulb 1.000, mobile phone 0.696, mouse 1.000, PCB 0.842, and `not_ewaste` 0.969. The increase in aggregate accuracy is largely the candidate's learned ability to reject general-waste images; it does not justify the lost e-waste recall.

### Confusion analysis

Rows are actual classes and columns are predicted classes in this order: Battery, Keyboard, Light bulb, Mobile, Mouse, PCB, Not e-waste.

Candidate-v2 matrix:

```text
[[11, 0, 0, 3, 0, 1, 0],
 [ 0, 8, 0, 0, 0, 0, 0],
 [ 0, 0, 3, 0, 0, 0, 0],
 [ 1, 0, 0, 8, 0, 1, 2],
 [ 0, 0, 0, 0, 6, 0, 0],
 [ 0, 0, 0, 0, 0,16, 0],
 [ 1, 0, 0, 0, 0, 4,110]]
```

The candidate missed eight supported items: three Battery→Mobile, one Battery→PCB, one Mobile→Battery, one Mobile→PCB, and two Mobile→Not e-waste. Four negative examples were predicted PCB and one Battery. Screenshot replay with the repository preprocessing: bottle → `not_ewaste` 99.95%; laptop scene → Keyboard 55.1%; adapter → `not_ewaste` 99.93%. The laptop image visibly includes a keyboard and laptop; laptop is unsupported, so Keyboard is not a reliable whole-device identification. The adapter result is a serious false negative. These three images are qualitative only and do not contribute to aggregate metrics.

## Export / deployment gate

Candidate Keras-to-ONNX export passed with opset 17, output `[N,7]`, and 173/173 validation argmax agreements. Across 173 validation images, maximum absolute logit difference was `5.96e-05`; maximum probability difference was `8.55e-06`. Python ONNX validation median single-image runtime was 6.71 ms and p95 9.75 ms on this local CPU. These do not establish Java parity or Render performance.

The required next promotion stages were intentionally not run: Java integration, staging, and production deployment require a candidate that passes offline e-waste/non-e-waste regression first. Candidate-v2 failed that gate. Production continues using the six-class v1 model; no online model change was made. No before/after claim is made about live performance.

## Next data and model work

Acquire appropriately licensed, diverse laptop and charger examples plus a broader set of everyday negatives. Define a separate `other_electronics` or hierarchical e-waste stage so unsupported electronics are not collapsed into non-e-waste. Preserve physical-object/source grouping and locked splits. Train and compare against the current baseline, prioritizing e-waste recall and false-negative cost alongside negative rejection. Add a mobile/laptop/charger challenge cohort captured independently of training, then calibrate on a sufficiently large validation set. Only after that candidate passes all locked tests should Java output semantics, API compatibility, local/staging deployment, and production be changed.

## Reproducibility artifacts

- Candidate dataset construction: `ml/scripts/build_reject_candidate.py` (refuses to overwrite its output).
- Candidate split manifest and class map: local ignored directory `ml/data/candidates/reject_v2/`.
- Comparison: `ml/reports/model_comparison_v1_vs_candidate_v2.json`.
- Candidate evaluation: `ml/reports/candidate_v2_evaluation.json`.
- Candidate export/parity: `ml/reports/candidate_v2_onnx_export.json`, `ml/reports/candidate_v2_onnx_parity.json`.
- Screenshot challenge labels and crop hashes: `ml/tests/fixtures/real_world_challenges/manifest.json`. Image pixels stay local and are ignored by Git; source screenshots were user-provided.
