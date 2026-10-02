# Dataset audit — Phase 7B

Audit date: 2026-10-02. Machine-readable report: [`dataset_audit.json`](dataset_audit.json). Command: `ml/.venv/bin/python ml/scripts/validate_dataset.py --data-root ml/data/raw/roboflow_v5 --report ml/reports/dataset_audit.json`.

## Source archive checks

| Check | Result |
|---|---:|
| Image files | 2,157 |
| Existing source split | train 1,500; valid 330; test 327 |
| Dimensions | all 640×640 |
| Corrupt images | 0 |
| Unsupported image files | 0 |
| Missing YOLO labels | 0 |
| Exact duplicate groups | 0 |
| Source filename families crossing splits | 0 |
| Images under 32 px on either side | 0 |
| Cross-split dHash pairs at distance ≤3 | 544 candidate pairs |

The automated source audit returns PASS for the checks it treats as release conditions. Its dHash scan is deliberately a candidate finder, not a definitive duplicate verdict; 544 pairs need human/source-family interpretation. The selected six-class dataset preparation separately grouped same-class dHash neighbors and source filename families before splitting, and reported no source-group cross-split leaks. Filename groups do not prove physical-object independence.

## Prepared classifier counts

| Class | Train | Validation | Test |
|---|---:|---:|---:|
| Battery waste | 103 | 10 | 15 |
| Keyboard | 90 | 10 | 8 |
| Light bulb | 31 | 3 | 3 |
| Mobile phone | 106 | 11 | 12 |
| Mouse | 47 | 11 | 6 |
| PCB | 146 | 15 | 16 |

These counts include only the supported class tree; train includes source training variants. The separate original-source negative evaluation pool has 205 images over Plastic 58, Paper 33, Glass 20, Organic 4, Metal 41 and Medical 49. Metal/Medical are semantically ambiguous and are not treated as clean non-e-waste labels. See [`dataset_report.md`](dataset_report.md) for the original source inventory, split method, and limitations.

## Quality limitations and Phase 7B expansion decision

The 2,157-image source has no charger/adapter, whole-laptop, monitor, cable, or headphone label. Four clean general-waste categories supported the previous negative-class experiment, but that candidate regressed the existing e-waste test from 59/60 to 52/60; Metal and Medical may contain electronics. This source alone cannot responsibly train the requested expanded taxonomy.

The GIZ CC BY 4.0 dataset is a promising external e-waste source for laptops/computers and broad real-world conditions, but it has no charger category, is object-detection data, and the public viewer reports a generation error. The archive was not represented as acquired, audited, or trained. Roboflow pages may list useful categories, but no versioned image export was available for file-level checks in this run. Source details and URLs are recorded in [`DATASET_SOURCES.md`](../DATASET_SOURCES.md).

Conclusion: do not fabricate expanded-class sample counts or mark any new categories supported. Dataset expansion and new training are blocked on obtaining a versioned, auditable, appropriately licensed dataset with charger/adapter plus laptop and representative hard negatives.
