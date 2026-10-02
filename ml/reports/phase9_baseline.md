# Phase 9 production V1 baseline

Audit date: 2026-10-02. Repository HEAD at audit start: `b45c6ccc01a24e8533dd8e03d3124bfc75488618`; requested Phase 8 reference: `2b06074`.

The active production model file in this checkout is `ml/models/ewaste.onnx`. The pasted path `models/recolens-v1-production.onnx` is not present here; its archived counterpart is `ml/models/archive/recolens-v1-production.onnx`.

| Artifact | SHA-256 |
|---|---|
| `ml/models/ewaste.onnx` (active) | `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5` |
| `ml/models/archive/recolens-v1-production.onnx` | `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5` |

The hashes match. V1 has six classes: battery, keyboard, light bulb, phone, mouse, and PCB. Its retained evaluation baseline is 59/60 (accuracy 0.98333; macro precision 0.98718; macro recall 0.98889; macro F1 0.98759). This is the existing split, which has unresolved near-duplicate cross-split candidates; treat it as a regression reference, not a clean independent estimate.

No model file was modified, no V2 model was trained, and no deployment was made during Phase 9.
