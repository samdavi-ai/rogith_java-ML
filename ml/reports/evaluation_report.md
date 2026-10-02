# Candidate-v2 evaluation report

> **Rejected for deployment.** This is an offline experiment, not a production result.

Test set: 175 images (60 existing e-waste test examples + 115 negatives). Test images were not used for training or model selection.

| Metric | Candidate-v2 |
|---|---:|
| Accuracy | 92.5714% |
| Macro precision | 89.7549% |
| Macro recall | 90.8075% |
| Macro F1 | 89.8948% |
| Weighted F1 | 92.6063% |

## Per-class results

| Class | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| battery_waste | 0.846 | 0.733 | 0.786 | 15 |
| keyboard | 1.000 | 1.000 | 1.000 | 8 |
| light_bulb | 1.000 | 1.000 | 1.000 | 3 |
| mobile_phone | 0.727 | 0.667 | 0.696 | 12 |
| mouse | 1.000 | 1.000 | 1.000 | 6 |
| pcb | 0.727 | 1.000 | 0.842 | 16 |
| not_ewaste | 0.982 | 0.957 | 0.969 | 115 |

## Confusion matrix

Rows are actual labels; columns are predicted labels, in the class order shown.

```text
[11, 0, 0, 3, 0, 1, 0]
[0, 8, 0, 0, 0, 0, 0]
[0, 0, 3, 0, 0, 0, 0]
[1, 0, 0, 8, 0, 1, 2]
[0, 0, 0, 0, 6, 0, 0]
[0, 0, 0, 0, 0, 16, 0]
[1, 0, 0, 0, 0, 4, 110]
```

## Release decision

On the same 60 supported e-waste test images, production v1 scored 59/60 and candidate-v2 scored 52/60. Candidate-v2 also rejected the charger challenge as not e-waste. The candidate was not integrated into Java or deployed. The production model remains v1.
