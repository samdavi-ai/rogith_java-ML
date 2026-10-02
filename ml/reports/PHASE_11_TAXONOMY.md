# RecoLens taxonomy decision — Phase 11

## Decision

Keep the six frozen V1 output labels for any future compatibility evaluation: `battery_waste`, `keyboard`, `light_bulb`, `mobile_phone`, `mouse`, and `pcb`. Do not expand the production class map in Phase 11. There is not enough independently sourced, identity-grouped data for accessory or whole-computer subtypes, and the camera set is empty.

For a future user-facing taxonomy, treat chargers, adapters, cables, and external power supplies as a single `electronic_accessory` category unless a later use-case study shows users need different disposal guidance. These items often share visual form and handling context, and splitting them now would overstate the evidence. Keep batteries separate because battery handling is distinct. Keep laptop, monitor, and tablet as separate whole-device categories only after each has sufficient whole-object captures and disposal guidance; laptop-component imagery is not whole-laptop evidence. A tablet should not be folded into `mobile_phone` merely because of a similar screen.

`non_ewaste` must represent diverse everyday objects, including hard negatives that resemble electronics. The current derived negative set is based on selected glass, organic, paper, and plastic source labels; visual review found 15 plastic-labelled images that appear electronic or ambiguous, so those and their linked families were held as `UNKNOWN`. This is not enough to establish a robust negative class. `unknown` remains a separate abstention/uncertainty outcome, not a known object category and never a synonym for `non_ewaste`.

## Phase 11 data disposition

The existing candidate V2 tree has 7 labels and 1,468 files. It remains rejected as a final training source. A local, ignored staging split was rebuilt by grouping filename families, exact hashes, and all dHash≤3 links. It contains 1,139 retained images; 37 files in 8 visually mixed-label components or 29 manual label holds were quarantined. Automated post-build split leakage audit passes with zero corrupt/small files, exact-duplicate groups, filename-family crossings, or cross-split dHash≤3 pairs. The staged split is a leakage experiment only: it is not a final V2 dataset and was not used to train a model.
