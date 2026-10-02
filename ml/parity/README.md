# RecoLens Java / Python / ONNX parity fixture

`phase9/` is the deterministic 60-image V1 held-out fixture used by `OnnxClassifierParityTest`.

- `images/` contains byte-for-byte copies of the 60 fixed test inputs.
- `preprocessed_nchw_f32.zip` contains the Python reference NCHW float32 tensors and two small preprocessing probes (RGBA PNG alpha handling and JPEG EXIF orientation 6).
- `fixture.json` records per-image input and tensor SHA-256 values, raw ONNX logits, float64 softmax probabilities, top-5 classes, model/runtime versions, and a Phase 8 reference generated using the old TensorFlow/Graphics2D pipelines.
- `probes/` contains the two deterministic synthetic probe images.

The current input contract is RGB, accurate JPEG decode, three-channel PNG decode with alpha ignored, no EXIF orientation transform, bilinear stretch resize to 224×224 without crop/pad, float32 NCHW, and `pixel / 127.5 - 1.0`. The model output is raw logits in the exact `ml/class_mapping.json` order; Java applies a stable double-precision softmax.

Regenerate the fixture and run the explicit Java parity gate with the project's JDK 17:

```bash
ml/.venv/bin/python ml/scripts/verify_java_onnx_parity.py \
  --java-home "$(brew --prefix openjdk@17)/libexec/openjdk.jdk/Contents/Home"
```

The command rebuilds the fixture from `ml/data/processed/classification/test`, verifies the model hash, then invokes only `OnnxClassifierParityTest`. Run the complete Java suite separately from `backend/` with `JAVA_HOME` set to JDK 17.

## Measured numerical gate

Across all 60 fixed images, Python and Java decode the RGB source pixels identically (the per-image decoded RGB SHA-256 values match). Float bilinear arithmetic differs by at most `8.60691e-5` in the normalized tensor (mean `3.20378e-7`); raw logits differ by at most `7.73073e-5` (mean `1.51503e-5`); probabilities differ by at most `2.19729e-5` (mean `2.80507e-7`). The largest top-1 confidence difference is `2.19729e-5` (mean `8.37332e-7`). These measurements set the test limits: tensor/logit absolute difference `1e-4`, probability absolute difference `3e-5`, and exact top-1/top-3/top-5 ranking agreement for every image. Relative logit error is reported as a diagnostic; its maximum is `0.00264471` and mean is `1.27014e-5`, with the maximum inflated by near-zero logits.

These limits reflect the observed float32 resize/ONNX CPU execution envelope on the pinned 60-image fixture, with a small round-up margin. They are not selected from a desired pass rate. Any runtime, model, or input contract change requires regenerating and reviewing the measurements before updating the gate.
