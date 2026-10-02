"""Build an isolated 7-class candidate with a conservative non-ewaste class.

The four general-waste source classes are copied only from their existing
train/valid/test partitions. The production dataset and its locked test remain
untouched. This candidate is experimental and is not a deployment artifact.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from pathlib import Path

from prepare_dataset import image_label

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/raw/roboflow_v5"
BASELINE = ROOT / "data/processed/classification"
OUTPUT = ROOT / "data/candidates/reject_v2"
CLASSES = ROOT / "class_mapping.json"
NEGATIVE_SOURCE_CLASSES = {"Plastic_Waste", "Paper_Waste", "Glass_Waste", "Organic_Waste"}
SPLITS = {"train": "train", "valid": "validation", "test": "test"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--baseline", type=Path, default=BASELINE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--classes", type=Path, default=CLASSES)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"Refusing to replace candidate data: {args.output}")

    source_names = json.loads((args.source / "data.yaml").read_text().split("names:", 1)[1].splitlines()[0].strip().replace("'", '"'))
    base_classes = json.loads(args.classes.read_text())["classes"]
    classes = [*base_classes, {"id": len(base_classes), "name": "not_ewaste", "displayName": "Not e-waste", "datasetLabel": "derived_general_waste"}]
    counts: dict[str, Counter] = {split: Counter() for split in SPLITS.values()}

    # Preserve the existing grouped split for the six e-waste classes.
    for split in SPLITS.values():
        for entry in base_classes:
            src = args.baseline / split / entry["name"]
            dst = args.output / split / entry["name"]
            files = sorted(p for p in src.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
            if not files:
                raise ValueError(f"Missing existing split/class: {src}")
            dst.mkdir(parents=True, exist_ok=True)
            for file in files:
                shutil.copy2(file, dst / file.name)
            counts[split][entry["name"]] = len(files)

    # Add four unambiguously general-waste labels, retaining their published split.
    # Metal and medical waste are excluded because those labels can contain e-waste.
    for source_split, target_split in SPLITS.items():
        image_dir = args.source / source_split / "images"
        labels_dir = args.source / source_split / "labels"
        out_dir = args.output / target_split / "not_ewaste"
        for image in sorted(p for p in image_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}):
            label, label_set = image_label(labels_dir / f"{image.stem}.txt", source_names)
            if label in NEGATIVE_SOURCE_CLASSES and len(label_set) == 1:
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(image, out_dir / f"{label}__{image.name}")
                counts[target_split]["not_ewaste"] += 1

    if any(counts[split]["not_ewaste"] == 0 for split in SPLITS.values()):
        raise ValueError(f"Negative class is empty in one or more splits: {counts}")
    args.output.mkdir(parents=True, exist_ok=True)
    mapping_path = args.output / "class_mapping.json"
    mapping_path.write_text(json.dumps({"version": "candidate-2.0.0", "classes": classes}, indent=2) + "\n")
    manifest = {
        "candidate": "recolens-reject-v2-experiment",
        "source": "Roboflow Universe e-waste-uvzkj v5 export (project archive records CC BY 4.0; Mendeley record attribution retained)",
        "splitPolicy": "Existing leakage-audited six-class processed splits retained; negative examples copied only from matching original source train/valid/test partitions.",
        "negativeSourceClasses": sorted(NEGATIVE_SOURCE_CLASSES),
        "excludedAmbiguousClasses": ["Metal_Waste", "Medical_Waste"],
        "counts": {split: dict(counts[split]) for split in SPLITS.values()},
        "classes": classes,
        "prohibitedUse": "Never use the test partition for training or model selection. This is an isolated candidate, not a production model.",
    }
    (args.output / "candidate_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
