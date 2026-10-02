"""Generate Python ONNX top-k references and run Java image-to-prediction parity tests."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path
import sys

import numpy as np
import onnxruntime as ort
import tensorflow as tf

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.training.train import load_class_map, make_dataset

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "ml/data/processed/classification/test")
    parser.add_argument("--onnx", type=Path, default=ROOT / "ml/models/ewaste.onnx")
    parser.add_argument("--classes", type=Path, default=ROOT / "ml/class_mapping.json")
    parser.add_argument("--mvn", default="mvn")
    parser.add_argument("--java-home", type=Path, required=True)
    args = parser.parse_args()
    classes = load_class_map(args.classes)
    files = [path for entry in classes for path in sorted((args.data / entry["name"]).glob("*")) if path.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not files:
        raise SystemExit(f"No image files found under {args.data}")

    session = ort.InferenceSession(str(args.onnx), providers=["CPUExecutionProvider"])
    input_meta, output_meta = session.get_inputs()[0], session.get_outputs()[0]
    dataset = make_dataset(args.data.parent, args.data.name, classes, 1, False)
    if dataset.cardinality().numpy() != len(files):
        raise SystemExit(f"Dataset order/count mismatch: files={len(files)}, TensorFlow={dataset.cardinality().numpy()}")
    records = []
    for path, (image, _) in zip(files, dataset):
        x = image.numpy()
        logits = session.run([output_meta.name], {input_meta.name: x})[0]
        row = tf.nn.softmax(logits, axis=-1).numpy()[0]
        record = {"path": str(path.resolve()), "actual": path.parent.name}
        order = np.argsort(row)[::-1][:4]
        record["topK"] = [{"category": classes[int(i)]["displayName"], "probability": float(row[i])} for i in order]
        records.append(record)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump({"records": records}, tmp)
        reference_path = Path(tmp.name)
    env = os.environ.copy()
    env["JAVA_HOME"] = str(args.java_home.resolve())
    env["PATH"] = f"{args.java_home.resolve() / 'bin'}:{env.get('PATH', '')}"
    try:
        completed = subprocess.run(
            [args.mvn, "-f", str(ROOT / "backend/pom.xml"), "-Dtest=OnnxClassifierParityTest",
             f"-Drecolens.parity.reference={reference_path}", "test", "-q"],
            cwd=ROOT / "backend", env=env, text=True, check=False,
        )
        if completed.returncode:
            raise SystemExit(completed.returncode)
        print(json.dumps({"status": "PASS", "images": len(records), "reference": "repository TensorFlow image loader/preprocessing + Python ONNX Runtime", "java": "ONNX Runtime + ImageIO/Graphics2D", "maxTop4ProbabilityDeltaLimit": 0.02}, indent=2))
    finally:
        reference_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
