"""Build a persistent Python/ONNX fixture and run the Java parity test."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
import sys
import zipfile

import numpy as np
import onnxruntime as ort
import tensorflow as tf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ml.training.train import load_class_map, make_dataset

ROOT = Path(__file__).resolve().parents[2]


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def softmax64(logits: np.ndarray) -> np.ndarray:
    values = logits.astype(np.float64)
    exps = np.exp(values - values.max())
    return exps / exps.sum()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=ROOT / "ml/data/processed/classification/test")
    parser.add_argument("--onnx", type=Path, default=ROOT / "ml/models/ewaste.onnx")
    parser.add_argument("--classes", type=Path, default=ROOT / "ml/class_mapping.json")
    parser.add_argument("--mvn", default="mvn")
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--fixture-dir", type=Path, default=ROOT / "ml/parity/phase9")
    args = parser.parse_args()
    classes = load_class_map(args.classes)
    files = [path for entry in classes for path in sorted((args.data / entry["name"]).glob("*")) if path.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    if not files:
        raise SystemExit(f"No image files found under {args.data}")

    fixture = args.fixture_dir.resolve()
    images_dir = fixture / "images"
    shutil.rmtree(fixture, ignore_errors=True)
    images_dir.mkdir(parents=True)
    session = ort.InferenceSession(str(args.onnx), providers=["CPUExecutionProvider"])
    input_meta, output_meta = session.get_inputs()[0], session.get_outputs()[0]
    dataset = make_dataset(args.data.parent, args.data.name, classes, 1, False)
    if dataset.cardinality().numpy() != len(files):
        raise SystemExit(f"Dataset order/count mismatch: files={len(files)}, TensorFlow={dataset.cardinality().numpy()}")

    records = []
    preprocessing_probes = []
    with zipfile.ZipFile(fixture / "preprocessed_nchw_f32.zip", "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as tensors:
        for index, (path, (image, _)) in enumerate(zip(files, dataset)):
            x = image.numpy()[0].astype("<f4", copy=False)
            encoded = tf.io.read_file(str(path))
            decoded = (tf.io.decode_png(encoded, channels=3) if path.suffix.lower() == ".png"
                       else tf.io.decode_jpeg(encoded, channels=3, dct_method="INTEGER_ACCURATE")).numpy()
            logits = session.run([output_meta.name], {input_meta.name: image.numpy()})[0][0]
            probabilities = softmax64(logits)
            order = np.argsort(probabilities)[::-1]
            legacy_rgb = tf.io.decode_image(tf.io.read_file(str(path)), channels=3, expand_animations=False)
            legacy_nchw = tf.transpose(tf.image.resize(legacy_rgb, (224, 224), method="bilinear") / 127.5 - 1.0, [2, 0, 1]).numpy().astype("<f4", copy=False)
            legacy_logits = session.run([output_meta.name], {input_meta.name: legacy_nchw[None, ...]})[0][0]
            # Recreate Phase 8's TensorFlow float32 softmax when identifying its exact top-k mismatches.
            legacy_probabilities = tf.nn.softmax(legacy_logits).numpy().astype(np.float64)
            legacy_order = np.argsort(legacy_probabilities)[::-1]
            relative_image = Path("images") / path.parent.name / path.name
            target_image = fixture / relative_image
            target_image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target_image)
            tensor_entry = f"{index:03d}.f32"
            tensor_bytes = x.tobytes(order="C")
            tensors.writestr(tensor_entry, tensor_bytes)
            records.append({
                "imageId": f"{index:03d}",
                "image": relative_image.as_posix(),
                "source": path.relative_to(ROOT).as_posix(),
                "trueClass": path.parent.name,
                "imageSha256": sha256(target_image.read_bytes()),
                "tensorEntry": tensor_entry,
                "tensorSha256": sha256(tensor_bytes),
                "decodedShape": list(decoded.shape),
                "decodedSha256": sha256(decoded.tobytes(order="C")),
                "rawLogits": [float(v) for v in logits],
                "probabilities": [float(v) for v in probabilities],
                "top5": [{"index": int(i), "category": classes[int(i)]["displayName"], "probability": float(probabilities[i])} for i in order[:5]],
                "phase8Reference": {
                    "preprocessedTensorSha256": sha256(legacy_nchw.tobytes(order="C")),
                    "rawLogits": [float(v) for v in legacy_logits],
                    "probabilities": [float(v) for v in legacy_probabilities],
                    "top5": [{"index": int(i), "category": classes[int(i)]["displayName"], "probability": float(legacy_probabilities[i])} for i in legacy_order[:5]],
                },
            })
        probe_dir = fixture / "probes"
        probe_dir.mkdir()
        yy, xx = np.mgrid[0:240, 0:320]
        rgb = np.stack(((xx * 3 + yy) % 256, (yy * 5 + 31) % 256, (xx + yy * 7) % 256), axis=-1).astype(np.uint8)
        rgba = np.concatenate((rgb, ((xx + yy) % 2 * 255).astype(np.uint8)[..., None]), axis=-1)
        rgba_path = probe_dir / "rgba_alpha.png"
        Image.fromarray(rgba, "RGBA").save(rgba_path)
        exif_path = probe_dir / "jpeg_exif_orientation_6.jpg"
        exif = Image.Exif()
        exif[274] = 6
        Image.fromarray(rgb, "RGB").save(exif_path, quality=91, subsampling=2, exif=exif)
        for index, (probe_id, path) in enumerate((("rgba_alpha_png", rgba_path), ("exif_orientation_6_jpeg", exif_path))):
            encoded = tf.io.read_file(str(path))
            decoded = (tf.io.decode_png(encoded, channels=3) if path.suffix.lower() == ".png"
                       else tf.io.decode_jpeg(encoded, channels=3, dct_method="INTEGER_ACCURATE"))
            tensor = tf.transpose(tf.image.resize(decoded, (224, 224), method="bilinear") / 127.5 - 1.0, [2, 0, 1]).numpy().astype("<f4", copy=False)
            decoded_bytes = decoded.numpy().tobytes(order="C")
            tensor_bytes = tensor.tobytes(order="C")
            decoded_entry, tensor_entry = f"probe-{index}.rgb8", f"probe-{index}.f32"
            tensors.writestr(decoded_entry, decoded_bytes)
            tensors.writestr(tensor_entry, tensor_bytes)
            preprocessing_probes.append({
                "id": probe_id,
                "image": path.relative_to(fixture).as_posix(),
                "imageSha256": sha256(path.read_bytes()),
                "decodedShape": list(decoded.shape),
                "decodedEntry": decoded_entry,
                "decodedSha256": sha256(decoded_bytes),
                "tensorEntry": tensor_entry,
                "tensorSha256": sha256(tensor_bytes),
            })
    payload = {
        "schema": "recolens-java-onnx-parity-fixture-v1",
        "modelSha256": sha256(args.onnx.read_bytes()),
        "onnxRuntimePython": ort.__version__,
        "tensorflow": tf.__version__,
        "input": {"layout": "NCHW", "shape": [1, 3, 224, 224], "type": "float32", "color": "RGB", "decode": "JPEG INTEGER_ACCURATE; PNG 3-channel decode; no EXIF orientation transform; alpha dropped", "resize": "TensorFlow bilinear stretch, half-pixel centers, float32 output", "normalization": "pixel / 127.5 - 1.0"},
        "output": {"type": "raw logits", "probabilities": "stable float64 softmax of float32 logits", "classes": [c["displayName"] for c in classes]},
        "records": records,
        "preprocessingProbes": preprocessing_probes,
    }
    (fixture / "fixture.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    env = os.environ.copy()
    env["JAVA_HOME"] = str(args.java_home.resolve())
    env["PATH"] = f"{args.java_home.resolve() / 'bin'}:{env.get('PATH', '')}"
    completed = subprocess.run(
        [args.mvn, "-f", str(ROOT / "backend/pom.xml"), "-Dtest=OnnxClassifierParityTest",
         f"-Drecolens.parity.fixture={fixture}", "test", "-q"],
        cwd=ROOT / "backend", env=env, text=True, check=False,
    )
    if completed.returncode:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
