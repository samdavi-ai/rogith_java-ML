# V1 vs candidate V2 comparison — Phase 10

The checkout already contains a rejected seven-output candidate V2 artifact. No model was trained in Phase 10. This comparison uses the existing `model_comparison_v1_vs_candidate_v2.json` outputs; its test set is not locked and has unresolved train/validation/test dHash candidates.

## Compatible existing-class evaluation

Both models were evaluated on the same 60 images from the six existing classes. This is the compatible slice for supported-class regression:

| Metric | V1 | Candidate V2 |
|---|---:|---:|
| Accuracy | 59/60 (98.33%) | 52/60 (86.67%) |
| Macro Precision | 98.72% | 92.21% |
| Macro Recall | 98.89% | 90.00% |
| Macro F1 | 98.76% | 90.86% |
| Real-world accuracy | Not tested | Not tested |
| False e-waste rate | 115/115 = 100% on the candidate source-test negatives (closed-set model; expected limitation) | 5/115 = 4.35% on those same source-test negatives |

Candidate V2 is lower by seven correct predictions on this same supported-class slice (11.67 percentage points). **Regression gate: FAIL.**

## Candidate's full mixed source test

The candidate's full test set has 175 images, including 60 existing e-waste class images and 115 derived negatives. Candidate V2 accuracy is 92.57%, macro precision 89.75%, macro recall 90.81%, macro F1 89.89%, weighted precision 93.14%, weighted recall 92.57%, weighted F1 92.61%. Its non-e-waste metrics are precision 98.21%, recall 95.65%, F1 96.92%, with 5/115 false e-waste predictions (4.35%).

V1's full-suite accuracy of 33.71% is not a meaningful model comparison: V1 has six e-waste outputs and necessarily assigns every negative image to an e-waste class. Compare V1 and candidate on the 60 compatible positive examples above for regression. The 115 negative examples show candidate behavior only, and are not independent real-camera negatives.

The candidate evaluation report records overall confusion matrix rows (true classes, in order Battery, Keyboard, Light bulb, Mobile, Mouse, PCB, Not e-waste):

```text
[[11,0,0,3,0,1,0],
 [0,8,0,0,0,0,0],
 [0,0,3,0,0,0,0],
 [1,0,0,8,0,1,2],
 [0,0,0,0,6,0,0],
 [0,0,0,0,0,16,0],
 [1,0,0,0,0,4,110]]
```

No real-world camera result, top-3 result, unknown-object result, Java candidate inference, or production API result is available. Keep V1; do not approve candidate V2.
