# V1 real-world error analysis — Phase 11

## Camera-set status

There are **0 accepted physical camera images** in `ml/data/recolens_real_world_test/`; all requested classes and capture-factor coverage are therefore **BLOCKED**. No real-world precision, recall, F1, confusion matrix, or false e-waste rate can be calculated. No camera error examples exist to save. The three screenshot crops in the diagnostic pilot manifest are excluded because they are not original camera frames with complete capture metadata.

## Separate laboratory baseline

The existing compatible V1 test remains 59/60 (98.33%). Its one error is a battery-waste image predicted as mobile phone at confidence 0.57193. This is a laboratory split error, not a real-world camera failure. The rejected candidate V2 scores 52/60 on that same existing-class slice; it is not approved and was not retrained in Phase 11.

The prior candidate's 115 derived-negative evaluation is also not camera evidence. Its 5/115 false e-waste predictions (4.35%) are a source-split diagnostic only. V1 is a six-class closed-set model and necessarily assigns an output class to every input; no unknown-object rejection behavior is established by these figures.

## Diagnostic upload smoke case

The production API smoke request used the pre-existing diagnostic bottle screenshot crop. V1 returned `Mouse` at confidence 0.8060. This is a concrete diagnostic misclassification, but it is not counted in the official camera set because the input is a screenshot crop without verified original capture metadata. The smoke request confirms endpoint behavior, not a real-world performance rate.

## Required next evidence

Collect consented original camera frames across the physical devices, lighting, backgrounds, positions, distances, and orientations in `ml/REAL_WORLD_TEST_PROTOCOL.md`. Independently verify labels and object identities, remove PII, compute hashes, freeze the manifest, and freeze the candidate before reviewing its errors. Then produce per-class metrics, a confusion matrix, false e-waste rate, and privacy-reviewed misclassification examples. Until that collection is complete, V1 real-world performance is **NOT TESTED**.
