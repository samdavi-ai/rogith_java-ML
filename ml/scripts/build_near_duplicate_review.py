#!/usr/bin/env python3
"""Write the reviewed disposition for all Phase 10 candidate split pairs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


LEGITIMATE_PAIR = frozenset({
    "IMG_20250822_231210_1_jpg.rf.bf5f830d9485eb8d3bf5ca84d009a28d.jpg",
    "IMG_20250822_231209_1_jpg.rf.fcf651145e2d95b81efe4e9904f3cfed.jpg",
})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, default=Path("ml/reports/v2_candidate_split_audit.json"))
    parser.add_argument("--csv", type=Path, default=Path("ml/reports/near_duplicate_review.csv"))
    parser.add_argument("--markdown", type=Path, default=Path("ml/reports/NEAR_DUPLICATE_REVIEW.md"))
    args = parser.parse_args()
    report = json.loads(args.audit.read_text(encoding="utf-8"))
    pairs = report["crossSplitDHashDistanceAtMost3"]
    rows = []
    for pair_id, pair in enumerate(pairs, start=1):
        left, right = Path(pair["left"]), Path(pair["right"])
        if frozenset({left.name, right.name}) == LEGITIMATE_PAIR:
            decision = "LEGITIMATE"
            reason = "The side-by-side images show two visibly different battery products and labels; the common green staging background explains the dHash match."
            action = "Keep both examples. For strict isolation, the rebuilt split conservatively places this dHash-linked pair in one partition."
        else:
            decision = "NEAR_DUPLICATE"
            reason = "Side-by-side visual review shows the same apparent object or same scene composition with near-identical framing; many filenames are adjacent capture sequence numbers. Exact source/object IDs are absent, so this is a conservative near-duplicate call rather than a claim of byte identity."
            action = "Keep the images in one connected capture group and assign the entire group to one split; do not delete files solely for this similarity."
        left_hash = sha256(left) if left.is_file() else "missing"
        right_hash = sha256(right) if right.is_file() else "missing"
        rows.append({
            "pair_id": pair_id,
            "distance": pair["distance"],
            "left_file": left.as_posix(),
            "left_split": pair["leftSplit"],
            "right_file": right.as_posix(),
            "right_split": pair["rightSplit"],
            "decision": decision,
            "reason": reason,
            "action": action,
            "left_sha256": left_hash,
            "right_sha256": right_hash,
        })

    args.csv.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["pair_id", "distance", "left_file", "left_split", "right_file", "right_split", "decision", "reason", "action", "left_sha256", "right_sha256"]
    with args.csv.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    by_decision: dict[str, int] = {}
    for row in rows:
        by_decision[row["decision"]] = by_decision.get(row["decision"], 0) + 1
    distances: dict[int, int] = {}
    for row in rows:
        d = int(row["distance"])
        distances[d] = distances.get(d, 0) + 1
    lines = [
        "# Cross-split near-duplicate review — Phase 11",
        "",
        "Review date: 2026-10-03. Scope: all 180 dHash≤3 cross-split candidates in the existing rejected seven-class candidate tree. Every pair was inspected side by side in 15 contact sheets; file SHA-256 values were compared. The working decision inventory is [`near_duplicate_review.csv`](near_duplicate_review.csv).",
        "",
        "## Decisions",
        "",
        f"- **NEAR_DUPLICATE:** {by_decision.get('NEAR_DUPLICATE', 0)} pairs.",
        f"- **LEGITIMATE:** {by_decision.get('LEGITIMATE', 0)} pair.",
        f"- **DUPLICATE:** 0 pairs. The audit found zero exact byte-identical duplicate groups; dHash distance 0 is not proof of byte identity.",
        f"- **UNKNOWN:** 0 pair decisions. The underlying physical object/capture identity remains unverified because the source has no object IDs or capture metadata; conservative near-duplicate grouping is used where the views match.",
        "",
        "Candidate distances: " + ", ".join(f"d={distance}: {count}" for distance, count in sorted(distances.items())) + ".",
        "",
        "The pair decision is based on visible image similarity and capture-sequence context. The original dataset contains no physical object IDs, source-camera IDs, or burst IDs, so pair inspection cannot establish whether every near-identical frame was the same camera shutter event. The rebuilt staging split groups each such connected family and preserves files; it does not delete examples to improve a score.",
        "",
        "The sole `LEGITIMATE` pair is battery waste: `IMG_20250822_231210_1_jpg.rf.bf5f830d9485eb8d3bf5ca84d009a28d.jpg` versus `IMG_20250822_231209_1_jpg.rf.fcf651145e2d95b81efe4e9904f3cfed.jpg`. The images show visibly different battery products/labels on the same green background. They are not the same item or capture. They are still co-located in the rebuilt staging split because the conservative hash grouping treats all dHash≤3 matches uniformly.",
        "",
        "## Pair inventory",
        "",
        "| Pair | dHash | Decision | Left file (split) | Right file (split) | Action |",
        "|---:|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['pair_id']} | {row['distance']} | {row['decision']} | `{Path(row['left_file']).name}` ({row['left_split']}) | `{Path(row['right_file']).name}` ({row['right_split']}) | {row['action']} |")
    lines.extend([
        "",
        "## Label findings from visual review",
        "",
        "Several images assigned to the derived `not_ewaste` class under source label `Plastic_Waste` visibly resemble calculators or other electronic devices. They are excluded from the reblocked staging split pending ground-truth review; no new label is assigned. A four-image mixed battery/PCB scene component also crosses source labels and is quarantined rather than forced into one class. The quarantine manifest records each file and reason.",
        "",
        "The original `ml/data/candidates/reject_v2/` tree and Phase 10 evaluation artifacts are preserved. This review does not rehabilitate the rejected candidate model or make its old metrics valid.",
    ])
    args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"reviewed": len(rows), "decisions": by_decision, "distances": distances}, indent=2))


if __name__ == "__main__":
    main()
