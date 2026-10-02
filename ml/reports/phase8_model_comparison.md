# Phase 8 model comparison

No Phase 8 candidate was trained. The data gate stopped the workflow before training: no image-audited source provides adequate explicit charger/adapter labels, and the potential Bower external validation source has unresolved count/privacy/metadata checks. Existing measured candidates are included for comparison; Phase 7 candidate results are not represented as Phase 8 training.

| Test | Production v1.0.0 | Previous rejected negative-class candidate | Phase 8 V2 |
|---|---:|---:|---|
| Existing six-class test | 59/60, 98.33% accuracy; macro F1 98.76% | 52/60, 86.67% accuracy | Not trained |
| Candidate mixed 175-image suite | 33.71% accuracy (closed-set forced labels; not a valid production comparison on negative items) | 92.57% accuracy; macro F1 89.89% | Not trained |
| Bottle diagnostic crop | Mouse, 72.2% | not_ewaste, 99.95% | Not tested |
| Charger/adapter diagnostic crop | Light bulb, 70.7% | not_ewaste, 99.93% (false negative) | Not tested |
| Laptop/keyboard scene diagnostic crop | Keyboard, 86.4% | Keyboard, 55.1% | Not tested |
| Independent real-world category suite | Not available | Not available | Not available |

The previous candidate's 175-image score masks the regression in the existing supported e-waste test. Its class metrics, full confusion matrix and experiment context are in [`candidate_v2_evaluation.json`](candidate_v2_evaluation.json), [`model_comparison_v1_vs_candidate_v2.json`](model_comparison_v1_vs_candidate_v2.json), and [`docs/MODEL_IMPROVEMENT_REPORT.md`](../../docs/MODEL_IMPROVEMENT_REPORT.md). Per-class metrics for the production model are in [`evaluation.json`](evaluation.json). The three diagnostic crops do not form an accuracy cohort.

**Selection: production v1 remains.** No V2, V2-A/B/C, new ONNX artifact, class mapping, API response, UI, or deployment was created/changed.
