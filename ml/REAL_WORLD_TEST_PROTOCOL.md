# RecoLens real-world test protocol

## Purpose and split integrity

Use this set only for final, locked external evaluation. Never use it for training, augmentation, validation-loss selection, hyperparameter tuning, threshold calibration, or class-map edits. Tune on separate validation data. If a test result influences a model change, retire that test version and collect a new locked set.

## Capture plan

Capture each available physical item in a clean, consented setting without people, faces, screens containing personal content, addresses, serial numbers, QR codes, documents, or other identifying details. Use the actual phone/webcam camera and save original image bytes; do not use web images or screenshots of model output. Assign an opaque image ID, not a personal name or device serial.

For each supported or proposed class, target at least 3 distinct objects per condition and vary items between frames:

| Factor | Required values |
|---|---|
| Lighting | bright; normal indoor; low light |
| Background | plain; cluttered |
| Distance | close; medium; far |
| Orientation | front; side; angled |

The full Cartesian product is too large for one object; use a balanced fractional design so each value occurs repeatedly and combinations are not confounded. Include isolated item and realistic scene views. Capture negatives (bottles, paper/books, plastic, glass, clothing and varied household objects) under the same conditions.

## Per-image metadata

Record image ID, file name, actual object, canonical category/system label, opaque object identity group (for duplicate control), device class, browser, generic camera label, image width/height, lighting, background, approximate distance, orientation/visibility, timestamp rounded to date, source/consent, EXIF handling, and SHA-256. Do not put names, precise location, faces, serials, or other PII in metadata. Any field not known must say `unknown`, not be guessed.

## Quality and lock procedure

Before lock, verify image decode, label review, no PII, class counts, exact hashes, perceptual near-duplicates, and object-ID grouping. Keep all images from one physical object/near-duplicate family together. Create train/validation/test splits by object/source before training; this real-world test remains separate. Once finalized, write the SHA-256 manifest, freeze the files read-only, tag the manifest version, and record model/test-set version together. Do not inspect test errors until candidate/model/configuration are frozen.

## Capture helper

Use [`tools/real_world_capture.html`](tools/real_world_capture.html) from localhost or HTTPS. It requests camera access only after “Start camera”, saves the full video frame as a JPEG, computes SHA-256, and records the chosen class and conditions. Chrome/Edge can write into the selected `ml/data` folder; other browsers use downloads. The capture tool does not verify physical labels or PII; a person must review each image before the manifest can be locked.

## Current set state

The existing three user-provided crops are a diagnostic pilot for bottle, charger/adapter, and a partial laptop scene only; they are not camera captures and original scene metadata are incomplete. They are excluded from the official camera set. Bower is a potential independent phone-camera waste validation set, but it has generic electronic-device annotations rather than RecoLens subtype labels. Accepted RecoLens camera images: **0**; required test set: **NOT COMPLETE**. No capture metadata is fabricated in the official manifest.
