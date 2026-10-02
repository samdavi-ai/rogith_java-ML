# RecoLens Phase 8 final report

Audit date: 2026-10-02. Repository baseline: `f6f6ec6`. Phase 8 followed the instruction to stop before training when no suitable expanded-class dataset passes the data gate.

## 1. Objective

Establish a defensible taxonomy, license-cleared data inventory, data quality gate, locked real-world evaluation protocol, and runtime parity evidence before training an accuracy V2 model.

## 2. Phase 7B findings

Production v1.0.0 recognizes battery, keyboard, light bulb, phone, mouse, and PCB, with 59/60 correct on the existing held-out set. Bottle, charger/adapter, and laptop are outside its class space, so a closed-set prediction may force them into a known class. The previous negative-class candidate recovered the bottle crop but regressed the existing e-waste set to 52/60 and incorrectly marked the adapter as non-e-waste.

## 3. Taxonomy

The official proposal is [`../RECOLENS_CLASS_TAXONOMY.md`](../RECOLENS_CLASS_TAXONOMY.md). The existing six are APPROVED only for v1; charger_adapter and laptop are PROPOSED pending data; monitor, cable, earphones/headphones and broad `other_electronic` are DEFERRED. `E_WASTE`, `NOT_E_WASTE`, and `UNKNOWN` are system-level results, not necessarily model logits. Production v1 does not support `NOT_E_WASTE` as a class or binary decision.

## 4. Dataset research and licensing

Source candidates, licenses, counts, relevant categories, redistribution/commercial use notes and disposition are documented in [`../DATASET_CANDIDATES.md`](../DATASET_CANDIDATES.md). The current 2,157-image Mendeley source is CC BY 4.0 and already audited, but lacks explicit charger/laptop labels. GIZ is CC BY 4.0 with laptop/computer detection labels but has not been acquired or file-audited; its viewer reports failure and it has no charger label. Bower is MIT and phone-camera validation imagery, but file audit uncovered a card/archive count discrepancy and it only labels e-waste generically. Gated/unclear-license sources were not used; the CC BY-NC-only source was rejected for commercial RecoLens use.

## 5. Dataset audit

The current source audit is documented in [`dataset_audit.md`](dataset_audit.md). A downloaded Bower Parquet was file-audited using [`../scripts/audit_bower_dataset.py`](../scripts/audit_bower_dataset.py); results are [`bower_dataset_audit.json`](bower_dataset_audit.json). The Bower archive has 2,546 rows, 1,578 unique image IDs/byte hashes, all JPEG, zero decode failures, zero exact duplicates, zero decoded dimension mismatches, one near-duplicate candidate, 24 images below 224 px on one side, and one null-only image. Its card says 1,440 images. There are 57 derived e-waste, 1,520 non-e-waste and one unlabeled image, using a documented frame aggregation rule. 544 frames contain multiple annotation rows, and 468 have more than one distinct material/object combination. No PII review has been completed, so it was not accepted as the locked RecoLens test set.

**Gate:** no new data passes the charger/laptop class-quality gate. Stop before V2 training.

## 6. Real-world test methodology

Capture instructions are in [`../REAL_WORLD_TEST_PROTOCOL.md`](../REAL_WORLD_TEST_PROTOCOL.md): bright/normal/low lighting, plain/cluttered background, close/medium/far distance, front/side/angled views, distinct physical-object grouping, no PII, source/consent metadata, and checksum lock before evaluation. The required multi-condition set is not complete. Three user-provided screenshot crops remain a locked diagnostic pilot only; see [`../data/recolens_real_world_test_manifest.csv`](../data/recolens_real_world_test_manifest.csv). Metadata is incomplete and no aggregate accuracy is reported. Bower remains a future external test candidate, not the RecoLens locked set.

## 7. Data layout and splits

Scaffolds exist at `ml/data/train/`, `ml/data/validation/`, `ml/data/test/`, and `ml/data/recolens_real_world_test/`. New training/validation/test folders are empty by design. The real-world pilot stays separate and is not used for training, validation, calibration, or model selection. Object/source grouping and locked-set protocol are defined before any new training.

## 8. Model architecture

No Phase 8 model was trained. Production remains the six-logit MobileNetV2 v1: 224×224 RGB float32 NCHW, bilinear stretch, `pixel/127.5 - 1`; existing training used ImageNet weights, a global-average-pooling/dropout/dense head, balanced class weights, Adam 1e-3 then 1e-5, up to 12 frozen and 8 fine-tuning epochs, and early stopping. This configuration is recorded for reproducibility, not as a Phase 8 experiment.

## 9. Training and augmentation

No Phase 8 train/validation/test split was populated and no V2 training run occurred. Existing v1 training-time augmentation was horizontal flip, small rotation, zoom, translation and contrast. The desired brightness/blur/perspective variants remain a future controlled proposal and were not tested. Two empty stage directories are not experiments.

## 10. Evaluation and comparison

Actual baseline and prior-candidate results are in [`phase8_model_comparison.md`](phase8_model_comparison.md) and [`phase8_model_comparison.json`](phase8_model_comparison.json). Baseline six-class set: 60 images, accuracy 0.9833, macro precision 0.9872, macro recall 0.9889, macro F1 0.9876. The earlier seven-class candidate obtained 92.57%/89.89% macro F1 on its 175-image mixed split but only 52/60 on the existing e-waste cases; it remains rejected. No Phase 8 candidate has accuracy/per-class metrics because no candidate was trained. Bower was not scored with the production classifier because its binary target would not be a valid v1 output.

## 11. Regression gate

V1's 59/60 existing test performance remains the release baseline. The previous negative-class candidate lost seven correct predictions. A V2 would need to preserve this benchmark and separately demonstrate improvements on sufficiently supported new classes and negatives. No V2 has passed or been selected.

## 12. Confidence calibration and unknown behavior

The production minimum-confidence floor is 0.66, selected from a small validation set and not a probability guarantee. Existing out-of-domain experiments found confident forced predictions for ordinary waste. The previous candidate returned approximately 99.9% `not_ewaste` for the adapter crop, demonstrating that softmax confidence alone can be misleading. Phase 8 did not fit a calibrator or retune thresholds. `UNKNOWN` remains a conceptual system state; current API only uses its existing `UNSURE` behavior below threshold.

## 13. Python / ONNX parity

The existing Keras-to-ONNX tensor check passed 60/60 with maximum absolute logit difference `5.72e-05` (see [`onnx_validation.json`](onnx_validation.json)).

## 14. Java / ONNX parity

OpenJDK 17.0.20.1 was available through Homebrew. A new automated same-image check compared Python repository preprocessing plus ONNX Runtime against Java ImageIO/Graphics2D plus ONNX Runtime on all 60 baseline test images. Top-1 classes matched 60/60, top-4 labels matched 237/240, maximum top-1 probability delta was 0.045159 and maximum top-4 delta 0.045443. The explicit ≤0.02 diagnostic parity assertion failed. See [`java_onnx_parity.md`](java_onnx_parity.md) and the repeatable [`verify_java_onnx_parity.py`](../scripts/verify_java_onnx_parity.py). The mismatch likely involves image decode/resize; exact cause still requires pixel-tensor comparison. This is a release blocker.

## 15. API contract

No application source, API contract, class map, or response schema was changed. `POST /api/classifications` and existing upload/camera consumers are untouched.

## 16. Camera workflow

Existing automated camera-controller tests cover start, capture/compression, API submission, response stabilization, stop, camera switch, and supported flashlight behavior. No new physical desktop or mobile camera session was performed for Phase 8. The user-provided three screenshot crops are the only real-world diagnostic predictions carried forward; they are not a complete camera regression.

## 17. Candidate comparison

The two-stage strategy is documented below as the better conceptual fit only if adequate data becomes available. A single multiclass approach has less serving complexity but entangles subtype learning and negative rejection; prior results demonstrate that adding one `not_ewaste` class can hurt existing e-waste recall. Phase 8 intentionally did not create V2-A, V2-B, or V2-C experiments without data capable of distinguishing their hypotheses.

## 18. Production decision and safety

**NOT DEPLOYED.** The six-class ONNX model and its versioned backup are byte-identical (SHA-256 `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`). No Java serving change, API/UI change, ONNX replacement, or Render deployment occurred. A read-only production check on 2026-10-02 returned HTTP 200 for the frontend and `MODEL_READY` / `UP` from the API health endpoint; the deployed artifact hash is not exposed by that endpoint. Java numerical parity is not yet at the configured diagnostic gate. Production URL remains [recolens-h55g.onrender.com](https://recolens-h55g.onrender.com/).

## 19. Limitations and next steps

Resolve Bower metadata count discrepancy and finish privacy/label review if using it as binary external evaluation. Obtain and file-audit licensed charger/adapter and whole-laptop data; verify per-class counts, provenance, object IDs, duplicates, near-duplicates and split leakage. Collect a consented, PII-free RecoLens camera suite across all target lighting/background/distance/orientation factors. Compare Python/Java preprocessed pixels to fix the measured parity gap. Only after those gates pass should controlled MobileNetV2 multiclass and two-stage experiments be considered. Deploy nothing until regression, real-world, ONNX, Java, API, and camera checks all pass.

## Two-stage vs single model (conceptual)

| Strategy | Advantages | Risks / requirements |
|---|---|---|
| Single multiclass model (electronic subtypes + non-e-waste) | One model/session, low latency, simpler Java/ONNX integration, learns boundaries jointly | Class imbalance and negative images can erase subtype recall; every class needs balanced, clean examples; a broad negative class may absorb unsupported electronics |
| Two-stage system | Stage 1 can focus on E_WASTE/NOT_E_WASTE/UNKNOWN; stage 2 focuses on subtype only after electronic evidence; easier to expand taxonomy separately | False negatives at Stage 1 suppress all subtype predictions; errors compound; needs sufficiently varied positive/negative data and calibrated cascade thresholds; Java must load/manage two sessions and maintain backward-compatible response semantics |

Given the observed candidate regression and absent charger examples, a two-stage experiment is plausible but not evidence-selected. Its training requirements are a broad, independently grouped electronics-vs-household collection for Stage 1 and well-supported subtype data for Stage 2, with threshold selection on validation only. No architecture has been implemented or selected in Phase 8.
