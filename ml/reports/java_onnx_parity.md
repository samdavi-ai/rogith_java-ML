# Java / Python ONNX parity — Phase 8 baseline check

Date: 2026-10-02. Environment: Homebrew OpenJDK 17.0.20.1, ONNX Runtime Java 1.20.0; Python ONNX Runtime from `ml/.venv`.

The automated comparison uses the same 60 local held-out image files in both runtimes. Python uses the repository's exact `image_dataset_from_directory` decode/resize/normalization path and runs the production ONNX file. Java reads the identical bytes with ImageIO, applies its 224×224 Graphics2D bilinear resize and RGB `pixel/127.5 - 1` normalization, then runs ONNX Runtime. Top four categories and probabilities are compared; this test is deliberately separate from Keras-vs-ONNX tensor parity.

## Result: FAIL / release-blocking

- Top-1 class agreement: **60/60**.
- Top-4 category agreement: **237/240 (98.75%)**; three lower-rank labels differ across three examples.
- Maximum top-1 confidence difference: **0.045159** (4.52 percentage points).
- Maximum top-4 confidence difference: **0.045443**.
- Four top-4 probability values exceed the chosen parity test's 0.02 diagnostic tolerance.
- Baseline Python Keras-to-ONNX tensor parity remains 60/60 with maximum logit difference `5.72e-05` (separate check in `onnx_validation.json`).

The observed top-1 categories agree, but numerical confidence and lower-ranked alternatives do not meet the parity assertion. The largest deviation is on a low-margin battery image. The mismatch may come from image decoding/resizing (TensorFlow decode/resize versus Java ImageIO/Graphics2D); that is a hypothesis until pixel tensors are compared directly. Do not hide this result by loosening thresholds or confidence. Phase 8 has no V2 candidate, and deployment remains prohibited until preprocessing parity is resolved and reverified on a candidate.

Reproduce with:

```bash
ml/.venv/bin/python ml/scripts/verify_java_onnx_parity.py \
  --java-home "$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
```

The script creates Python references and executes `OnnxClassifierParityTest`; it intentionally exits nonzero when the assertions fail. The JUnit parity test is skipped when invoked without a generated reference file.
