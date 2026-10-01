# Dataset report

Source: Custom Bangladeshi E-Waste Image Dataset, Mendeley Data V1

## Provenance and suitability

The archive contains 2,157 images across 12 labeled waste classes in train/valid/test folders, with YOLO bounding-box annotations. Images are suitable for image-level classification because audited frames each had exactly one unique class label; box annotations were not used to crop objects. Selected classes are six e-waste categories with visual object identities relevant to the app. The original test images from the six non-selected source classes are held out for a closed-set OOD characterization.

The read-only validation run (`reports/dataset_validation.json`) checked all 2,157 source images: 1,500 train, 330 validation, 327 test; zero corrupt images, missing labels, exact-duplicate groups, or source filename families crossing source splits. It recorded 544 raw image-pair dHash ≤3 candidates across source splits. The preparation audit separately compares one representative per source family (255 near-duplicate candidates) and groups same-class selected candidates before constructing the final split; those counts use different units and are not contradictory.

The archive documentation declares CC BY 4.0. Source links and attribution are in [DATASET_SOURCES.md](../DATASET_SOURCES.md). Source-reported names/counts were read from the archive and verified by the audit script; this report does not infer physical object identities.

## Cleaning and leakage checks

- Images scanned: 2,157; corrupt/too-small: 0; missing label files: 0; labels without images: 0; multi-class frames: 0. Four images had no single class label and were excluded from classification.
- Exact duplicate groups: 0.
- Same-stem filename-family cross-partition leaks: 0.
- Cross-source-partition dHash candidates at Hamming distance ≤3: 255 over source data; 109 selected-class edges grouped into connected components before splitting.
- Selected-class components after near-duplicate grouping: 320.

dHash grouping is a conservative visual heuristic, not proof of distinct physical devices. The source has no device-level IDs or acquisition manifest. Train-only augmentations remain only in train; for any family assigned to validation/test only one original image is retained.

## Final split (after component reassignment)

| Class | Train images | Train families | Validation images/families | Test images/families |
|---|---:|---:|---:|---:|
| battery_waste | 103 | 57 | 10/10 | 15/15 |
| keyboard | 90 | 50 | 10/10 | 8/8 |
| light_bulb | 31 | 15 | 3/3 | 3/3 |
| mobile_phone | 106 | 62 | 11/11 | 12/12 |
| mouse | 47 | 29 | 11/11 | 6/6 |
| pcb | 146 | 78 | 15/15 | 16/16 |

Split algorithm: Selected-class source filename families connected by same-class dHash distance <=3 were kept together; deterministic seed-42 70/15/15 split stratified by class; training variants retained only in train.

Excluded-class original test images held aside for OOD characterization: 205. These are never used for training, checkpoint selection, or supported-class metrics.
