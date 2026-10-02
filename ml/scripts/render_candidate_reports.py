"""Render the isolated candidate-v2 metrics as reviewable CSV, Markdown and PNGs."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def main() -> None:
    data = json.loads((REPORTS / "candidate_v2_evaluation.json").read_text())
    data["modelVersion"] = "candidate-v2 experiment; rejected for deployment"
    data["releaseStatus"] = "REJECTED: six-class e-waste accuracy regressed from 59/60 to 52/60; adapter challenge was labeled not_e_waste."
    data["testSet"] = "175 images: 60 unchanged selected e-waste test images + 115 negatives from original source test partitions"
    (REPORTS / "evaluation_report.json").write_text(json.dumps(data, indent=2) + "\n")

    classes = data["confusionMatrixLabels"]
    cm = data["confusionMatrix"]
    details = data["perClass"]
    with (REPORTS / "per_class_metrics.csv").open("w", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["class", "precision", "recall", "f1_score", "support"])
        for name in classes:
            row = details[name]
            writer.writerow([name, row["precision"], row["recall"], row["f1-score"], int(row["support"])])

    lines = [
        "# Candidate-v2 evaluation report",
        "",
        "> **Rejected for deployment.** This is an offline experiment, not a production result.",
        "",
        f"Test set: {data['testImages']} images (60 existing e-waste test examples + 115 negatives). Test images were not used for training or model selection.",
        "",
        "| Metric | Candidate-v2 |",
        "|---|---:|",
        f"| Accuracy | {data['accuracy']:.4%} |",
        f"| Macro precision | {data['macroPrecision']:.4%} |",
        f"| Macro recall | {data['macroRecall']:.4%} |",
        f"| Macro F1 | {data['macroF1']:.4%} |",
        f"| Weighted F1 | {data['weightedF1']:.4%} |",
        "",
        "## Per-class results",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in classes:
        row = details[name]
        lines.append(f"| {name} | {row['precision']:.3f} | {row['recall']:.3f} | {row['f1-score']:.3f} | {int(row['support'])} |")
    lines += ["", "## Confusion matrix", "", "Rows are actual labels; columns are predicted labels, in the class order shown.", "", "```text"]
    lines += [str(row) for row in cm]
    lines += ["```", "", "## Release decision", "", "On the same 60 supported e-waste test images, production v1 scored 59/60 and candidate-v2 scored 52/60. Candidate-v2 also rejected the charger challenge as not e-waste. The candidate was not integrated into Java or deployed. The production model remains v1.", ""]
    (REPORTS / "evaluation_report.md").write_text("\n".join(lines))

    # Confusion-matrix heatmap, labeled with actual and predicted categories.
    cell, left, top, right, bottom = 95, 260, 140, 90, 150
    width, height = left + len(classes) * cell + right, top + len(classes) * cell + bottom
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, label_font, number_font = font(26, True), font(14), font(17, True)
    draw.text((left, 30), "Candidate-v2 confusion matrix", fill="#24563f", font=title_font)
    maximum = max(max(row) for row in cm) or 1
    for index, name in enumerate(classes):
        draw.text((left - 12, top + index * cell + 35), name, fill="#202b25", font=label_font, anchor="rm")
        draw.text((left + index * cell + cell // 2, top - 12), name.replace("_", " "), fill="#202b25", font=label_font, anchor="mb")
    draw.text((left + len(classes) * cell // 2, height - 45), "Predicted", fill="#24563f", font=label_font, anchor="mm")
    for row in range(len(classes)):
        for col in range(len(classes)):
            value = cm[row][col]
            intensity = int(245 - 150 * value / maximum)
            color = (intensity, min(255, intensity + 8), min(255, intensity + 3))
            x0, y0 = left + col * cell, top + row * cell
            draw.rectangle((x0, y0, x0 + cell, y0 + cell), fill=color, outline="#d2ddd6", width=2)
            draw.text((x0 + cell // 2, y0 + cell // 2), str(value), fill="#12251a", font=number_font, anchor="mm")
    image.save(REPORTS / "confusion_matrix.png")

    # Source class distribution (original archive labels) using the same local Pillow renderer.
    dataset = json.loads((REPORTS / "dataset_report.json").read_text())
    inventory = dataset["classInventory"]
    labels = [row["sourceClass"] for row in inventory]
    values = [row["images"] for row in inventory]
    chart = Image.new("RGB", (1500, 820), "white")
    d = ImageDraw.Draw(chart)
    d.text((80, 36), "Source class-labeled images (2,153 of 2,157)", fill="#24563f", font=font(28, True))
    chart_left, chart_top, chart_width, chart_height = 230, 110, 1160, 610
    max_count = max(values)
    bar_h, gap = 31, 17
    for i, (label, value) in enumerate(zip(labels, values)):
        y = chart_top + i * (bar_h + gap)
        d.text((chart_left - 12, y + bar_h // 2), label, fill="#202b25", font=font(16), anchor="rm")
        w = int(chart_width * value / max_count)
        d.rounded_rectangle((chart_left, y, chart_left + w, y + bar_h), radius=5, fill="#327356")
        d.text((chart_left + w + 9, y + bar_h // 2), str(value), fill="#202b25", font=font(15, True), anchor="lm")
    d.text((80, 770), "Train + validation + test source counts; source labels, not candidate output classes.", fill="#53635a", font=font(14))
    chart.save(REPORTS / "class_distribution.png")


if __name__ == "__main__":
    main()
