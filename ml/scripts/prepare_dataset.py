#!/usr/bin/env python3
"""Audit the licensed Roboflow export and build a single-label image-classification tree."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageOps


SPLITS = {"train": "train", "valid": "validation", "test": "test"}
SUPPORTED_SPLITS = ("train", "valid", "test")
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def source_group(image_path: Path) -> str:
    """Roboflow keeps the original basename before `.rf.<content hash>` on variants."""
    return re.sub(r"\.rf\.[0-9a-f]+$", "", image_path.stem, flags=re.IGNORECASE)


def parse_classes(classes_path: Path) -> list[dict]:
    data = json.loads(classes_path.read_text(encoding="utf-8"))
    classes = data["classes"]
    if [entry["id"] for entry in classes] != list(range(len(classes))):
        raise ValueError("classes.json IDs must be contiguous and ordered from zero")
    if len({entry["name"] for entry in classes}) != len(classes):
        raise ValueError("classes.json contains duplicate canonical class names")
    return classes


def image_label(label_path: Path, source_names: list[str]) -> tuple[str | None, set[str]]:
    found: set[str] = set()
    if not label_path.is_file():
        return None, found
    for line in label_path.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if not parts:
            continue
        class_id = int(parts[0])
        if class_id < 0 or class_id >= len(source_names):
            raise ValueError(f"Invalid class ID {class_id} in {label_path}")
        found.add(source_names[class_id])
    return (next(iter(found)) if len(found) == 1 else None), found


def dhash(image_path: Path) -> int:
    with Image.open(image_path) as image:
        image = ImageOps.exif_transpose(image).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(image.getdata())
    value = 0
    for y in range(8):
        for x in range(8):
            value = (value << 1) | int(pixels[y * 9 + x + 1] > pixels[y * 9 + x])
    return value


def audit_and_prepare(data_root: Path, classes_path: Path, output_root: Path, report_path: Path, ood_output_root: Path) -> dict:
    classes = parse_classes(classes_path)
    canonical_by_source = {entry["datasetLabel"]: entry for entry in classes}
    yaml_path = data_root / "data.yaml"
    yaml_text = yaml_path.read_text(encoding="utf-8")
    match = re.search(r"(?m)^names:\s*(\[.*\])\s*$", yaml_text)
    if not match:
        raise ValueError(f"Cannot read source class list from {yaml_path}")
    source_names = json.loads(match.group(1).replace("'", '"'))

    report = {
        "source": "Custom Bangladeshi E-Waste Image Dataset, Mendeley Data V1",
        "sourceArchiveImages": 0,
        "sourceClassNames": source_names,
        "sourceImagesBySplitAndClass": {split: Counter() for split in SUPPORTED_SPLITS},
        "sourceAnnotationBoxesByClass": Counter(),
        "uniqueSourceGroupsBySplitAndClass": {split: Counter() for split in SUPPORTED_SPLITS},
        "sourceGroupVariantCounts": Counter(),
        "multiClassFrames": 0,
        "missingLabels": 0,
        "corruptImages": [],
        "missingImagesForLabels": 0,
        "exactDuplicateGroups": [],
        "nearDuplicateCandidatesAcrossSplits": [],
        "sourceGroupCrossSplitLeaks": [],
        "classificationImagesBySplitAndClass": {split: Counter() for split in SPLITS.values()},
        "classificationUniqueSourceGroupsBySplitAndClass": {split: Counter() for split in SPLITS.values()},
        "oodTestImagesByClass": Counter(),
        "ignoredSourceImages": Counter(),
        "imageDimensions": Counter(),
    }
    records: list[dict] = []
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    hash_paths: dict[str, list[str]] = defaultdict(list)
    source_splits: dict[str, set[str]] = defaultdict(set)

    for source_split in SUPPORTED_SPLITS:
        image_dir = data_root / source_split / "images"
        label_dir = data_root / source_split / "labels"
        image_paths = sorted(p for p in image_dir.glob("*") if p.suffix.lower() in IMAGE_EXTENSIONS)
        label_stems = {p.stem for p in label_dir.glob("*.txt")}
        report["missingImagesForLabels"] += len(label_stems - {p.stem for p in image_paths})
        for image_path in image_paths:
            report["sourceArchiveImages"] += 1
            label_path = label_dir / f"{image_path.stem}.txt"
            source_label, labels = image_label(label_path, source_names)
            if not label_path.is_file():
                report["missingLabels"] += 1
            for label in labels:
                report["sourceAnnotationBoxesByClass"][label] += sum(
                    1 for line in label_path.read_text(encoding="utf-8").splitlines()
                    if line.split() and int(line.split()[0]) == source_names.index(label)
                )
            if len(labels) > 1:
                report["multiClassFrames"] += 1
            try:
                with Image.open(image_path) as im:
                    im.verify()
                with Image.open(image_path) as im:
                    width, height = im.size
                    if width < 32 or height < 32:
                        raise ValueError(f"Image too small: {width}x{height}")
                    report["imageDimensions"][f"{width}x{height}"] += 1
            except Exception as exc:  # noqa: BLE001 - audit must record decoder failures.
                report["corruptImages"].append({"path": str(image_path), "error": str(exc)})
                continue

            file_digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
            hash_paths[file_digest].append(str(image_path))
            group = source_group(image_path)
            source_splits[group].add(source_split)
            record = {
                "path": image_path,
                "label": source_label,
                "labels": labels,
                "sourceSplit": source_split,
                "split": SPLITS[source_split],
                "group": group,
                "sha256": file_digest,
            }
            records.append(record)
            groups[(source_split, group)].append(record)
            if source_label:
                report["sourceImagesBySplitAndClass"][source_split][source_label] += 1

    for digest, paths in hash_paths.items():
        if len(paths) > 1:
            report["exactDuplicateGroups"].append({"sha256": digest, "paths": paths})
    report["sourceGroupVariantCounts"] = Counter(len(rows) for rows in groups.values())
    report["sourceGroupCrossSplitLeaks"] = [
        {"group": group, "splits": sorted(splits)}
        for group, splits in source_splits.items() if len(splits) > 1
    ]

    for (source_split, group), rows in groups.items():
        labels = {row["label"] for row in rows}
        if len(labels) != 1:
            raise ValueError(f"A source group has conflicting image labels: {source_split}/{group}: {labels}")
        label = next(iter(labels))
        if label in canonical_by_source:
            report["uniqueSourceGroupsBySplitAndClass"][source_split][label] += 1

    # The filename family is the available grouping key. Compare one representative
    # of every source family across partitions for additional near-duplicate leaks.
    representatives = [min(rows, key=lambda row: str(row["path"])) for rows in groups.values()]
    hashes = [(row, dhash(row["path"])) for row in representatives]
    near_edges: list[tuple[tuple[str, str], tuple[str, str]]] = []
    for index, (left, left_hash) in enumerate(hashes):
        for right, right_hash in hashes[index + 1:]:
            if left["sourceSplit"] == right["sourceSplit"]:
                continue
            distance = (left_hash ^ right_hash).bit_count()
            if distance <= 3:
                report["nearDuplicateCandidatesAcrossSplits"].append({
                    "distance": distance, "left": str(left["path"]), "right": str(right["path"]),
                    "leftClass": left["label"], "rightClass": right["label"],
                })
                if left["label"] == right["label"] and left["label"] in canonical_by_source:
                    near_edges.append(((left["sourceSplit"], left["group"]), (right["sourceSplit"], right["group"])))

    if report["sourceGroupCrossSplitLeaks"]:
        raise ValueError(f"Source-group leakage across splits: {report['sourceGroupCrossSplitLeaks'][:5]}")

    if output_root.exists():
        shutil.rmtree(output_root)
    if ood_output_root.exists():
        shutil.rmtree(ood_output_root)
    # Reassign visual-near-duplicate families together, then make a deterministic
    # stratified 70/15/15 split at the resulting family-component level.
    parent: dict[tuple[str, str], tuple[str, str]] = {}
    def find(item: tuple[str, str]) -> tuple[str, str]:
        parent.setdefault(item, item)
        if parent[item] != item:
            parent[item] = find(parent[item])
        return parent[item]
    def union(a: tuple[str, str], b: tuple[str, str]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    for a, b in near_edges:
        union(a, b)
    selected_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    group_label = {(split, group): rows[0]["label"] for (split, group), rows in groups.items()}
    for key, label in group_label.items():
        if label in canonical_by_source:
            selected_groups[label].append(key)
    components: dict[str, dict[tuple[str, str], list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for label, keys in selected_groups.items():
        for key in keys:
            components[label][find(key)].append(key)
    assigned_split: dict[tuple[str, str], str] = {}
    rng = random.Random(42)
    for label, label_components in components.items():
        bins = list(label_components.values())
        rng.shuffle(bins)
        n = len(bins)
        n_train = max(1, round(n * 0.70))
        n_valid = max(1, round(n * 0.15))
        if n_train + n_valid >= n:
            n_train, n_valid = n - 2, 1
        for index, component in enumerate(bins):
            split = "train" if index < n_train else "valid" if index < n_train + n_valid else "test"
            for key in component:
                assigned_split[key] = split
    report["nearDuplicateComponentCount"] = len({find(key) for keys in selected_groups.values() for key in keys})
    report["selectedNearDuplicateEdgesGrouped"] = len(near_edges)
    report["splitMethod"] = "Selected-class source filename families connected by same-class dHash distance <=3 were kept together; deterministic seed-42 70/15/15 split stratified by class; training variants retained only in train."

    # Keep all train variants; held-out components contain one image per family.
    for (source_split, group), rows in groups.items():
        labels = {row["label"] for row in rows}
        label = next(iter(labels)) if len(labels) == 1 else None
        if label not in canonical_by_source:
            reason = label or "missing_or_multi_class"
            report["ignoredSourceImages"][reason] += len(rows)
            # The source test partition is held aside exclusively for OOD testing.
            # It is never copied into train/validation or used to choose a checkpoint.
            if source_split == "test" and label:
                for row in rows:
                    destination_dir = ood_output_root / label
                    destination_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(row["path"], destination_dir / row["path"].name)
                    report["oodTestImagesByClass"][label] += 1
            continue
        entry = canonical_by_source[label]
        target_split = SPLITS[assigned_split[(source_split, group)]]
        selected_rows = rows if target_split == "train" else rows[:1]
        for row in selected_rows:
            destination_dir = output_root / target_split / entry["name"]
            destination_dir.mkdir(parents=True, exist_ok=True)
            destination = destination_dir / row["path"].name
            shutil.copy2(row["path"], destination)
            report["classificationImagesBySplitAndClass"][target_split][entry["name"]] += 1
        report["classificationUniqueSourceGroupsBySplitAndClass"][target_split][entry["name"]] += 1

    report["selectedClassNames"] = [entry["name"] for entry in classes]
    report["selectedDatasetLabels"] = [entry["datasetLabel"] for entry in classes]
    report["sourceImagesBySplitAndClass"] = {k: dict(v) for k, v in report["sourceImagesBySplitAndClass"].items()}
    report["sourceAnnotationBoxesByClass"] = dict(report["sourceAnnotationBoxesByClass"])
    report["uniqueSourceGroupsBySplitAndClass"] = {k: dict(v) for k, v in report["uniqueSourceGroupsBySplitAndClass"].items()}
    report["sourceGroupVariantCounts"] = {str(k): v for k, v in sorted(report["sourceGroupVariantCounts"].items())}
    report["classificationImagesBySplitAndClass"] = {k: dict(v) for k, v in report["classificationImagesBySplitAndClass"].items()}
    report["classificationUniqueSourceGroupsBySplitAndClass"] = {k: dict(v) for k, v in report["classificationUniqueSourceGroupsBySplitAndClass"].items()}
    report["oodTestImagesByClass"] = dict(report["oodTestImagesByClass"])
    report["ignoredSourceImages"] = dict(report["ignoredSourceImages"])
    report["imageDimensions"] = dict(report["imageDimensions"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--classes", type=Path, default=Path("ml/classes.json"))
    parser.add_argument("--output", type=Path, default=Path("ml/data/processed/classification"))
    parser.add_argument("--ood-output", type=Path, default=Path("ml/data/processed/ood_test"))
    parser.add_argument("--report", type=Path, default=Path("ml/reports/dataset_report.json"))
    args = parser.parse_args()
    report = audit_and_prepare(args.data_root, args.classes, args.output, args.report, args.ood_output)
    print(json.dumps({
        "sourceArchiveImages": report["sourceArchiveImages"],
        "classificationImagesBySplitAndClass": report["classificationImagesBySplitAndClass"],
        "classificationUniqueSourceGroupsBySplitAndClass": report["classificationUniqueSourceGroupsBySplitAndClass"],
        "corruptImages": len(report["corruptImages"]),
        "exactDuplicateGroups": len(report["exactDuplicateGroups"]),
        "nearDuplicateCandidatesAcrossSplits": len(report["nearDuplicateCandidatesAcrossSplits"]),
        "sourceGroupCrossSplitLeaks": len(report["sourceGroupCrossSplitLeaks"]),
    }, indent=2))


if __name__ == "__main__":
    main()
