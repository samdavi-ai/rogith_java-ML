"""Audit prepared classifier splits for decode failures, duplicates, and family/visual overlap."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.scripts.prepare_dataset import dhash, source_group

EXTENSIONS = {".jpg", ".jpeg", ".png"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("ml/data/processed/classification"))
    parser.add_argument("--source-audit", type=Path, default=Path("ml/reports/dataset_audit.json"))
    parser.add_argument("--out", type=Path, default=Path("ml/reports/phase9_split_leakage_audit.json"))
    args = parser.parse_args()

    records = []
    corrupt = []
    unsupported = []
    counts: dict[str, Counter[str]] = {split: Counter() for split in ("train", "validation", "test")}
    exact: dict[str, list[str]] = defaultdict(list)
    family_splits: dict[str, set[str]] = defaultdict(set)
    for split in counts:
        for path in sorted((args.data / split).glob("*/*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in EXTENSIONS:
                unsupported.append(str(path))
                continue
            label = path.parent.name
            counts[split][label] += 1
            family_splits[source_group(path)].add(split)
            try:
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    width, height = image.size
                    if min(width, height) < 32:
                        raise ValueError(f"image is too small: {width}x{height}")
            except Exception as error:  # report every file-level failure
                corrupt.append({"path": str(path), "error": type(error).__name__})
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            exact[digest].append(str(path))
            records.append({"split": split, "label": label, "path": path, "dhash": dhash(path)})

    near = []
    for index, left in enumerate(records):
        for right in records[index + 1:]:
            if left["split"] == right["split"]:
                continue
            distance = (left["dhash"] ^ right["dhash"]).bit_count()
            if distance <= 3:
                near.append({
                    "distance": distance,
                    "sameLabel": left["label"] == right["label"],
                    "left": str(left["path"]), "leftSplit": left["split"], "leftLabel": left["label"],
                    "right": str(right["path"]), "rightSplit": right["split"], "rightLabel": right["label"],
                })

    source_audit = json.loads(args.source_audit.read_text())
    source_candidate_count = source_audit.get("nearDuplicateCandidatePairsAcrossSourceSplits")
    if source_candidate_count is None:
        source_candidate_count = len(source_audit.get("nearDuplicateCandidatesAcrossSplits", []))

    report = {
        "dataRoot": str(args.data),
        "images": len(records) + len(corrupt),
        "countsBySplitAndClass": {split: dict(sorted(value.items())) for split, value in counts.items()},
        "corruptOrSmall": corrupt,
        "unsupportedFiles": unsupported,
        "exactDuplicateGroups": [paths for paths in exact.values() if len(paths) > 1],
        "sourceFilenameFamiliesCrossingSplits": [
            {"family": family, "splits": sorted(splits)}
            for family, splits in sorted(family_splits.items()) if len(splits) > 1
        ],
        "crossSplitDHashDistanceAtMost3": near,
        "crossSplitDHashCandidateCount": len(near),
        "sourceArchiveCrossSplitDHashCandidateCount": source_candidate_count,
        "interpretation": "dHash distance <=3 marks candidates for visual review; it does not prove same physical object. Any unresolved candidate remains a split-leakage gate failure.",
        "manualVisualReview": {
            "reviewedPairCount": 0,
            "method": "No manual pair review required when the automated cross-split candidate count is zero; otherwise inspect every listed pair side by side.",
            "finding": "No cross-split dHash candidates remain." if not near else "Cross-split candidates require manual disposition; image similarity alone does not prove physical-object identity.",
            "disposition": "PASS: no cross-split candidates." if not near else "UNRESOLVED; retain as a split leakage gate failure until related views are grouped or removed and the split is rebuilt.",
        },
    }
    report["gate"] = "FAIL" if corrupt or unsupported or report["exactDuplicateGroups"] or report["sourceFilenameFamiliesCrossingSplits"] or near else "PASS"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("gate", "images", "countsBySplitAndClass", "corruptOrSmall", "exactDuplicateGroups", "sourceFilenameFamiliesCrossingSplits", "crossSplitDHashCandidateCount", "sourceArchiveCrossSplitDHashCandidateCount")}, indent=2))
    if report["gate"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
