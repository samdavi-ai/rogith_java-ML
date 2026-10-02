# Phase 7B — accuracy improvement decision

Date: 2026-10-02. This Phase 7B report builds on the detailed prior experiment in [`docs/MODEL_IMPROVEMENT_REPORT.md`](../../docs/MODEL_IMPROVEMENT_REPORT.md).

## Decision

**NOT DEPLOYED.** Production remains RecoLens model v1.0.0, the six-class MobileNetV2 model. Before work began, its ONNX artifact was copied byte-for-byte to [`models/archive/recolens-v1-production.onnx`](../models/archive/recolens-v1-production.onnx), SHA-256 `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`. No production weights, ONNX file, mapping, Java inference code, or Render deployment were changed.

## Comparison evidence

| Test | Production v1 | Rejected negative-class candidate | Decision |
|---|---:|---:|---|
| Existing e-waste set | 59/60 (98.33%) | 52/60 (86.67%) | candidate regressed; reject |
| Mixed six-class + non-e-waste split | not comparable as a closed-set baseline; all negatives forced to electronics | 92.57% accuracy, 89.89% macro F1 on 175 images | candidate learns negatives but loses e-waste cases; reject |
| Bottle screenshot crop | Mouse, 72.2% replay | not_e-waste, 99.95% replay | candidate improves this one qualitative example |
| Charger/adapter screenshot crop | Light bulb, 70.7% replay | not_e-waste, 99.93% replay | candidate false negative; reject |
| Laptop-with-keyboard screenshot crop | Keyboard, 86.4% replay | Keyboard, 55.1% replay | laptop remains unsupported |
| Real mobile camera cohort | 3 user-supplied screenshot crops; no representative independent camera suite | same 3 crops | insufficient to claim real-world improvement |

The baseline full per-class metrics, confusion matrices, candidate metrics and split counts are in [`evaluation.json`](evaluation.json), [`candidate_v2_evaluation.json`](candidate_v2_evaluation.json), [`model_comparison_v1_vs_candidate_v2.json`](model_comparison_v1_vs_candidate_v2.json), and the linked detailed report. The 175-image aggregate score is not a fair basis to ignore the 7-case regression on the existing 60-image e-waste test.

## Root cause assessment

The verified root cause is a taxonomy gap: production supports only battery, keyboard, bulb, phone, mouse, and PCB. A bottle, charger, or laptop is out of scope, and the closed-set head always selects one of the six classes unless the confidence falls below the existing 0.66 rejection threshold. The example images likely also expose object scale/framing, background, occlusion, and camera-domain differences compared with centered dataset images. Those are plausible contributing factors, not confirmed visual-feature explanations. The screenshot results do not establish that Java preprocessing caused the errors.

## Data and training

The existing CC BY 4.0 Mendeley archive has 2,157 images in 12 labels, but selected classes have modest support and there is no charger/laptop class. The Phase 7B audit found no corruption, exact duplicates, missing labels, or filename-family split leaks; 544 low-dHash cross-split pairs are flagged for review, and image names cannot establish unique physical objects. The GIZ CC BY 4.0 source may help with broad electronics/laptops but lacks charger labels and needs object-crop and split audit. Public Roboflow listings were not counted as datasets because their versioned image exports were not independently obtained and checked. No new model was trained from unaudited samples.

## Preprocessing, parity, and release gates

The input contract remains RGB float32 NCHW `[1,3,224,224]`, bilinear stretch resize, `pixel/127.5 - 1`. Existing Keras-to-ONNX tensor parity passed 60/60 baseline validation images (max logit difference `5.72e-05`). The Java implementation has matching intended channel order, layout, size, and normalization formula, but Graphics2D interpolation and EXIF orientation have not been proven equivalent to the Python image loader on identical byte fixtures. See [`preprocessing_parity.md`](preprocessing_parity.md). Thus Java end-to-end top-k/confidence parity is **not certified** for a new candidate.

No candidate qualifies: there is no auditable expanded-class dataset, no broad locked real-camera set, no candidate that preserves the 59/60 e-waste benchmark, and no end-to-end Java parity result. Candidate integration, app response changes, Render staging, and production deployment are therefore not justified. The live URL remains [recolens-h55g.onrender.com](https://recolens-h55g.onrender.com/).

## Next evidence required

Obtain a versioned license-cleared image export with enough charger/adapter and whole-laptop examples plus clean non-electronic negatives; audit object identities and duplicate groups; preserve a locked, independently captured phone-camera suite across the supported and negative classes; then train one expanded classifier and one justified rejection/two-stage alternative. Compare on the unchanged 60-image baseline and held-out new-device suite, calibrate only on validation, and add identical-image Python/Java ONNX top-k and confidence comparison before any integration or deployment decision.
