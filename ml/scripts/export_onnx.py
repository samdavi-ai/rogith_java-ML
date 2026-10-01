"""Export and validate the selected Keras checkpoint as a CPU ONNX model."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import tensorflow as tf
import tf2onnx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.training.train import IMAGE_SIZE, SEED, load_class_map, make_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, default=Path("ml/models/best_model.keras"))
    parser.add_argument("--data", type=Path, default=Path("ml/data/processed/classification"))
    parser.add_argument("--classes", type=Path, default=Path("ml/classes.json"))
    parser.add_argument("--out", type=Path, default=Path("ml/models/onnx/ewaste_mobilenetv2.onnx"))
    parser.add_argument("--report", type=Path, default=Path("ml/reports/onnx_validation.json"))
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    model = tf.keras.models.load_model(args.model)
    spec = (tf.TensorSpec((None, 3, *IMAGE_SIZE), tf.float32, name="image"),)
    converted, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=17, output_path=str(args.out))
    onnx.checker.check_model(converted)
    session = ort.InferenceSession(str(args.out), providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    outputs = session.get_outputs()
    if len(inputs) != 1 or len(outputs) != 1:
        raise ValueError(f"Expected one model input and output, got {len(inputs)} and {len(outputs)}")
    classes = load_class_map(args.classes)
    if outputs[0].shape[-1] != len(classes):
        raise ValueError(f"Output count {outputs[0].shape[-1]} != class count {len(classes)}")
    validation = make_dataset(args.data, "validation", classes, 16, False)
    max_abs = 0.0
    max_rel = 0.0
    checked = 0
    agreements = 0
    for images, _ in validation.take(4):
        tensor = images.numpy()
        keras_logits = model(tensor, training=False).numpy()
        onnx_logits = session.run([outputs[0].name], {inputs[0].name: tensor})[0]
        max_abs = max(max_abs, float(np.max(np.abs(keras_logits - onnx_logits))))
        max_rel = max(max_rel, float(np.max(np.abs(keras_logits - onnx_logits) / np.maximum(np.abs(keras_logits), 1e-6))))
        agreements += int(np.sum(keras_logits.argmax(axis=1) == onnx_logits.argmax(axis=1)))
        checked += int(len(tensor))
    if max_abs > 1e-4 or agreements != checked:
        raise AssertionError(f"ONNX parity failed: max_abs={max_abs}, agreements={agreements}/{checked}")
    model_proto = onnx.load(str(args.out))
    report = {
        "status": "PASS",
        "path": str(args.out),
        "sizeBytes": args.out.stat().st_size,
        "input": {"name": inputs[0].name, "shape": inputs[0].shape, "type": inputs[0].type},
        "output": {"name": outputs[0].name, "shape": outputs[0].shape, "type": outputs[0].type},
        "opset": model_proto.opset_import[0].version,
        "providers": session.get_providers(),
        "validationImagesCompared": checked,
        "kerasOnnxArgmaxAgreements": agreements,
        "maxAbsoluteLogitDifference": max_abs,
        "maxRelativeLogitDifference": max_rel,
        "classesFile": str(args.classes),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
