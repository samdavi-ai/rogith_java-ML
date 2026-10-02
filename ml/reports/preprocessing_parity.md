# Preprocessing parity audit

Audit date: 2026-10-02. Candidate assessment remains blocked from release unless the checks below pass on the same image bytes.

| Operation | Python/Keras and ONNX export | Java ONNX serving | Assessment |
|---|---|---|---|
| Orientation | `prepare_dataset.py` / evaluation loader applies EXIF orientation before RGB decode | Upload decoding uses ImageIO; Java path receives a `BufferedImage` | Verify oriented inputs at the upload boundary; parity is not established for EXIF-tagged images |
| Resize | TensorFlow directory loader resizes to 224×224 with bilinear interpolation and stretches | `Graphics2D` bilinear interpolation to 224×224, no crop | Same dimensions and intent; resampling kernels/rounding may differ slightly |
| Color | RGB | Java `getRGB`, channel order R, G, B | Same intended order |
| Range / normalization | float32 `pixel / 127.5 - 1.0` | 8-bit RGB values converted to float and `value / 127.5f - 1.0f` | Same formula; float rounding may differ |
| Layout | NCHW | NCHW `[1,3,224,224]` | Match |
| Shape / dtype | `[N,3,224,224]`, float32 | `[1,3,224,224]`, float32 | Match |

Existing artifact-level check: Keras and ONNX logits agreed on all 60 baseline validation images, with maximum absolute difference `5.72e-05` (see `onnx_validation.json`). This verifies export parity for preprocessed tensors. It does **not** by itself prove Python-vs-Java image-resize parity or Java-vs-Python top-class and confidence agreement on identical source image files. Java end-to-end image parity has therefore not been certified for Phase 7B. Before promoting any candidate, add/run a shared-image integration comparison and resolve any differences, especially EXIF orientation and interpolation rounding.

Phase 8 added an actual Java-vs-Python ONNX check across all 60 existing test image files. Top-1 class agreement was 60/60, top-4 label agreement 237/240, maximum top-1 confidence delta 0.045159, and maximum top-4 delta 0.045443. The ≤0.02 parity assertion failed. See [`java_onnx_parity.md`](java_onnx_parity.md) for method and release consequence. No candidate is selected or released on the strength of tensor-level ONNX parity alone.
