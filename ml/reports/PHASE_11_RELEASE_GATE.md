# RecoLens release gate — Phase 11

| Gate | Status | Evidence |
|---|---|---|
| V1 artifact freeze | PASS | Active ONNX and archived production V1 hashes match; see [V1 baseline](V1_PRODUCTION_BASELINE.md). |
| Reviewed original 180 pairs | PASS | 179 visually near-duplicate families and one visibly legitimate pair documented in [review inventory](NEAR_DUPLICATE_REVIEW.md). Source object/burst metadata are absent, so the rebuilt staging split groups all links conservatively. |
| Reblocked staging split | PASS (staging only) | Automated audit: 1,139 files; zero corruption, exact duplicate groups, filename-family crossings, and cross-split dHash≤3 candidates. Source archive itself still contains 544 such edges. The staging split comes from a rejected source and is not a final training dataset. |
| Real-world camera set | FAIL | 0 accepted images; no locked manifest or dataset hash. |
| Taxonomy and source audit | FAIL | V1 labels frozen; proposed classes lack adequate object-independent data. Existing derived negative set has ambiguous labels. Dataset source/license declarations are documented, but they do not resolve data adequacy. |
| V1 camera diagnostic | BLOCKED | No eligible camera images; no real-world metrics or error cases. |
| Candidate V2 existing-class regression | FAIL | Previously reported candidate scores 52/60 versus V1 59/60. No new training performed. |
| Candidate V2 Java parity | NOT TESTED | No Phase 11 V2 model was trained/exported. Historical parity evidence is V1 only. |
| Hosted V1 production verification | PASS (service smoke; model identity partial) | Static homepage HTTP 200; API `/health` HTTP 200 with `MODEL_READY`; CORS preflight HTTP 200; multipart classification HTTP 200. Model hash is not exposed. One diagnostic screenshot crop returned Mouse at 0.806 confidence; it is not camera-set evidence. |

## Decision

**V2 TRAINING BLOCKED**. Keep production V1 unchanged. Do not train or deploy until an adequate, licensed, leakage-controlled training/evaluation corpus and a separate locked physical-camera test set exist, and the other release gates pass.
