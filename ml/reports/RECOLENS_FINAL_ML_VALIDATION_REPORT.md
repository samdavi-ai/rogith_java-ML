# RecoLens final ML validation report — Phase 10

Audit date: 2026-10-02  
Final decision: **V2 NOT APPROVED**

## 1. Executive summary

The existing V1 Java/Python/ONNX fixture parity passes when rerun on OpenJDK 17. A seven-class MobileNetV2 candidate and prior evaluation artifacts already exist in this repository, although Phase 9 did not train a model. That candidate is not release ready: its dataset split has 180 unresolved near-duplicate candidates, it drops compatible V1 accuracy from 59/60 to 52/60, and there is no locked camera test set. No Phase 10 training, model export, frontend modification, or deployment was done. Release gates are in [RELEASE_GATE.md](RELEASE_GATE.md).

## 2. Problem definition

RecoLens currently classifies six electronic-item categories. Existing V1 cannot reject general household objects. The existing candidate adds a derived `not_ewaste` category but adds no verified charger/adapter, whole-laptop, monitor, cable, earphone/headphone or unknown-object support. The candidate remains diagnostic only.

## 3. Dataset and licensing

The candidate tree contains 1,468 files from the Mendeley/Roboflow version 5 source declared CC BY 4.0: 1,120 train, 173 validation and 175 test. Six e-waste labels account for 643 files; 825 files from glass, organic, paper and plastic labels were aggregated into `not_ewaste`. The source has 2,157 source images across 12 labels; transformations and required attribution are in [DATASET_SOURCES_FINAL.md](../DATASET_SOURCES_FINAL.md). No unclear-license candidate was used. Source provenance is not recorded per image.

## 4. Data preprocessing and augmentation

The existing candidate uses the shared RGB 224×224 bilinear stretch and `pixel / 127.5 - 1.0` normalization. Its training metadata says source training variants were retained, seed 42 was used, and train-only online augmentation is represented in the 1,120 training image count. Exact augmentation operations were not recovered as a separately versioned Phase 10 config. No additional augmentation or data preprocessing was run in this phase.

## 5. Model architecture and training configuration

An existing candidate artifact uses MobileNetV2 ImageNet features, global average pooling, dropout 0.25 and a dense seven-logit head; the last 20 backbone layers were fine-tuned with batch normalization frozen. Metadata records Adam, batch 16, frozen learning rate 0.001, fine-tune learning rate 0.00001, up to 12 frozen and 8 fine-tune epochs, validation-loss early stopping with patience 3 and best-weight restoration, class weighting, seed 42. This is historical candidate metadata, not a Phase 10 training run. No new model, final checkpoint, curves, configuration, or class map were created.

## 6. Evaluation methodology and dataset quality

The existing candidate evaluation covers 175 source-split files (60 from the six old categories plus 115 derived negatives). Re-audit finds 0 corrupt/small images, 0 exact duplicate groups, 0 source filename families crossing splits, but 180 cross-split dHash≤3 candidates (all same-label; 23 distance 0, 34 distance 1, 50 distance 2, 73 distance 3). As these have not all been adjudicated/grouped, the test is not treated as locked or independent. The report is [V2_DATASET_FINAL_REPORT.md](V2_DATASET_FINAL_REPORT.md).

## 7. Accuracy, precision, recall, F1 and confusion matrix

Existing candidate metrics on its diagnostic 175-image split:

- Accuracy / top-1: **92.57%**.
- Macro precision / recall / F1: **89.75% / 90.81% / 89.89%**.
- Weighted precision / recall / F1: **93.14% / 92.57% / 92.61%**.
- Top-3 accuracy: **NOT TESTED**.

Per-class precision, recall, F1 and support:

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| Battery waste | 84.62% | 73.33% | 78.57% | 15 |
| Keyboard | 100.00% | 100.00% | 100.00% | 8 |
| Light bulb | 100.00% | 100.00% | 100.00% | 3 |
| Mobile phone | 72.73% | 66.67% | 69.57% | 12 |
| Mouse | 100.00% | 100.00% | 100.00% | 6 |
| PCB | 72.73% | 100.00% | 84.21% | 16 |
| Not e-waste | 98.21% | 95.65% | 96.92% | 115 |

Confusion matrix, rows true and columns predicted in the table order:

```text
[[11,0,0,3,0,1,0], [0,8,0,0,0,0,0], [0,0,3,0,0,0,0],
 [1,0,0,8,0,1,2], [0,0,0,0,6,0,0], [0,0,0,0,0,16,0],
 [1,0,0,0,0,4,110]]
```

These are historical candidate values, not release measurements, because the split is not cleanly isolated.

## 8. Real-world camera evaluation

Official real-world images: **0**. The manifest is empty. Diagnostic screenshot crops are excluded, so standard dataset accuracy and real-world camera accuracy are kept separate: 92.57% diagnostic source-split accuracy; real-world accuracy **NOT TESTED**. Lighting, device, orientation, distance, and background coverage are unavailable.

## 9. Non-e-waste and unknown-object handling

On 115 derived negative test examples, candidate V2 has negative precision 98.21%, recall 95.65%, F1 96.92%; five were assigned known e-waste classes, giving a source-split false e-waste rate of 4.35%. This is not a real-world false e-waste rate.

There is no separate unknown class and no validation-derived unknown threshold evaluation. The backend has a configured minimum confidence default of 0.66 that returns `status: UNSURE` with a null category; evidence that this threshold was calibrated on validation data is absent. Counts for accepted known objects and rejected/accepted unknowns are **NOT TESTED**.

## 10. Java/Python/ONNX parity

The Phase 9 V1 parity fixture was rerun. On 60 images: decoded RGB hashes agree 60/60; maximum/mean tensor error `8.60691e-5 / 3.20378e-7`; maximum/mean logit error `7.73072e-5 / 1.51503e-5`; maximum/mean probability error `2.19728e-5 / 2.80507e-7`; top-1, top-3 and top-5 agree 60/60. RGBA PNG and EXIF JPEG probes match decoded pixels 2/2. The parity gate passes for V1 on the tested JDK 17 and ONNX Runtime 1.20. Candidate V2 Java parity was **NOT TESTED**. The full details and old mismatch replay are in [java_onnx_parity_v2.md](java_onnx_parity_v2.md).

## 11. V1 vs V2

On the same 60 examples from existing classes, V1 achieved 59/60 (98.33%, macro F1 98.76%); candidate V2 achieved 52/60 (86.67%, macro F1 90.86%). Candidate V2's macro precision/recall/F1 on those six labels were 92.21%/90.00%/90.86%. Regression gate: **FAIL**. Full comparison: [V1_VS_V2_COMPARISON.md](V1_VS_V2_COMPARISON.md).

## 12. API and frontend integration

Backend contract in source is an `Envelope` containing `data.classification` with `status`, `categoryName`, `confidence`, `confidenceLevel`, `alternatives`, and `guide`. Low confidence returns `UNSURE`, null `categoryName`; it does not implement the sample `label`/`REJECTED` fields verbatim. Frontend upload opens the file picker, while camera use has a separate explicit “Start camera” action. History is described as browser-local. These source paths were inspected; candidate V2 was not wired into them and no V2 end-to-end image upload was run.

## 13. Deployment and production status

No deployment was made. The production homepage returned HTTP 200 on 2026-10-02; `GET /health` returned HTTP 404. Therefore frontend reachability is observed, but backend health, `MODEL_READY`, camera, upload classification, guide/history production flows and actual production classification are **NOT TESTED / NOT CONFIRMED**. Local active and archived V1 model files match at SHA-256 `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`; this does not prove the live service's model hash.

## 14. Performance

An existing candidate Python ONNX timing artifact reports median 6.71 ms, p95 9.75 ms, max 10.43 ms for model inference in its recorded environment. Upload size, server preprocessing, API response time, total user-visible latency, and production measurements were **NOT TESTED**. Do not extrapolate that model-only timing to user-perceived latency.

## 15. Limitations and future work

Obtain a versioned, licensed, auditable dataset with relevant class counts; resolve or regroup all 180 candidate near-duplicate pairs and the existing mixed-label image groups; review source-image provenance; collect a separate consented real camera set with device/light/distance/orientation metadata; calibrate unknown behavior on validation data; then repeat compatible V1 regression, V2 Java/ONNX parity, API and product smoke checks. New classes should be added only when each has enough object-independent train/validation/test evidence.

## 16. Final release decision

**V2 NOT APPROVED.** Exact blockers: candidate split leakage unresolved; no accepted real-world camera test set; candidate loses 7/60 compatible existing-class predictions against V1; candidate V2 Java parity and end-to-end API behavior are untested; production health route returns 404; and the live served model cannot be verified. Keep V1 and do not deploy candidate V2.
