# RecoLens real-world test set

The locked real-world test set currently has **zero image files**. The root manifest at `../recolens_real_world_test_manifest.csv` contains `image_id,true_class,source,condition,device,lighting,distance,hash,relative_path` and no records until a consented, PII-reviewed capture set is ready. Unknown metadata must be recorded as `unknown`, not inferred.

Three user-provided screenshot crops remain diagnostic-only fixtures in `../../tests/fixtures/real_world_challenges/`. Their metadata and hashes are in [`pilot_manifest.csv`](pilot_manifest.csv); they are excluded from training, validation, threshold selection, and locked-set metrics. One shows only part of a laptop, so it is not a whole-laptop example.

Follow [`../../REAL_WORLD_TEST_PROTOCOL.md`](../../REAL_WORLD_TEST_PROTOCOL.md) for future captures. Do not place training or validation images here. This set cannot support aggregate real-world accuracy claims yet.
