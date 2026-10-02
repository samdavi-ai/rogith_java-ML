# RecoLens Phase 11 final report

Audit date: 2026-10-03. Starting commit: `a7bb435821e6496adf7a22304b52c5630f427c53`.

## 1. Objective

Build evidence for a trustworthy, isolated V2 dataset and establish a physical-camera baseline without changing production V1. Phase 11 reviewed the original leakage candidates, built a local reblocked staging split, froze and reproduced V1, prepared a physical camera capture tool, and inspected deployment configuration. The real-camera collection gate remains unmet.

## 2. V1 baseline

V1 is frozen at `ml/models/ewaste.onnx`, SHA-256 `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`. The archived artifact at `ml/models/archive/recolens-v1-production.onnx` has the same hash. Its six-class ID order, 224×224 RGB NCHW input, bilinear stretch, normalization, ONNX shape/opsets, and 59/60 reproducibility are recorded in [V1_PRODUCTION_BASELINE.md](V1_PRODUCTION_BASELINE.md). Neither model file nor class mapping was changed.

The reproduced compatible test score is 59/60 = 98.33%. The one error is battery waste predicted as mobile phone (confidence 0.57193). Macro F1 is 98.76%; weighted F1 is 98.34%. This remains an existing lab split result, not camera performance.

## 3. Near-duplicate resolution

All 180 original cross-split dHash≤3 candidates were compared visually in 15 contact sheets; pair decisions, rationale, actions and both file hashes are in [NEAR_DUPLICATE_REVIEW.md](NEAR_DUPLICATE_REVIEW.md) and its CSV inventory. There are 179 `NEAR_DUPLICATE`, one `LEGITIMATE`, zero byte-identical `DUPLICATE` decisions, and zero pair decisions marked `UNKNOWN`. The legitimate pair shows two distinct battery products against the same green background. The other pairs show the same apparent item/view or scene with adjacent capture-sequence filenames. The source has no object IDs or capture-burst metadata, so inspection cannot prove physical identity or whether a frame is the same original capture. The rebuild therefore groups every dHash≤3 edge, including the legitimate pair, rather than discarding images.

## 4. Leakage analysis

The original rejected tree still fails the automated check with 180 cross-split candidates: `ml/.venv/bin/python ml/scripts/audit_split_leakage.py --data ml/data/candidates/reject_v2 --source-audit ml/reports/dataset_audit.json --out /tmp/phase11_original_split_audit.json`.

A separate ignored local staging tree `ml/data/candidates/phase11_reblocked` was created by unioning filename families, exact hashes, and all dHash≤3 relationships. It retains 1,139 images (991 train, 73 validation, 75 test). The audit command above, pointed at this tree and writing `ml/reports/phase11_reblocked_split_audit.json`, passes: zero corruption/small files, exact duplicates, filename-family crossings, or cross-split dHash candidates. It reports zero newly linked cross-split candidates; the source-audit reference still records 544 broader source-archive edges. Eight mixed-label components (8 files) and 29 manually held ambiguous images were quarantined; the hold manifest is [phase11_label_holds.csv](phase11_label_holds.csv), and all 37 quarantined files are listed in [phase11_quarantine_manifest.csv](phase11_quarantine_manifest.csv). The script fails with status 1 when its checked split has leakage. The clean staging result is not a final dataset: its source remains rejected, labels/negative semantics require further review, and it must not be treated as permission to train.

## 5. Dataset taxonomy

The production class map remains the six V1 labels: battery waste, keyboard, light bulb, mobile phone, mouse and PCB. The new seven-label candidate mapping is not adopted. [Taxonomy decision](PHASE_11_TAXONOMY.md) groups charger, adapter, cable and external power supply as a proposed future `electronic_accessory` category pending sufficient data; laptops, monitors and tablets need distinct whole-object data before any addition. `unknown` is an abstention concept, separate from known `non_ewaste`. The derived negative class is not yet adequate: 15 plastic-labelled examples looked electronic or ambiguous and were held as unknown.

## 6. Dataset sources

No new external images were acquired in Phase 11. The rejected candidate tree carries forward Phase 10's Roboflow e-waste version 5 source, whose embedded data card declares CC BY 4.0 and whose Mendeley record/attribution are recorded in [DATASET_SOURCES_FINAL.md](../DATASET_SOURCES_FINAL.md). The existing 1,468 files include transformed and derived labels; that declared license does not establish correct per-file labels, source identity, or suitability for another training run. Other source candidates were not acquired for this phase.

## 7. Licensing

The Phase 10 source register documents declared licenses, attribution, modifications, and candidates excluded for unclear or non-commercial rights. No new licensing claims are made. The original per-image creator/source manifest is unavailable for the candidate export; therefore provenance granularity remains a limitation even though the dataset-level declaration is CC BY 4.0.

## 8. Real-world camera collection

The official set has **0 accepted physical camera images**. `ml/data/recolens_real_world_test_manifest.csv` is header-only. There is no locked manifest, dataset hash, or training use of this set. Three screenshot crops remain diagnostic-only, excluded from the camera cohort and all official camera metrics. The local capture helper is [real_world_capture.html](../tools/real_world_capture.html); the collection and locking requirements are in [REAL_WORLD_TEST_PROTOCOL.md](../REAL_WORLD_TEST_PROTOCOL.md). Actual images still need human label/PII review and a locked manifest.

Required supported and challenge category coverage currently stands at zero:

| Requested category | Accepted camera images | Status |
|---|---:|---|
| battery, keyboard, light bulb, mobile phone, mouse, PCB | 0 each | BLOCKED |
| charger, adapter, laptop | 0 each | BLOCKED |
| water bottle, book, paper, clothing, food, plastic object, glass object | 0 each | BLOCKED |

## 9. Device coverage

No actual camera frame was collected from an iPhone, Android phone, desktop webcam, or laptop webcam. Device, browser, camera, resolution, and capture date coverage are all **0 / not tested**.

## 10. Lighting coverage

No physical camera set exists for normal indoor, bright, or low-light scenes. All lighting coverage is **0 / not tested**. Background, front/side/angled position, close/medium distance, and orientation/partial-visibility coverage are likewise **0 / not tested**.

## 11. V1 real-world results

Overall and per-class real-world precision/recall/F1, macro F1, confusion matrix, and false e-waste rate are **NOT TESTED** because there are no accepted images. See [V1_REAL_WORLD_ERROR_ANALYSIS.md](V1_REAL_WORLD_ERROR_ANALYSIS.md). No source-split or screenshot-pilot metric is substituted for a camera score.

## 12. V1 real-world error analysis

There are no camera error examples to report. The single 59/60 lab error is documented separately and must not be described as a real-world miss. The candidate V2's old derived-negative false e-waste rate (5/115 = 4.35%) remains a source-split diagnostic, not an actual household-camera rate.

## 13. V2 training decision

No Phase 11 V2 model was trained. The data gate fails because no physical-camera cohort exists and the rejected source/labels do not yet support the proposed taxonomy. The clean reblocked staging split only resolves within-tree split overlap for experimentation.

## 14. V2 results

No new V2 results exist. The pre-existing rejected candidate is not relabeled as a Phase 11 model and was not deployed.

## 15. V1 vs V2 comparison

The inherited same-60 regression remains V1 59/60 (98.33%) versus candidate V2 52/60 (86.67%). Candidate V2 was 92.57% on its old mixed source test, but that diagnostic result is not a final independent evaluation. See [V1_VS_V2_COMPARISON.md](V1_VS_V2_COMPARISON.md). No current locked real-world or new V2 comparison is available.

## 16. Java/Python parity

Historical V1 Python/ONNX checks reproduce on the same 60 images (60/60 argmax agreement; maximum logit absolute difference 6.48499e-5, probability difference 7.24196e-6). No V2 was trained, so final-V2 Python ONNX versus Java parity is **NOT TESTED** and no V2 parity claim is made.

## 17. Spring Boot integration

The source exposes `POST /api/classifications` as multipart field `image` and returns an envelope with `data.classification` fields including `status`, `categoryName`, `confidence`, `confidenceLevel`, `alternatives`, and `guide`. The service loads the ONNX model and class map from configured paths. The hosted V1 `POST /api/classifications` returned HTTP 200 for a multipart `image` request and the expected envelope/status/confidence fields. The smoke fixture was the existing diagnostic bottle screenshot crop (not an accepted camera image); V1 classified it as Mouse at confidence 0.8060. This is one diagnostic prediction, not an official real-world metric. No V2 serving-model change or camera-frame capture test was made.

## 18. Frontend integration

The frontend build writes the configured HTTPS API base URL into `api-config.js`; the Render blueprint points it to the API service. Source inspection confirms selecting an existing image uses a file input and the camera has a separate explicit start-camera flow; choosing upload does not automatically request camera access. The static homepage returned HTTP 200. The production API accepted the multipart upload smoke fixture as described above. The browser UI flow and a live physical-camera permission/capture flow were not exercised in this audit; no V2 was integrated.

## 19. Render architecture and production verification

`render.yaml` defines three components: the static `recolens` frontend, the Docker Spring service `rogith-ewaste-api`, and PostgreSQL `rogith-ewaste-db`. The static frontend is at `https://recolens-h55g.onrender.com`; it calls `https://rogith-ewaste-api.onrender.com`. The backend gets the ONNX model and class map from its container at `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`, uses the configured Render PostgreSQL datasource and initializes `schema.sql`; classification history is not persisted server-side, and the current source has no classification repository. The frontend saves classification history in browser `localStorage`; Spring source explicitly says personal history is not persisted server-side.

The previously observed `/health` HTTP 404 at the static frontend URL is explained by this split-service architecture: the health controller exists in the Spring API and the static host does not serve it. The static homepage returned HTTP 200. At the correct API host, `/health` returned HTTP 200 with `status=UP`, `modelStatus=MODEL_READY`, and `modelLoadTimeMs=3196`. CORS OPTIONS for the deployed frontend origin returned HTTP 200 and the expected allow-origin/method/header values. Multipart classification also returned HTTP 200. The service does not expose a model hash, so the currently hosted artifact identity is **NOT CONFIRMED**. No endpoint was added and no deployment was made.

## 20. Remaining blockers

- Collect and review actual physical camera images across requested classes/devices/conditions; freeze their manifest and dataset hash.
- Establish adequate independent objects for each proposed production class and diverse hard negatives; resolve all ambiguous labels.
- Preserve source/license provenance at image-level where available and document any new source terms.
- Build a final, identity-grouped train/validation/test version; the local candidate staging split is not the final V2 dataset.
- After data gates pass, train a fresh, documented V2; evaluate on independent locked sets; require the compatible-class regression gate and candidate new-class metrics.
- If V2 is trained, export ONNX and pass exact-fixture Python/Java parity before any staging integration.
- Confirm hosted backend health, model readiness, CORS, classification, and production model identity from a responsive API endpoint.

## 21. Final decision

**V2 TRAINING BLOCKED**
