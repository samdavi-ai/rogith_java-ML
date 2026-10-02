# RecoLens dataset report

Audit date: 2026-10-02. Source archive available locally at `ml/data/raw/roboflow_v5/`; files are excluded from Git. The archive `data.yaml` identifies Roboflow Universe project `e-waste-uvzkj`, version 5, and declares CC BY 4.0. The associated dataset publication is documented in [`DATASET_SOURCES.md`](../DATASET_SOURCES.md). The archive contains 2,157 labeled-image files with YOLO boxes across 12 source labels; four images lacked one uniquely classifiable source label.

## Image and annotation audit

| Check | Result |
|---|---:|
| Total source image files | 2,157 |
| Source train / validation / test | 1,500 / 330 / 327 |
| Corrupt or undersized images | 0 |
| Missing labels | 0 |
| Labels without corresponding image | 0 |
| Multi-class frames | 0 |
| Exact duplicate groups | 0 |
| Source filename-family leaks between original splits | 0 |
| Cross-split dHash near-duplicate pair candidates | 544 (raw all-pairs audit) |
| Images excluded for missing/non-unique labels | 4 |

The 544 dHash candidates are similarity flags, not confirmed duplicates. A separate preparation audit compared one representative per filename family, found 255 candidate pairs, and grouped 109 same-class selected-class links before re-splitting. Pair units differ between those audits. Filename and perceptual hashes cannot prove physical-object independence.

## Source class inventory

Counts are images in original source train/valid/test partitions. Canonical class and ID are populated only for the six v1 outputs. A visual chart is saved as [`class_distribution.png`](class_distribution.png).

| Source label | v1 class / ID | Train | Validation | Test | Candidate-v2 treatment |
|---|---|---:|---:|---:|---|
| Battery_Waste | battery_waste / 0 | 99 | 26 | 23 | E-waste output |
| Glass_Waste | — | 93 | 14 | 20 | `not_ewaste` source |
| Keyboard | keyboard / 1 | 87 | 20 | 19 | E-waste output |
| Light_Bulb | light_bulb / 2 | 33 | 4 | 6 | E-waste output |
| Medical_Waste | — | 195 | 38 | 49 | Excluded; label can overlap electronics |
| Metal_Waste | — | 192 | 60 | 41 | Excluded; label can overlap electronics |
| Mobile | mobile_phone / 3 | 99 | 26 | 26 | E-waste output |
| Mouse | mouse / 4 | 51 | 13 | 16 | E-waste output |
| Organic_Waste | — | 84 | 12 | 4 | `not_ewaste` source |
| PCB | pcb / 5 | 144 | 30 | 31 | E-waste output |
| Paper_Waste | — | 141 | 26 | 33 | `not_ewaste` source |
| Plastic_Waste | — | 279 | 61 | 58 | `not_ewaste` source |

Candidate-v2 used only the source classes whose labels unambiguously denote general waste for this experiment. The generated candidate split counts are 1,120 train (597 negative), 173 validation (113 negative), and 175 test (115 negative plus the unchanged 60 selected e-waste test images). See `dataset_report.json` for machine-readable counts and dimensions, and `dataset_validation.json` for source integrity findings.

## Curated v1 split

| Class | Train images | Validation | Test |
|---|---:|---:|---:|
| battery_waste | 103 | 10 | 15 |
| keyboard | 90 | 10 | 8 |
| light_bulb | 31 | 3 | 3 |
| mobile_phone | 106 | 11 | 12 |
| mouse | 47 | 11 | 6 |
| pcb | 146 | 15 | 16 |
| **Total** | **523** | **60** | **60** |

Selected-class groups connected by same-class dHash distance ≤3 were held together, followed by deterministic seed-42 stratified 70/15/15 assignment. Training variants remain in train; validation/test groups retain one image. The original test partition of excluded classes was previously reserved for out-of-domain characterization, not training.

## Limits

No physical-item IDs, capture protocol, or per-image source provenance is available. The label set does not cover laptops, chargers, monitors, or arbitrary electronics, and “waste” labels describe appearance/category rather than legal e-waste status. Three user-submitted screenshot crops are qualitative error-analysis fixtures and were not included in training, validation, or locked test. Per-class counts and audit fields are in `dataset_report.json`; raw images remain local and ignored by Git.
