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

Record image ID, actual object, canonical category/system label, object identity group (for duplicate control), lighting, background, camera class (phone/webcam; omit make/model if it could identify a person), approximate distance, object orientation, timestamp rounded to date, source/consent, EXIF handling, and SHA-256. Do not put names, precise location, faces, or other PII in metadata. Any field not known must say `unknown`, not be guessed.

## Quality and lock procedure

Before lock, verify image decode, label review, no PII, class counts, exact hashes, perceptual near-duplicates, and object-ID grouping. Keep all images from one physical object/near-duplicate family together. Create train/validation/test splits by object/source before training; this real-world test remains separate. Once finalized, write the SHA-256 manifest, freeze the files read-only, tag the manifest version, and record model/test-set version together. Do not inspect test errors until candidate/model/configuration are frozen.

## Current set state

The existing three user-provided crops are a locked diagnostic pilot for bottle, charger/adapter, and laptop scene only; original camera and scene metadata are incomplete. They are not a representative real-camera dataset. Bower is a potential independent phone-camera waste validation set, but it has generic electronic-device annotations rather than RecoLens subtype labels. The required multi-condition RecoLens test set is **NOT COMPLETE**; no capture metadata is fabricated in the accompanying manifest.
