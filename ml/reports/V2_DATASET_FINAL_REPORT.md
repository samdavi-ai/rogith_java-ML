# V2 dataset final report — Phase 10

Audit date: 2026-10-02. Dataset status: **FAIL**. No dataset is locked or approved for a new V2 run.

## Dataset and labels

The checkout contains `ml/data/candidates/reject_v2/` with seven labels: battery waste, keyboard, light bulb, mobile phone, mouse, PCB, and derived `not_ewaste`. This is a previously assembled candidate experiment, not a locked Phase 10 dataset. It does not cover charger, adapter, whole laptop, monitor, cable, earphones, headphones, or arbitrary unknown objects. Its 1,468 files are assigned 1,120 train (76.29%), 173 validation (11.78%) and 175 test (11.92%). Training files include source variants. Per-class counts and within-class split percentages are:

| Class | Train | Validation | Test | Total | Train / val / test within class |
|---|---:|---:|---:|---:|---:|
| Battery waste | 103 | 10 | 15 | 128 | 80.47% / 7.81% / 11.72% |
| Keyboard | 90 | 10 | 8 | 108 | 83.33% / 9.26% / 7.41% |
| Light bulb | 31 | 3 | 3 | 37 | 83.78% / 8.11% / 8.11% |
| Mobile phone | 106 | 11 | 12 | 129 | 82.17% / 8.53% / 9.30% |
| Mouse | 47 | 11 | 6 | 64 | 73.44% / 17.19% / 9.38% |
| PCB | 146 | 15 | 16 | 177 | 82.49% / 8.47% / 9.04% |
| Derived not e-waste | 597 | 113 | 115 | 825 | 72.36% / 13.70% / 13.94% |
| **Total files** | **1,120** | **173** | **175** | **1,468** | **76.29% / 11.78% / 11.92%** |

Source classes Glass, Organic, Paper and Plastic were aggregated as `not_ewaste`; that is a derived task label rather than an explicit source label. Candidate V2 contains only the six current e-waste outputs plus this binary-style negative category. No physical object identities or capture conditions are recorded.

## Licensing

Candidate files originate from the Mendeley/Roboflow source archive declared CC BY 4.0. The selected six categories and four negative-source categories share that archive license declaration. See [DATASET_SOURCES_FINAL.md](../DATASET_SOURCES_FINAL.md) for source URLs, published versus audited counts, file usage, transformations and attribution requirements. The source archive has no per-image creator/provenance manifest; this and the image-level split findings prevent release acceptance. Other leads, including Bower, GIZ, Kaggle and Roboflow listings, were not used.

## Quality checks

The candidate directory was audited with `ml/scripts/audit_split_leakage.py`:

- Corrupt or undersized images: **0** of 1,468.
- Exact duplicate groups: **0**.
- Source filename families crossing splits: **0**.
- Class directories and labels: seven mapped directories; no unsupported labels reported.
- Cross-split dHash distance ≤3 pairs: **180**, all same-label; 23 at distance 0, 34 at 1, 50 at 2 and 73 at 3. These remain candidates and were not all individually adjudicated for this candidate tree; therefore split isolation is **FAIL**.
- The raw source archive reported 544 cross-split dHash candidate pairs; these are a separate all-source audit count. Phase 9 visually reviewed 23 candidates in the prepared six-class split and left them unresolved. The corrected temporary split still contained three cross-class near-duplicate links in a mixed battery/PCB scene.

The exact candidate audit output is checked in as [`v2_candidate_split_audit.json`](v2_candidate_split_audit.json). Automated decode/duplicate checks pass, but the release gate requires unresolved near-duplicate candidates to be resolved, so these passes do not make the data set ready.

## Real-world isolation

`ml/data/recolens_real_world_test_manifest.csv` has zero image rows. `ml/data/recolens_real_world_test/` contains documentation and a diagnostic pilot manifest, no accepted camera images. Three screenshot crops documented in the pilot manifest are excluded. There is no real-world accuracy, lighting/device/distance coverage, or locked hash set. Nothing from the real-world set was used in training.

## Candidate V2 test measurements (diagnostic only)

The existing candidate evaluation reports 175 files: accuracy/top-1 accuracy 92.57%, macro precision 89.75%, macro recall 90.81%, macro F1 89.89%, weighted precision 93.14%, weighted recall 92.57%, weighted F1 92.61%. Its test split is affected by unresolved dHash candidates and is not a final locked test result. Per-class results are in `candidate_v2_evaluation.json`.

On the 115 derived-negative examples, the model predicted five as known e-waste: false e-waste rate **5/115 = 4.35%**; negative precision 98.21%, recall 95.65%, F1 96.92%. This is a source-split diagnostic score, not real-world performance. Top-3 accuracy, unknown-object acceptance, confidence-threshold calibration, and camera accuracy are **NOT TESTED**.

## Decision

Do not train a new model or present these candidate results as release validation. The existing candidate is retained for investigation, while a future training run remains blocked on a leakage-clean licensed dataset and an independent locked camera cohort.
