#!/usr/bin/env python3
"""Create a local, non-release staging split grouped by source and visual family."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from shutil import copy2
import sys

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.scripts.prepare_dataset import dhash, source_group


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("ml/data/candidates/reject_v2"))
    parser.add_argument("--out", type=Path, default=Path("ml/data/candidates/phase11_reblocked"))
    parser.add_argument("--pair-review", type=Path, default=Path("ml/reports/near_duplicate_review.csv"))
    parser.add_argument("--label-holds", type=Path, default=Path("ml/reports/phase11_label_holds.csv"))
    parser.add_argument("--manifest", type=Path, default=Path("ml/reports/phase11_reblocked_manifest.csv"))
    parser.add_argument("--quarantine", type=Path, default=Path("ml/reports/phase11_quarantine_manifest.csv"))
    parser.add_argument("--summary", type=Path, default=Path("ml/reports/phase11_reblocked_summary.json"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite existing staging tree: {args.out}")

    records = []
    for split in ("train", "validation", "test"):
        for path in sorted(p for p in (args.source / split).glob("*/*") if p.is_file()):
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                if min(image.size) < 32:
                    raise ValueError(f"Image too small: {path}")
            records.append({
                "path": path,
                "label": path.parent.name,
                "original_split": split,
                "source_group": source_group(path),
                "sha256": digest(path),
                "dhash": dhash(path),
            })
    if not records:
        raise ValueError(f"No images under {args.source}")

    parent = list(range(len(records)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a

    # Same basename family is authoritative regardless of perceptual distance.
    family_members: dict[str, list[int]] = defaultdict(list)
    exact_members: dict[str, list[int]] = defaultdict(list)
    for i, record in enumerate(records):
        family_members[record["source_group"]].append(i)
        exact_members[record["sha256"]].append(i)
    for members in (*family_members.values(), *exact_members.values()):
        for index in members[1:]:
            union(members[0], index)

    all_edges = []
    cross_split_edges = []
    distance_counts = Counter()
    cross_label_edges = []
    for i, left in enumerate(records):
        for j in range(i + 1, len(records)):
            right = records[j]
            distance = (left["dhash"] ^ right["dhash"]).bit_count()
            if distance <= 3:
                all_edges.append((i, j, distance))
                distance_counts[distance] += 1
                union(i, j)
                if left["original_split"] != right["original_split"]:
                    cross_split_edges.append((i, j, distance))
                if left["label"] != right["label"]:
                    cross_label_edges.append((i, j, distance))

    components: dict[int, list[int]] = defaultdict(list)
    for i in range(len(records)):
        components[find(i)].append(i)

    manual_holds = {}
    with args.label_holds.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["decision"] == "UNKNOWN":
                manual_holds[row["file"]] = row["reason"]

    component_state = {}
    quarantine_rows = []
    for component_id, members in components.items():
        labels = sorted({records[i]["label"] for i in members})
        source_files = [records[i]["path"].as_posix() for i in members]
        manual_reasons = [manual_holds[path] for path in source_files if path in manual_holds]
        if len(labels) > 1:
            reason = "Conflicting labels within a visually linked component: " + ", ".join(labels)
            state = "MIXED_LABEL_COMPONENT"
        elif manual_reasons:
            reason = "Manual visual label hold: " + sorted(set(manual_reasons))[0]
            state = "MANUAL_LABEL_HOLD"
        else:
            reason = ""
            state = "KEEP"
        component_state[component_id] = (state, labels[0] if len(labels) == 1 else "", reason)
        if state != "KEEP":
            for i in members:
                quarantine_rows.append({
                    "source_file": records[i]["path"].as_posix(),
                    "source_split": records[i]["original_split"],
                    "source_label": records[i]["label"],
                    "decision": state,
                    "component_id": component_id,
                    "reason": reason,
                    "sha256": records[i]["sha256"],
                })

    kept_by_label: dict[str, list[tuple[int, list[int]]]] = defaultdict(list)
    for component_id, members in components.items():
        state, label, _ = component_state[component_id]
        if state == "KEEP":
            kept_by_label[label].append((component_id, members))

    rng = random.Random(args.seed)
    assignment = {}
    component_counts = {}
    for label, groups in sorted(kept_by_label.items()):
        rng.shuffle(groups)
        count = len(groups)
        if count < 3:
            raise ValueError(f"Class {label} has only {count} independent groups")
        n_train = max(1, round(count * 0.70))
        n_validation = max(1, round(count * 0.15))
        if n_train + n_validation >= count:
            n_train, n_validation = count - 2, 1
        for index, (component_id, members) in enumerate(groups):
            split = "train" if index < n_train else "validation" if index < n_train + n_validation else "test"
            assignment[component_id] = split
        component_counts[label] = {
            "groups": count,
            "trainGroups": n_train,
            "validationGroups": n_validation,
            "testGroups": count - n_train - n_validation,
        }

    args.out.mkdir(parents=True)
    manifest_rows = []
    class_counts = {split: Counter() for split in ("train", "validation", "test")}
    for label, groups in sorted(kept_by_label.items()):
        for component_id, members in groups:
            split = assignment[component_id]
            selected = members if split == "train" else [min(members, key=lambda i: records[i]["sha256"])]
            group_hash = hashlib.sha256("\n".join(sorted(records[i]["sha256"] for i in members)).encode()).hexdigest()
            selected_ids = set(selected)
            for i in members:
                record = records[i]
                if i in selected_ids:
                    destination = args.out / split / label / record["path"].name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    copy2(record["path"], destination)
                    class_counts[split][label] += 1
                    disposition = "COPIED"
                    dest_path = destination.as_posix()
                else:
                    disposition = "SAME_GROUP_HOLDOUT_SIBLING_NOT_EVALUATED"
                    dest_path = ""
                manifest_rows.append({
                    "source_file": record["path"].as_posix(),
                    "original_split": record["original_split"],
                    "source_label": label,
                    "new_split": split,
                    "group_id": group_hash,
                    "decision": disposition,
                    "new_file": dest_path,
                    "sha256": record["sha256"],
                })
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    with args.manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(manifest_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(manifest_rows)
    with args.quarantine.open("w", newline="", encoding="utf-8") as stream:
        fields = ["source_file", "source_split", "source_label", "decision", "component_id", "reason", "sha256"]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(quarantine_rows)
    output = {
        "source": args.source.as_posix(),
        "output": args.out.as_posix(),
        "seed": args.seed,
        "inputFiles": len(records),
        "retainedTrainValidationTestFiles": {split: sum(counts.values()) for split, counts in class_counts.items()},
        "retainedClassCounts": {split: dict(sorted(counts.items())) for split, counts in class_counts.items()},
        "retainedComponentsByClass": component_counts,
        "manualUnknownImages": len(manual_holds),
        "quarantinedComponentFiles": len(quarantine_rows),
        "quarantineByReason": dict(Counter(row["decision"] for row in quarantine_rows)),
        "visualNearDuplicateEdgesAcrossAllSplits": len(all_edges),
        "visualNearDuplicateDistanceCountsAcrossAllSplits": dict(sorted(distance_counts.items())),
        "originalCrossSplitNearDuplicateEdges": len(cross_split_edges),
        "crossLabelNearDuplicateEdges": len(cross_label_edges),
        "crossLabelComponentCount": sum(1 for state, _, _ in component_state.values() if state == "MIXED_LABEL_COMPONENT"),
        "outputSplitMethod": "Union exact source filename families, exact hashes and every dHash<=3 pair across all source partitions. Remove visually linked mixed-label components and manual label holds. Assign independent components per label by seed 42. Keep all training variants; use one deterministic image per component in validation/test.",
        "postBuildLeakageAudit": "REQUIRED",
        "warning": "This is a local staging split of a previously rejected candidate source. It is not the final V2 dataset; its source labels and negative-class semantics still need broader review, and it contains no real-world camera data.",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
