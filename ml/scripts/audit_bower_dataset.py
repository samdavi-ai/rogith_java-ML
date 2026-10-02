"""Audit the public Bower validation Parquet without exporting image bytes."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image, ImageOps


EWASTE_OBJECTS = {"battery", "bulb", "electronic device", "e-cigarette"}
EWASTE_MATERIAL = "electronic waste"


def dhash(image: Image.Image) -> int:
    image = ImageOps.exif_transpose(image).convert("L").resize((9, 8), Image.Resampling.LANCZOS)
    pixels = list(image.getdata())
    value = 0
    for row in range(8):
        for col in range(8):
            value = (value << 1) | int(pixels[row * 9 + col] > pixels[row * 9 + col + 1])
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=Path("ml/reports/bower_dataset_audit.json"))
    args = parser.parse_args()

    table = pq.read_table(args.parquet, columns=["image_id", "image", "material", "object", "image_width", "image_height"])
    rows = table.to_pylist()
    by_id: dict[str, dict] = {}
    annotations = defaultdict(list)
    for row in rows:
        image_id = row["image_id"]
        blob = row["image"]["bytes"]
        annotations[image_id].append({"material": row["material"], "object": row["object"]})
        if image_id not in by_id:
            by_id[image_id] = {"bytes": blob, "declared": set()}
        elif by_id[image_id]["bytes"] != blob:
            by_id[image_id].setdefault("byteConflicts", 0)
            by_id[image_id]["byteConflicts"] += 1
        by_id[image_id]["declared"].add((row["image_width"], row["image_height"]))

    corrupt, dimension_mismatches = [], []
    hashes: dict[str, list[str]] = defaultdict(list)
    fingerprints = []
    dimensions = Counter()
    formats = Counter()
    small_images = []
    object_counts, material_counts = Counter(), Counter()
    image_counts_by_object, image_counts_by_material = defaultdict(set), defaultdict(set)
    image_labels, label_conflicts = {}, []
    for image_id, record in sorted(by_id.items()):
        blob = record["bytes"]
        digest = hashlib.sha256(blob).hexdigest()
        hashes[digest].append(image_id)
        objects = {a["object"].strip().lower() for a in annotations[image_id] if a["object"]}
        materials = {a["material"].strip().lower() for a in annotations[image_id] if a["material"]}
        object_counts.update(a["object"] for a in annotations[image_id] if a["object"])
        material_counts.update(a["material"] for a in annotations[image_id] if a["material"])
        for obj in objects: image_counts_by_object[obj].add(image_id)
        for material in materials: image_counts_by_material[material].add(image_id)
        try:
            with Image.open(BytesIO(blob)) as image:
                image.verify()
            with Image.open(BytesIO(blob)) as image:
                image_format = image.format or "unknown"
                image = ImageOps.exif_transpose(image)
                actual = image.size
                dimensions[f"{actual[0]}x{actual[1]}"] += 1
                formats[image_format] += 1
                if min(actual) < 224:
                    small_images.append({"imageId": image_id, "size": list(actual)})
                declared = record["declared"]
                if not any((width, height) == actual for width, height in declared):
                    dimension_mismatches.append({"imageId": image_id, "declared": sorted([list(x) for x in declared]), "actual": list(actual)})
                fingerprints.append((image_id, dhash(image)))
        except Exception as exc:
            corrupt.append({"imageId": image_id, "error": type(exc).__name__})
        positive = EWASTE_MATERIAL in materials or bool(objects & EWASTE_OBJECTS)
        known = bool(objects or materials)
        image_labels[image_id] = "E_WASTE" if positive else "NOT_E_WASTE" if known else "UNLABELED"
        if not known:
            label_conflicts.append(image_id)

    duplicate_groups = [ids for ids in hashes.values() if len(ids) > 1]
    near_pairs = []
    for i, (left_id, left_hash) in enumerate(fingerprints):
        for right_id, right_hash in fingerprints[i + 1:]:
            distance = (left_hash ^ right_hash).bit_count()
            if distance <= 3:
                near_pairs.append({"leftId": left_id, "rightId": right_id, "dHashDistance": distance})
    binary_counts = Counter(image_labels.values())
    report = {
        "dataset": "BowerApp/bower-waste-annotations",
        "sourceParquet": str(args.parquet),
        "sourceParquetSha256": hashlib.sha256(args.parquet.read_bytes()).hexdigest(),
        "license": "MIT (published dataset card)",
        "rowAnnotations": len(rows),
        "uniqueImageIds": len(by_id),
        "uniqueImageByteHashes": len(hashes),
        "duplicateImageGroups": duplicate_groups,
        "annotationRowsByObject": dict(object_counts),
        "uniqueImagesByObject": {k: len(v) for k, v in sorted(image_counts_by_object.items())},
        "annotationRowsByMaterial": dict(material_counts),
        "uniqueImagesByMaterial": {k: len(v) for k, v in sorted(image_counts_by_material.items())},
        "imageFormatCounts": dict(formats),
        "dimensionDistribution": dict(dimensions),
        "imagesBelow224Px": small_images,
        "imagesWithMultipleAnnotations": sum(len(value) > 1 for value in annotations.values()),
        "annotationRowsPerImageDistribution": dict(Counter(str(len(value)) for value in annotations.values())),
        "derivedFrameLabels": {"E_WASTE": binary_counts["E_WASTE"], "NOT_E_WASTE": binary_counts["NOT_E_WASTE"], "UNLABELED": binary_counts["UNLABELED"]},
        "derivation": "Frame is E_WASTE when any annotation material is Electronic Waste or object is Battery, Bulb, Electronic Device or E-cigarette; NOT_E_WASTE when known labels exist and no positive label; null-only images are UNLABELED.",
        "corruptImages": corrupt,
        "dimensionMismatches": dimension_mismatches,
        "imageIdByteConflicts": {k: v.get("byteConflicts", 0) for k, v in by_id.items() if v.get("byteConflicts")},
        "unlabeledImageIds": label_conflicts,
        "nearDuplicatePairsDHashLe3": len(near_pairs),
        "nearDuplicateExamples": near_pairs[:100],
        "parquetBytes": args.parquet.stat().st_size,
        "imagesExported": False,
        "status": "FAIL" if corrupt or dimension_mismatches or label_conflicts or any(v.get("byteConflicts") for v in by_id.values()) else "PASS_WITH_NEAR_DUPLICATE_REVIEW",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary = {k: report[k] for k in ("status", "rowAnnotations", "uniqueImageIds", "uniqueImageByteHashes", "derivedFrameLabels", "corruptImages", "dimensionMismatches", "imagesBelow224Px", "nearDuplicatePairsDHashLe3")}
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
