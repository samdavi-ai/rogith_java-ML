"""Validate an existing ONNX export against the selected Keras model and validation images."""
from __future__ import annotations
import argparse, json, statistics, time
from pathlib import Path
import numpy as np
import onnxruntime as ort
import tensorflow as tf
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.training.train import IMAGE_SIZE, load_class_map, make_dataset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, default=Path('ml/models/best_model.keras'))
    parser.add_argument('--onnx', type=Path, default=Path('ml/models/ewaste.onnx'))
    parser.add_argument('--data', type=Path, default=Path('ml/data/processed/classification'))
    parser.add_argument('--classes', type=Path, default=Path('ml/class_mapping.json'))
    parser.add_argument('--report', type=Path, default=Path('ml/reports/onnx_validation.json'))
    args = parser.parse_args()
    if not args.onnx.is_file(): raise FileNotFoundError(args.onnx)
    model = tf.keras.models.load_model(args.model)
    classes = load_class_map(args.classes)
    dataset = make_dataset(args.data, 'validation', classes, 1, False)
    session = ort.InferenceSession(str(args.onnx), providers=['CPUExecutionProvider'])
    inp, out = session.get_inputs()[0], session.get_outputs()[0]
    if inp.type != 'tensor(float)' or out.type != 'tensor(float)': raise ValueError('ONNX input/output must be float32')
    if len(inp.shape) != 4 or inp.shape[1:] != [3, *IMAGE_SIZE]: raise ValueError(f'Unexpected ONNX input: {inp.shape}')
    if len(out.shape) != 2 or out.shape[-1] != len(classes): raise ValueError(f'Unexpected ONNX output: {out.shape}')
    checked = agreements = 0
    max_abs = max_prob_delta = 0.0
    latencies_ms = []
    for image_batch, _ in dataset:
        image = image_batch.numpy()
        expected = model(image, training=False).numpy()
        started = time.perf_counter()
        actual = session.run([out.name], {inp.name: image})[0]
        latencies_ms.append((time.perf_counter() - started) * 1000)
        max_abs = max(max_abs, float(np.max(np.abs(expected - actual))))
        p1, p2 = tf.nn.softmax(expected, -1).numpy(), tf.nn.softmax(actual, -1).numpy()
        max_prob_delta = max(max_prob_delta, float(np.max(np.abs(p1-p2))))
        agreements += int(np.sum(expected.argmax(-1) == actual.argmax(-1)))
        checked += len(image)
    report = {'status':'PASS' if agreements == checked and max_abs <= 1e-4 else 'FAIL', 'onnxPath':str(args.onnx), 'imagesCompared':checked, 'argmaxAgreements':agreements, 'maxAbsoluteLogitDifference':max_abs, 'maxProbabilityDifference':max_prob_delta, 'singleImageLatencyMs':{'median':statistics.median(latencies_ms),'p95':float(np.percentile(latencies_ms,95)),'max':max(latencies_ms)},'input':{'name':inp.name,'shape':inp.shape,'type':inp.type},'output':{'name':out.name,'shape':out.shape,'type':out.type}}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
    if report['status'] != 'PASS': raise SystemExit(1)
if __name__ == '__main__': main()
