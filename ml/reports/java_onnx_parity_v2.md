# Java / Python / ONNX parity — Phase 9

Audit date: 2026-10-02. Runtime: OpenJDK 17.0.20.1, ONNX Runtime Java 1.20.0 and Python ONNX Runtime 1.20.0. Python preprocessing uses TensorFlow 2.17.0. Model SHA-256: `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`.

## Pipeline contract verified

- **Input and decoding:** Java `ClassificationService` reads JPEG/PNG through ImageIO. Python now dispatches JPEG to `tf.io.decode_jpeg(..., dct_method="INTEGER_ACCURATE")` and PNG to `tf.io.decode_png(..., channels=3)`. Both produce RGB. PNG alpha is discarded without compositing. Neither side applies EXIF orientation.
- **Resize:** Bilinear stretch to 224×224; no crop, padding or letterbox. TensorFlow returns float32 resized values. Java now interpolates in float32 directly and no longer rounds the resized image through an 8-bit `BufferedImage`.
- **Normalization and tensor:** RGB values use `pixel / 127.5 - 1.0`; float32 NCHW with shape `[1,3,224,224]` at inference. The batch dimension is 1.
- **Output and class order:** ONNX emits six raw logits. Java applies a stable double-precision softmax. The order is the contiguous `id` order in `ml/class_mapping.json`: Battery waste, Keyboard, Light bulb, Mobile phone, Mouse, Printed circuit board. The class count and NCHW input shape are checked when Java loads the model.

Two deterministic probes cover RGBA PNG alpha handling and a JPEG containing EXIF orientation 6. Python and Java decoded RGB bytes match exactly on both; the orientation dimensions remain unchanged. The probes' maximum normalized tensor difference is `6.06775e-5`.

## Phase 8 mismatch replay

The original discrepancy came from two preprocessing differences. TensorFlow 2.17's generic `decode_image` selected its faster JPEG decode path; Java ImageIO matched TensorFlow's `INTEGER_ACCURATE` decode instead. On the 60-image fixture, fast-decoded source pixels differed from ImageIO by as much as 5/255 per channel. Then Java `Graphics2D` rounded the resized image to uint8 before normalization, while TensorFlow retained float32 interpolation. Replaying the old paths found a maximum normalized input difference of `0.03613245` across 9,031,680 tensor elements.

The maximum confidence differences were therefore not caused by class mapping or softmax. The old Python float32 softmax and Java double softmax differ only slightly compared with the large change caused by decoded and resized pixels. After the inputs were aligned, both ONNX Runtime CPU paths produced closely matching logits. The lower-ranked disagreements occurred where class probabilities were nearly tied.

The three examples affecting the old top-4 ranking were:

1. `IMG_20250822_231153_1_jpg.rf.055d65f1f0714e9fda6d890f79bc15ab.jpg` — rank 4 differed. Python top-5: Battery waste `0.999981761`, Light bulb `0.000010084`, Mouse `0.000004081`, Printed circuit board `0.000001902`, Mobile phone `0.000001750`. Java top-5: Battery waste `0.999983668`, Light bulb `0.000008801`, Mouse `0.000004023`, Mobile phone `0.000001691`, Printed circuit board `0.000001437`. The tail classes at ranks 4–5 were reversed; their rank-wise probability differences were `2.11e-7` and `3.13e-7`.
2. `IMG_20250822_231221_1_jpg.rf.187ee67700b833c74c2c876f9f8165c7.jpg` — rank 4 differed. Python top-5: Battery waste `0.999896049`, Mobile phone `0.000070135`, Light bulb `0.000029188`, Printed circuit board `0.000002249`, Mouse `0.000002106`. Java top-5: Battery waste `0.999898946`, Mobile phone `0.000066552`, Light bulb `0.000030450`, Mouse `0.000002022`, Printed circuit board `0.000001800`. The Printed circuit board and Mouse tail classes were reversed; rank-wise differences were `2.27e-7` and `3.06e-7`.
3. `IMG_20250819_235956_1_jpg.rf.13c8f40791f750605aa42a1d3e903da9.jpg` — ranks 2 and 3 were reversed. Python top-5: Printed circuit board `0.999135077`, Mobile phone `0.000410283`, Keyboard `0.000402244`, Battery waste `0.000049412`, Mouse `0.000002266`. Java top-5: Printed circuit board `0.999011665`, Keyboard `0.000466556`, Mobile phone `0.000460810`, Battery waste `0.000057663`, Mouse `0.000002480`. Rank-wise probability differences at ranks 2 and 3 were `5.6273e-5` and `5.8566e-5`.

The old implementation also had a rank-5-only difference on `IMG_20250822_140413_jpg.rf.73cf4af821a990defde96ed1db5c0d92.jpg`: Python ranked Light bulb at `0.000008106`, while Java ranked Battery waste at `0.000008349` (difference `2.43e-7`). This did not affect top-4.

The exact replay confirms a maximum old top-1 confidence difference of `0.045158911` and a maximum top-4 rank probability difference of `0.045443077`. Both occur on `IMG_20250803_215701_jpg.rf.352a524931e1295dac040a7f6381d4f1.jpg`, at ranks 1 and 2 respectively. Python's top-5 was Mobile phone `0.520296812`, Battery waste `0.477712840`, Printed circuit board `0.001615686`, Light bulb `0.000321753`, Keyboard `0.000026972`. Java's was Mobile phone `0.565455723`, Battery waste `0.432269763`, Printed circuit board `0.001894977`, Light bulb `0.000319299`, Keyboard `0.000030470`.

The Phase 8 summary recorded top-4 agreement `237/240`. The replay from the saved 60 images and old preprocessing produces 236/240 rank-position matches, with the same three top-4-affected examples above; the rank-2/rank-3 swap accounts for two differing positions. The Phase 8 report did not preserve a scoring definition that explains the one-count difference, so its exact aggregate cannot be reproduced from the available artifacts.

## Fix and measured release gate

Python's shared loader and Java inference now use the same accurate JPEG decode and float bilinear resize contract. The persistent fixture and generator are in [`../parity/README.md`](../parity/README.md), [`../parity/phase9/fixture.json`](../parity/phase9/fixture.json), and [`../scripts/verify_java_onnx_parity.py`](../scripts/verify_java_onnx_parity.py). The fixture saves input image copies, all 60 preprocessed tensors, Python raw logits, probabilities and top-5 predictions, plus decoder and tensor checksums.

Measured across 60 fixed images:

- Decoded RGB SHA-256 agreement: **60/60**.
- Tensor max / mean absolute difference: **8.60691e-5 / 3.20378e-7**.
- Raw logit max / mean absolute difference: **7.73072e-5 / 1.51503e-5**.
- Raw logit max / mean relative difference: **0.00264471 / 1.27014e-5**. Relative maximum is sensitive to near-zero logits; release comparison uses absolute error as well.
- Probability max / mean absolute difference across all classes: **2.19728e-5 / 2.80507e-7**.
- Top-1 confidence max / mean absolute difference: **2.19728e-5 / 8.37332e-7**.
- Top-1 agreement: **60/60**; top-3 ranking agreement: **60/60**; top-5 ranking agreement: **60/60**.
- JPEG EXIF and RGBA PNG probes: **2/2** decoded pixel matches; maximum tensor difference `6.06775e-5`.

The gate is based on observed execution: tensor/logit absolute difference `≤1e-4`, probability absolute difference `≤3e-5`, identical top-1/top-3/top-5 rankings, and exact decoded RGB hashes. The limits round up the observed maxima and pass the same fixed images in the project's supported JDK 17 environment. The explicit parity test passed, and the complete Maven suite passed under JDK 17.

## Gate result

**JAVA / PYTHON / ONNX PARITY: PASS** for the fixed 60-image fixture and the two preprocessing probes. This result establishes local parity on OpenJDK 17.0.20.1 and ONNX Runtime 1.20.0. Recheck on any serving-platform runtime upgrade before deployment.
