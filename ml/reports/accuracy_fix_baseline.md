# Phase 7B accuracy-fix baseline

Audit date: 2026-10-02. Production artifact was preserved before any Phase 7B experiment as `ml/models/archive/recolens-v1-production.onnx` (SHA-256 `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`, 8,943,137 bytes). It is byte-identical to `ml/models/ewaste.onnx` at audit time.

## Production model

| Property | Baseline |
|---|---|
| Model version | 1.0.0 |
| Architecture | ImageNet-pretrained MobileNetV2, global average pooling, dropout 0.25, dense six-logit head; last 20 backbone layers fine-tuned, batch normalization frozen |
| Classes, in output order | battery_waste, keyboard, light_bulb, mobile_phone, mouse, pcb |
| Training source | Custom Bangladeshi E-Waste Image Dataset, Mendeley Data V1, CC BY 4.0; selected six classes |
| Evaluation | Existing held-out six-class split: 60 images; 59 correct |
| Test metrics | Accuracy 0.9833; macro precision 0.9872; macro recall 0.9889; macro F1 0.9876; weighted F1 0.9834 |
| ONNX | Opset 17; input `image`, float32 `[N,3,224,224]`; six logits |
| Inference preprocessing | EXIF-oriented RGB image; bilinear stretch to 224×224; RGB channels; `pixel/127.5 - 1.0`; float32 NCHW |
| Serving | Java ONNX Runtime 1.20.0; minimum confidence 0.66; below threshold returns `UNSURE` |

Per-class test support / precision / recall / F1 from the committed evaluation: battery 15 / 1.000 / 0.933 / 0.966; keyboard 8 / 1.000 / 1.000 / 1.000; bulb 3 / 1.000 / 1.000 / 1.000; phone 12 / 0.923 / 1.000 / 0.960; mouse 6 / 1.000 / 1.000 / 1.000; PCB 16 / 1.000 / 1.000 / 1.000. Small supports, especially three bulbs, make these estimates uncertain. The lone error is a battery predicted as phone at 0.520 confidence.

## Accuracy failures and evidence

The model is a closed-set classifier: its output mapping contains only those six classes. A water bottle therefore gets a forced e-waste label unless the confidence floor rejects it; charger and laptop are also absent from training labels. The supplied screenshot results were bottle→mouse (76.6%), charger/adapter→bulb (~82.6%), and laptop-with-keyboard-visible→keyboard (74.4%). Local screenshot-crop replay reproduced the same labels, with confidence 72.2%, 70.7%, and 86.4%. These cases show taxonomy and distribution gaps; they do not establish a single internal visual cause.

The previous seven-class negative-class candidate is preserved as a rejected experiment. On the existing six-class test subset it dropped from 59/60 correct to 52/60, and its adapter crop returned `not_ewaste`; it also called the laptop scene keyboard (0.551). Although it classified a bottle crop as `not_ewaste` (0.9995), that three-image challenge set is qualitative and cannot compensate for the six-class regression. Do not deploy that model.

## Phase 7B release status

No expanded-class production candidate is supported by the currently audited, downloaded, licensed data. The Mendeley source has no charger, laptop, monitor, headphone, or cable class. A promising GIZ dataset is CC BY 4.0 and documents Ghana scrapyard photos, but its available labels are ACs, Compressors, Computers, Fridges, Laptops, Microwave, TV, and unsure; it has no charger class and its dataset viewer currently fails. Its large object-detection archive still requires curation, grouping, and crop-level label auditing before use. Public Roboflow pages likewise indicate possible classes, but a page-level count is not proof of an accessible, auditable image archive; no unverified page totals are counted as training data.

The current production model remains the release choice. No changes have been made to its weights, ONNX file, class mapping, Java serving path, or deployed Render service. Further model training is deferred until a licensed source with auditable images supports the expanded taxonomy and a sufficiently broad, locked real-camera test set is available. This is an evidence-based no-deploy decision, not a claim that the problem is fixed.
