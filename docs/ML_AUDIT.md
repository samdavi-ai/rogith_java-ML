# RecoLens ML audit

Audit date: 2026-10-02. This records the checked-in production model (`v1.0.0`) and the separate rejected experiment (`candidate-v2`). Source evidence is in `ml/`, including `class_mapping.json`, the training/evaluation scripts, model metadata, reports, and the Java ONNX service.

| Component | Current implementation | Status |
|---|---|---|
| Dataset | Roboflow Universe `e-waste-uvzkj` v5 export in the local workspace, corresponding to the documented Custom Bangladeshi E-Waste dataset; archive `data.yaml` declares CC BY 4.0. Source audit: 2,157 images / 12 labels. | Audited locally; archive/raw images are ignored by Git. |
| Classes | Six outputs in `ml/class_mapping.json`: battery_waste, keyboard, light_bulb, mobile_phone, mouse, pcb. There is no laptop, charger, monitor, or unknown class in v1. | Confirmed; this is a closed-set classifier. |
| Class balance | Curated v1 split: 523 train / 60 validation / 60 test. Light bulb has 31/3/3; Mouse 47/11/6. | Uneven and small held-out supports. |
| Training | ImageNet MobileNetV2, global average pooling, dropout 0.25, dense logits. v1 was frozen-backbone then last-20-layer fine-tuning; the retraining script now adds mild random flip/rotation/zoom/translation/contrast augmentation during training. | v1 artifact remains unchanged; augmentation was used in candidate-v2 only. |
| Validation | Validation loss drives checkpoint selection; six-class validation has 60 images. | Used for model selection, not the final v1 test. Small sample. |
| Test set | Grouped selected-class split with 60 examples for v1. Candidate negative examples preserve source train/valid/test partition; candidate test has 175 examples. | No test examples used in fitting/checkpoint selection. Object identity is not available. |
| Preprocessing | RGB; bilinear stretch resize 224×224; float32 `pixel / 127.5 - 1`; NCHW model input. | Training and Keras/Python ONNX parity verified. Java pixel-by-pixel parity was not measured in this phase. |
| Augmentation | v1 training run predates augmentation in the script. Candidate uses mild horizontal flip, rotation 0.04, zoom 0.08, translation 0.04 and contrast 0.12. | Candidate parameters logged in code; exact augmentation is training-only. |
| Model | TensorFlow/Keras MobileNetV2, ImageNet initialization, six v1 logits. | v1 is deployed. Seven-class candidate failed e-waste recall regression gate. |
| Export | v1 ONNX opset 17, six logits. Candidate ONNX opset 17, seven logits. | Candidate export and Python ONNX parity passed; not integrated into Java. |
| ONNX inference | Java ONNX Runtime 1.20.0 session loads model and class map, softmaxes logits. | Production v1 integration exists. Candidate Java integration not attempted because offline evaluation failed. |
| Label mapping | Java and Python read ordered `ml/class_mapping.json`; IDs are contiguous. | v1 verified. Candidate has an isolated generated seven-class map. |
| Confidence | Softmax maximum; production API confidence floor 0.66 yields `UNSURE` below threshold. | Not a calibrated probability. High-confidence wrong predictions are documented. |

## Screenshot error analysis

Three user-provided phone-camera screenshots are treated as qualitative, evaluation-only examples. They were not used for training, augmentation, validation, or checkpoint selection. Replaying crops through v1 with the repository preprocessing gives: bottle → Mouse (72.2%), laptop scene → Keyboard (86.4%), adapter → Light bulb (70.7%). These values differ from the displayed screenshot probabilities because only compressed, displayed image crops were available. Case labels and SHA-256 hashes are recorded in [`ml/tests/fixtures/real_world_challenges/manifest.json`](../ml/tests/fixtures/real_world_challenges/manifest.json); the personal image crops are local-only and ignored by Git.

The most directly supported causes are taxonomy gaps and forced closed-set prediction: laptop and charger are not output classes, and v1 has no negative/unknown class. The bottle is also outside the trained target taxonomy. General-waste imagery, camera lighting/background differences, and small per-class datasets make domain shift plausible. No evidence from these examples alone proves a specific background bias or image-label error. Recorded v1 Keras/ONNX parity is strong; Java preprocessing parity remains unverified, so preprocessing mismatch cannot be ruled out as a production-specific factor.

## Candidate-v2 outcome

An isolated seven-class candidate added a `not_ewaste` class using Plastic, Paper, Glass, and Organic waste images from their original source partitions. Metal and Medical were excluded because those labels may include electronics. Candidate training used 597 negatives; validation used 113; final test used 115. Candidate test combined those 115 negatives with the unchanged 60 selected e-waste test examples. The candidate improved bottle handling, but reduced six-class e-waste test accuracy from 59/60 (98.3%) to 52/60 (86.7%); it also called the charger screenshot not-e-waste at 99.9%. Candidate-v2 is therefore rejected for deployment. Details and metrics: `MODEL_IMPROVEMENT_REPORT.md` and `ml/reports/`.
