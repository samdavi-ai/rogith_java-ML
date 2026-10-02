# RecoLens release gate — Phase 10

Audit date: 2026-10-02. Required values use PASS, FAIL, BLOCKED or NOT TESTED.

| Gate | Status | Evidence |
|---|---|---|
| DATASET READY? | **FAIL** | Existing candidate split has 180 cross-split dHash≤3 candidates; zero corrupt/exact duplicate files and no filename-family crossing. New class data and real-world cohort are absent; details in [V2_DATASET_FINAL_REPORT.md](V2_DATASET_FINAL_REPORT.md). |
| PARITY READY? | **PASS** (V1 only) | Reproduced Phase 9 Java/Python ONNX parity on 60 images and PNG/EXIF probes using JDK 17; top-1/top-3/top-5 agree. Candidate V2 Java parity is NOT TESTED. |
| V2 MODEL READY? | **BLOCKED** | A seven-class MobileNetV2 candidate artifact exists from prior work, but its split fails the leakage gate and it reduces the compatible six-class V1 test from 59/60 to 52/60. Candidate V2 is not a release model. |
| REAL-WORLD TEST READY? | **FAIL** | Official manifest is empty; accepted actual camera images: 0. Three diagnostic screenshot crops are not a representative camera test set. |
| REGRESSION PASS? | **FAIL** | On the same 60 existing-class test examples: V1 is 59/60 (98.33%); candidate V2 is 52/60 (86.67%), a decrease of 7/60 (11.67 percentage points). |
| PRODUCTION READY? | **FAIL** | Dataset, real-world and regression gates fail; candidate V2 Java/API/frontend and deployed smoke checks are not complete. Production homepage responds HTTP 200, but `GET /health` returns HTTP 404, so production model/API health is not confirmed. No deployment was made. |

## Current production artifact

The local active V1 artifact `ml/models/ewaste.onnx` and archive `ml/models/archive/recolens-v1-production.onnx` have identical SHA-256 `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`. The local active file was not changed. The live HTTP checks do not establish which model, if any, is currently loaded by the hosted API.

## Decision

**V2 NOT APPROVED. V2 TRAINING = BLOCKED. DO NOT DEPLOY.** Preserve V1 while obtaining licensed and audited data, resolving split-related near duplicates, collecting and locking actual RecoLens camera images, and fixing the candidate's measured supported-class regression. Re-run candidate V2 Java inference and the production smoke suite only after those gates pass.
