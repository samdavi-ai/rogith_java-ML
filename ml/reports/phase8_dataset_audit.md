# Phase 8 dataset quality audit

Audit date: 2026-10-02. Summary of research and local file-level audit; no candidate was used for training.

## Existing production source

The current Mendeley CC BY 4.0 archive has 2,157 images and 12 labels. Its local image/label audit passed decode, label presence, exact duplicate, and source-family split checks. It does not contain explicit charger, laptop, monitor, cable, or headphones classes. The prior selected six-class train/validation/test grouping audit reported no source-family crossing; 544 broad cross-split dHash candidate pairs remain in the raw source audit and were not all manually adjudicated. Existing counts and limits are recorded in [`dataset_audit.md`](dataset_audit.md) and [`dataset_report.md`](dataset_report.md).

## Downloaded external candidate: Bower

Source: `BowerApp/bower-waste-annotations`, published MIT license; local file `ml/data/external/bower_validation/0000.parquet`. File size: 225,427,984 bytes. SHA-256: `85bc4d92c37c6c09e0cc5b7b3e880cd78f685e363b48df2e693105ad4778b9a2`. The published source describes consumer phone-camera images and says it is a validation-only collection with manually reviewed annotations.

The actual parquet has **2,546 annotation rows**, **1,578 unique image IDs**, and **1,578 unique image byte hashes**. This conflicts with the card's stated 1,440 image files. File-level checks over unique images found:

| Check | Result |
|---|---:|
| Decode failures | 0 |
| Declared-vs-decoded dimensions mismatches | 0 |
| File format | 1,578 JPEG |
| Distinct post-orientation dimensions | 38 dimensions, spanning 256×205 through 901×901 |
| Images with either dimension below 224 px | 24 |
| Exact duplicate image groups | 0 |
| dHash candidate pairs at distance ≤3 | 1 |
| Image IDs whose bytes conflict between annotation rows | 0 |
| Null-only/unlabeled images | 1 |
| Images with multiple annotation rows | 544 |

The dataset has 53 unique images labeled object `Battery`, 2 `E-cigarette`, 2 `Electronic Device`; material `Electronic Waste` appears on 11 images. Using the conservative frame rule “any positive e-waste/battery object or electronic-waste material means E_WASTE; otherwise a known annotation means NOT_E_WASTE,” this yields 57 E_WASTE, 1,520 NOT_E_WASTE and 1 UNLABELED frame labels. These are derived audit labels, not labels provided as a binary target. 544 frames have multiple annotation rows; 468 have more than one distinct material/object label combination. Frame-level aggregation can conceal object-level mixtures.

The full machine report is [`bower_dataset_audit.json`](bower_dataset_audit.json); the repeatable audit script is [`../scripts/audit_bower_dataset.py`](../scripts/audit_bower_dataset.py), using [`../requirements-audit.txt`](../requirements-audit.txt). The one near-duplicate candidate has not been manually adjudicated. Image-level privacy/PII review and missing camera-condition metadata remain open, and the card/image count discrepancy needs resolution. Therefore Bower is **not yet accepted as the locked RecoLens test set**. It may be useful for an external binary challenge later, but it cannot establish subtype accuracy for chargers, adapters, laptops, monitors, cables, or audio accessories.

## Other sources and gate outcome

See [`../DATASET_CANDIDATES.md`](../DATASET_CANDIDATES.md) for license, volume, classes, redistribution/commercial-use status, collection characteristics, and disposition for each candidate. GIZ offers relevant laptop/computer labels but a 2.83 GB object-detection archive whose individual counts, images, object-group leakage and label quality have not been audited; the viewer currently fails. A separate Mendeley CC BY 4.0 laptop-parts dataset lists 3,640 raw phone-camera component images, but its scope is dismantled internal components rather than whole laptops, and its record/paper disagree about augmented counts. Akhil's 78 MB MIT dataset is gated behind contact-information sharing, so it was not accessed. 4w4kt lacks a clearly stated dataset license and combines seven upstream sources with independent terms. NexTech14 is CC BY-NC 4.0 and not suitable for this commercial deployment. Roboflow listings were not mistaken for downloaded data.

### Gate result

The existing v1 training source is audited, but no new dataset passes the Phase 8 gate for expanded charger/laptop categories. Bower has promising phone imagery but is not fully accepted for evaluation because of the image-count discrepancy, unlabeled frame, one near-duplicate candidate and missing PII/capture-metadata review. No dataset supports enough clean charger/adapter examples to train and independently test that class. **STOP before Phase 8 model training** as directed by the brief.
