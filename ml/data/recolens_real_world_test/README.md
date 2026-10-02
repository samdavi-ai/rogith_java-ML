# RecoLens real-world test set

The locked real-world test set currently has **zero accepted camera images**. The root manifest at `../recolens_real_world_test_manifest.csv` contains the Phase 11 required fields plus object grouping and image dimensions, with a header only. No locked manifest exists because there is nothing to lock.

Three user-provided screenshot crops remain diagnostic-only fixtures in `../../tests/fixtures/real_world_challenges/`. Their metadata and hashes are in [`pilot_manifest.csv`](pilot_manifest.csv); they are excluded from training, validation, threshold selection, and locked-set metrics. One shows only part of a laptop, so it is not a whole-laptop example.

Use [`../../tools/real_world_capture.html`](../../tools/real_world_capture.html) to record new physical camera frames and metadata. The page saves only after a person starts the camera and chooses each label/condition. On desktop Chrome/Edge, choose the `ml/data` directory for direct local writes. Other browsers can download each JPEG plus CSV and SHA-256 lock files for manual placement. Review the images and labels for PII before locking. Never use these files for training or threshold tuning.

Follow [`../../REAL_WORLD_TEST_PROTOCOL.md`](../../REAL_WORLD_TEST_PROTOCOL.md) for future captures. Do not place training or validation images here. This set cannot support aggregate real-world accuracy claims yet.
