"""One-shot held-out evaluation and out-of-domain characterization."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_score, recall_score

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.training.train import IMAGE_SIZE, SEED, load_class_map, make_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("ml/data/processed/classification"))
    parser.add_argument("--ood-data", type=Path, default=Path("ml/data/processed/ood_test"))
    parser.add_argument("--classes", type=Path, default=Path("ml/classes.json"))
    parser.add_argument("--model", type=Path, default=Path("ml/models/best_model.keras"))
    parser.add_argument("--out", type=Path, default=Path("ml/reports/evaluation.json"))
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(f"Refusing to overwrite prior test evaluation: {args.out}")
    classes = load_class_map(args.classes)
    model = tf.keras.models.load_model(args.model)
    test_ds = make_dataset(args.data, "test", classes, 16, False)
    y_true = np.concatenate([labels.numpy() for _, labels in test_ds])
    logits = model.predict(test_ds, verbose=0)
    probabilities = tf.nn.softmax(logits, axis=-1).numpy()
    y_pred = probabilities.argmax(axis=1)
    names = [entry["name"] for entry in classes]
    report = classification_report(y_true, y_pred, labels=np.arange(len(classes)), target_names=names, output_dict=True, zero_division=0)
    confusion = confusion_matrix(y_true, y_pred, labels=np.arange(len(classes)))
    errors = []
    for true_id, pred_id, row in zip(y_true, y_pred, probabilities):
        if true_id != pred_id:
            errors.append({"true": names[int(true_id)], "predicted": names[int(pred_id)], "confidence": float(row[int(pred_id)])})

    ood_result: dict = {"evaluatedImages": 0, "bySourceClass": {}, "confidentForcedPredictions": 0, "threshold": 0.85}
    if args.ood_data.is_dir():
        ood_by_class: dict[str, dict] = {}
        all_confidences: list[float] = []
        for class_dir in sorted(p for p in args.ood_data.iterdir() if p.is_dir()):
            files = sorted(p for p in class_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
            if not files:
                continue
            dataset = tf.keras.utils.image_dataset_from_directory(
                args.ood_data,
                labels="inferred", label_mode="int", class_names=sorted(p.name for p in args.ood_data.iterdir() if p.is_dir()),
                color_mode="rgb", image_size=IMAGE_SIZE, batch_size=16, shuffle=False, seed=SEED,
                interpolation="bilinear", crop_to_aspect_ratio=False,
            )
            selected_index = dataset.class_names.index(class_dir.name)
            x_batches = []
            y_batches = []
            for x, y in dataset:
                mask = tf.equal(y, selected_index)
                if bool(tf.reduce_any(mask)):
                    x_batches.append(tf.boolean_mask(x, mask))
                    y_batches.append(tf.boolean_mask(y, mask))
            if not x_batches:
                continue
            x = tf.concat(x_batches, axis=0)
            nchw = tf.transpose(tf.cast(x, tf.float32) / 127.5 - 1.0, [0, 3, 1, 2])
            probs = tf.nn.softmax(model.predict(nchw, verbose=0), axis=-1).numpy()
            preds = probs.argmax(axis=1)
            confidence = probs.max(axis=1)
            all_confidences.extend(confidence.tolist())
            counts = {name: int(np.sum(preds == i)) for i, name in enumerate(names)}
            ood_by_class[class_dir.name] = {
                "images": len(files), "topPredictions": counts,
                "meanMaxConfidence": float(confidence.mean()),
                "maxConfidenceAtLeast85Percent": int(np.sum(confidence >= 0.85)),
            }
        ood_result = {
            "evaluatedImages": len(all_confidences), "bySourceClass": ood_by_class,
            "meanMaxConfidence": float(np.mean(all_confidences)) if all_confidences else None,
            "confidentForcedPredictions": int(np.sum(np.asarray(all_confidences) >= 0.85)),
            "threshold": 0.85,
            "interpretation": "This closed-set classifier always chooses one supported class; results are not an unknown-class detector.",
        }

    metrics = {
        "testImages": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macroPrecision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "macroRecall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "macroF1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weightedF1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "perClass": report,
        "confusionMatrix": confusion.tolist(),
        "confusionMatrixLabels": names,
        "misclassifiedCountsByConfusion": {f"{e['true']}->{e['predicted']}": sum(x["true"] == e["true"] and x["predicted"] == e["predicted"] for x in errors) for e in errors},
        "misclassifiedExamples": errors[:40],
        "ood": ood_result,
        "testUsedForSelection": False,
        "preprocessing": "RGB, bilinear stretch resize 224x224, pixel/127.5 - 1.0, NCHW float32",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("testImages", "accuracy", "macroPrecision", "macroRecall", "macroF1", "weightedF1")}, indent=2))


if __name__ == "__main__":
    main()
