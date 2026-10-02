# RecoLens Phase 9 final report

Audit date: 2026-10-02  
Final decision: **NOT READY FOR V2 TRAINING OR PRODUCTION**

## 1. Phase 8 baseline and production V1

Phase 8 ended with production V1 unchanged and not deployed. The reported evaluation was 59/60. Its Java/Python check had top-1 agreement 60/60, top-4 rank-position agreement 237/240, and a maximum reported probability difference of 0.045443; the parity assertion failed.

The active model in this checkout is `ml/models/ewaste.onnx`; the archived model is `ml/models/archive/recolens-v1-production.onnx`. Both SHA-256 hashes are `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`. The path `models/recolens-v1-production.onnx` in the request is not present in this checkout. Full evidence is in [phase9_baseline.md](phase9_baseline.md).

The retained V1 evaluation is 59/60 (accuracy 0.98333; macro precision 0.98718; macro recall 0.98889; macro F1 0.98759). The prepared split has 643 images (523 train, 60 validation, 60 test), but near-duplicate candidates cross its splits. Keep these metrics as a regression reference, not as a clean independent performance estimate.

## 2. Java/Python/ONNX parity investigation and exact old mismatches

The complete preprocessing contract and per-image old output lists are documented in [java_onnx_parity_v2.md](java_onnx_parity_v2.md). The three Phase 8 top-4-affected images are:

1. `IMG_20250822_231153_1_jpg.rf.055d65f1f0714e9fda6d890f79bc15ab.jpg`: top-4 set agrees, but ranks 4 and 5 swap. Python probabilities: Battery waste .999981761, Light bulb .000010084, Mouse .000004081, PCB .000001902, Mobile phone .000001750. Java: Battery waste .999983668, Light bulb .000008801, Mouse .000004023, Mobile phone .000001691, PCB .000001437.
2. `IMG_20250822_231221_1_jpg.rf.187ee67700b833c74c2c876f9f8165c7.jpg`: ranks 4 and 5 swap. Python: Battery waste .999896049, Mobile phone .000070135, Light bulb .000029188, PCB .000002249, Mouse .000002106. Java: Battery waste .999898946, Mobile phone .000066552, Light bulb .000030450, Mouse .000002022, PCB .000001800.
3. `IMG_20250819_235956_1_jpg.rf.13c8f40791f750605aa42a1d3e903da9.jpg`: ranks 2 and 3 swap. Python: PCB .999135077, Mobile phone .000410283, Keyboard .000402244, Battery waste .000049412, Mouse .000002266. Java: PCB .999011665, Keyboard .000466556, Mobile phone .000460810, Battery waste .000057663, Mouse .000002480.

There was also a rank-5-only mismatch on `IMG_20250822_140413_jpg.rf.73cf4af821a990defde96ed1db5c0d92.jpg`: Python ranked Light bulb fifth at .000008106; Java ranked Battery waste fifth at .000008349. The exact replay gives 236/240 top-4 rank-position matches and 293/300 top-5 rank-position matches. The Phase 8 report's 237/240 scoring definition was not saved; replay finds the same three affected examples, with one pairwise swap contributing two changed rank positions.

The historical maximum top-1 confidence difference was 0.045158911. The maximum top-4 rank probability difference was 0.045443077. Both occur for `IMG_20250803_215701_jpg.rf.352a524931e1295dac040a7f6381d4f1.jpg`. Python top probabilities were Mobile phone .520296812 and Battery waste .477712840; Java produced .565455723 and .432269763. This difference arose primarily from preprocessing. TensorFlow's generic image decoder used its faster JPEG path while Java ImageIO matched `INTEGER_ACCURATE`; decoded channels differed by up to 5/255. Java Graphics2D then rounded resized values through uint8 while Python retained float32. The replay measured a max normalized tensor difference of .03613245. Class mapping and softmax were not the cause.

## 3. Fix, fixture, and parity gate

The Python training loader now explicitly decodes JPEG using `INTEGER_ACCURATE` (and PNG as three-channel RGB). Java now performs float32 bilinear stretch resizing directly rather than rounding through an 8-bit image. Both paths use RGB, 224×224, no crop/padding, `pixel / 127.5 - 1`, NCHW `[1,3,224,224]`. Class order is checked against the model mapping. Java applies stable double-precision softmax.

The deterministic 60-image reference fixture, tensor/output references, generator and usage notes live in [`ml/parity/`](../parity/README.md). It also checks RGBA PNG alpha handling and JPEG EXIF orientation. The supported test runtime was OpenJDK 17.0.20.1 with ONNX Runtime 1.20.0; TensorFlow was 2.17.0.

Current cross-runtime measurements: decoded RGB hashes agree 60/60; tensor maximum/mean absolute difference `8.60691e-5 / 3.20378e-7`; logits `7.73072e-5 / 1.51503e-5`; probability `2.19728e-5 / 2.80507e-7`; top-1 confidence `2.19728e-5 / 8.37332e-7`. Top-1, top-3 and top-5 rankings agree on all 60 images. PNG/EXIF probes match decoded pixels 2/2, with maximum tensor difference `6.06775e-5`.

Release gate justified from these observed CPU runtime differences: exact decoded RGB hashes; tensor and logit max absolute error at most `1e-4`; probability max absolute error at most `3e-5`; identical top-1, top-3 and top-5 rankings. The measured fixture passes each bound. The explicit parity test and complete Maven suite passed with JDK 17 selected explicitly. Historical mismatches remain documented above; current fixed-path comparisons pass.

## 4. Dataset research, licensing, and quality

Source-level research is summarized in [DATASET_CANDIDATES.md](../DATASET_CANDIDATES.md). The current Mendeley source is CC BY 4.0 and has 2,157 raw images across 12 source labels; it supports the existing six-class V1 subset but has no charger, laptop, monitor, cable, or headphone labels. The V1 prepared data has 643 images and zero corrupt files, exact-duplicate groups, or labels outside the six supported classes.

New listings do not pass image-level acceptance. GIZ publishes CC BY 4.0 detection data and laptop/computer labels but was not acquired or audited and has no charger label. Roboflow's listing displays CC BY 4.0 and includes adapter/charger/laptop labels, but has zero dataset versions and no per-label counts. Kaggle's reported charger/laptop dataset has no verified license or file-level class counts. TrashBox has broad e-waste labels without a license statement on the inspected page. TrashNet++ claims CC BY 4.0 but lacks verified subtype counts and provenance. MMEWaste and XBAT+ show no license; MMEWaste says the full data are confidential. Bower is MIT and useful as a possible broad negative/validation source, but the card says validation-only, reports different image counts than the downloaded file audit, and needs image privacy/provenance review. No candidate was counted as accepted V2 data.

### Near-duplicate and split review

The raw source audit identified 544 cross-split dHash candidate pairs. The corrected preparation/audit logic now compares variants across all filename families and builds same-class near-duplicate components before splitting. The current prepared V1 split audit found 23 cross-split same-label candidates at dHash distance 0–3 (4 at 0, 2 at 1, 7 at 2, 10 at 3). All were visually reviewed as the same object or very similar scene, so this split fails the no-leakage gate. Evidence and review notes: [phase9_split_leakage_audit.json](phase9_split_leakage_audit.json).

A temporary corrected re-split was generated outside the repository and not adopted: 643 images, train 513, validation 60, test 70, no corruption/exact duplicates/family leakage, but three cross-class near-duplicate pairs remain. They show the same mixed battery/PCB scene assigned conflicting labels. This is a label and data quality blocker. The prior production evaluation split was not overwritten.

## 5. Missing-class readiness

| Requested group | Accepted usable images | Train / validation / test | Decision |
|---|---:|---:|---|
| Charger / adapter | 0 | 0 / 0 / 0 | Blocked: no acquired, licensed, audited source with enough independent splits |
| Whole laptop | 0 | 0 / 0 / 0 | Blocked: GIZ is only a research lead; laptop-component data do not represent whole devices |
| Monitor, cable, earphones, headphones, other electronic device | 0 | 0 / 0 / 0 | Blocked: candidate labels are unverified or too broad; no accepted images |
| Representative non-e-waste | 0 | 0 / 0 / 0 | Blocked: no locked, audited collection covering realistic household negatives |
| Existing six V1 classes | 643 in prepared V1 data | 523 / 60 / 60 | Regression baseline only; split has unresolved near-duplicate leakage |

The required real-world scenarios (bright/normal/low light, plain/cluttered backgrounds, distance and angles) are not represented by a verified camera cohort. Three old screenshot crops are retained only in a diagnostic pilot manifest; they are not camera captures, their metadata is incomplete, and they are excluded from the official set.

## 6. Locked real-world test set

`ml/data/recolens_real_world_test/` contains zero accepted images. `ml/data/recolens_real_world_test_manifest.csv` is a header-only schema with `image_id,true_class,source,capture_condition,hash,relative_path`. The three diagnostic crops and hashes are listed separately in `ml/data/recolens_real_world_test/pilot_manifest.csv`. Since there are no qualifying camera examples, there is no locked test set or camera performance metric.

## 7. V2 training, metrics, and blockers

**V2 NOT TRAINED.** The data gate fails: charger/adapter has zero accepted samples and no independent train/validation/test sets; new classes lack verified labels and splits; no representative non-e-waste cohort exists; the real-world camera set is empty; and the current six-class split has unresolved near-duplicate and cross-label scene issues. No V2 metrics, architecture comparison, unknown threshold, or deployment evaluation is claimed.

The 59/60 V1 result remains the regression baseline. Any future V2 needs independently sourced, licensed, audited per-class data, a leakage-clean split, a representative locked real-world test set, and class-wise plus existing-class regression metrics before training can be considered. Deployment remains a separate gate.

## 8. Final status

- **Parity:** PASS on the fixed 60-image fixture and two preprocessing probes. Top-1 60/60; top-3 60/60; top-5 60/60. Maximum top-1 confidence difference `2.19728e-5`; mean `8.37332e-7`.
- **Data:** FAIL. Accepted new-class training/validation/test images: 0 / 0 / 0. Official real-world images: 0. Existing V1 prepared data: 523 / 60 / 60, held as a regression baseline with split-leakage concerns.
- **Model:** V2 not trained because required data and clean-split gates failed.
- **Production:** V1 unchanged; active and archived model hashes match at `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`. Deployment: not performed.
- **Readiness:** **NOT READY** for V2 training or production.
