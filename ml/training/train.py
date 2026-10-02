"""Train MobileNetV2 transfer learning on the curated, leakage-audited splits."""
from __future__ import annotations

import argparse
import json
import os
import platform
import time
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

IMAGE_SIZE = (224, 224)
SEED = 42
BATCH_SIZE = 16


def load_class_map(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    classes = payload["classes"]
    if [entry["id"] for entry in classes] != list(range(len(classes))):
        raise ValueError("class IDs must be contiguous and ordered from zero")
    return classes


def list_files(data_root: Path, split: str, classes: list[dict]) -> tuple[list[str], np.ndarray]:
    paths: list[str] = []
    labels: list[int] = []
    for entry in classes:
        class_dir = data_root / split / entry["name"]
        files = sorted(p for p in class_dir.glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"})
        if not files:
            raise ValueError(f"No images for class {entry['name']} in {split}")
        paths.extend(str(p) for p in files)
        labels.extend([entry["id"]] * len(files))
    return paths, np.asarray(labels, dtype=np.int32)


def make_dataset(data_root: Path, split: str, classes: list[dict], batch_size: int, shuffle: bool) -> tf.data.Dataset:
    dataset = tf.keras.utils.image_dataset_from_directory(
        data_root / split,
        labels="inferred",
        label_mode="int",
        class_names=[entry["name"] for entry in classes],
        color_mode="rgb",
        image_size=IMAGE_SIZE,
        batch_size=batch_size,
        shuffle=shuffle,
        seed=SEED if shuffle else None,
        interpolation="bilinear",
        crop_to_aspect_ratio=False,
    )
    if dataset.class_names != [entry["name"] for entry in classes]:
        raise ValueError(f"Dataset classes do not match class_mapping.json: {dataset.class_names}")

    def preprocess(images: tf.Tensor, labels: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        rgb = tf.cast(images, tf.float32) / 127.5 - 1.0
        nchw = tf.transpose(rgb, [0, 3, 1, 2])
        return nchw, labels

    return dataset.map(preprocess, num_parallel_calls=1).prefetch(1)


def build_model(class_count: int) -> tuple[tf.keras.Model, tf.keras.Model]:
    model_input = tf.keras.Input(shape=(3, *IMAGE_SIZE), dtype=tf.float32, name="image")
    nhwc = tf.keras.layers.Permute((2, 3, 1), name="nchw_to_nhwc")(model_input)
    backbone = tf.keras.applications.MobileNetV2(
        input_shape=(*IMAGE_SIZE, 3), include_top=False, weights="imagenet", pooling=None
    )
    backbone.trainable = False
    # Mild camera-like perturbations are active only during training; inference
    # remains deterministic and retains the established preprocessing contract.
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal", seed=SEED),
        tf.keras.layers.RandomRotation(0.04, fill_mode="reflect", seed=SEED + 1),
        tf.keras.layers.RandomZoom(0.08, fill_mode="reflect", seed=SEED + 2),
        tf.keras.layers.RandomTranslation(0.04, 0.04, fill_mode="reflect", seed=SEED + 3),
        tf.keras.layers.RandomContrast(0.12, seed=SEED + 4),
    ], name="camera_augmentation")
    augmented = augmentation(nhwc)
    features = backbone(augmented, training=False)
    features = tf.keras.layers.GlobalAveragePooling2D(name="global_average_pooling")(features)
    features = tf.keras.layers.Dropout(0.25, name="classifier_dropout")(features)
    logits = tf.keras.layers.Dense(class_count, name="logits")(features)
    return tf.keras.Model(model_input, logits, name="ewaste_mobilenetv2"), backbone


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("ml/data/processed/classification"))
    parser.add_argument("--classes", type=Path, default=Path("ml/class_mapping.json"))
    parser.add_argument("--out", type=Path, default=Path("ml/models"))
    parser.add_argument("--frozen-epochs", type=int, default=12)
    parser.add_argument("--fine-tune-epochs", type=int, default=8)
    args = parser.parse_args()

    tf.keras.utils.set_random_seed(SEED)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass
    classes = load_class_map(args.classes)
    train_paths, train_labels = list_files(args.data, "train", classes)
    train_ds = make_dataset(args.data, "train", classes, BATCH_SIZE, True)
    val_ds = make_dataset(args.data, "validation", classes, BATCH_SIZE, False)
    class_weights_array = compute_class_weight(
        class_weight="balanced", classes=np.arange(len(classes)), y=train_labels
    )
    class_weights = {int(i): float(weight) for i, weight in enumerate(class_weights_array)}

    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint = args.out / "best_model.keras"
    if checkpoint.exists():
        raise FileExistsError(f"Refusing to overwrite an existing checkpoint: {checkpoint}")
    model, backbone = build_model(len(classes))
    callback_list = [
        tf.keras.callbacks.ModelCheckpoint(checkpoint, monitor="val_loss", mode="min", save_best_only=True),
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", mode="min", patience=3, restore_best_weights=True),
    ]
    history: dict[str, list[float]] = {}
    started = time.perf_counter()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    frozen_history = model.fit(
        train_ds, validation_data=val_ds, epochs=args.frozen_epochs,
        class_weight=class_weights, callbacks=callback_list, verbose=2,
    )
    history["frozen"] = {k: [float(v) for v in values] for k, values in frozen_history.history.items()}

    # Fine-tune the last 20 convolutional layers, leaving batch-normalization frozen.
    backbone.trainable = True
    for layer in backbone.layers[:-20]:
        layer.trainable = False
    for layer in backbone.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-5),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    fine_tune_history = model.fit(
        train_ds, validation_data=val_ds, epochs=args.fine_tune_epochs,
        class_weight=class_weights, callbacks=callback_list, verbose=2,
    )
    history["fine_tune"] = {k: [float(v) for v in values] for k, values in fine_tune_history.history.items()}
    selected = tf.keras.models.load_model(checkpoint)
    val_loss, val_accuracy = selected.evaluate(val_ds, verbose=0)
    report = {
        "modelName": "MobileNetV2 E-Waste Classifier",
        "version": "1.0.0",
        "framework": f"TensorFlow {tf.__version__} / Keras {tf.keras.__version__}",
        "architecture": "ImageNet MobileNetV2 feature extractor, GlobalAveragePooling2D, Dropout(0.25), Dense logits head; last 20 backbone layers fine-tuned with BatchNorm frozen",
        "pretrainedWeights": "MobileNetV2 ImageNet weights (Keras official weights)",
        "seed": SEED,
        "input": {"width": 224, "height": 224, "channels": 3, "layout": "NCHW", "dtype": "float32", "normalization": "RGB / 127.5 - 1.0"},
        "classMappingFile": str(args.classes),
        "classes": classes,
        "batchSize": BATCH_SIZE,
        "optimizer": "Adam",
        "frozenLearningRate": 1e-3,
        "fineTuneLearningRate": 1e-5,
        "frozenEpochLimit": args.frozen_epochs,
        "fineTuneEpochLimit": args.fine_tune_epochs,
        "earlyStopping": {"monitor": "validation loss", "patience": 3, "restoreBestWeights": True},
        "classWeights": class_weights,
        "trainImagesIncludingTrainOnlyAugmentations": len(train_paths),
        "trainImagesPerClass": {entry["name"]: int(np.sum(train_labels == entry["id"])) for entry in classes},
        "validationMetricsAtSelectedCheckpoint": {"loss": float(val_loss), "accuracy": float(val_accuracy)},
        "history": history,
        "bestCheckpoint": str(checkpoint),
        "trainingSeconds": time.perf_counter() - started,
        "platform": platform.platform(),
        "tensorflowDevices": [device.name for device in tf.config.list_physical_devices()],
    }
    (args.out / "training_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (args.out / "model_metadata.json").write_text(json.dumps({
        "modelName": report["modelName"],
        "version": report["version"],
        "inputWidth": 224,
        "inputHeight": 224,
        "channels": 3,
        "inputLayout": "NCHW",
        "inputType": "float32",
        "normalization": "RGB float32, pixel / 127.5 - 1.0",
        "resize": "bilinear stretch to 224x224; EXIF orientation applied before RGB decode",
        "output": "logits [1,N]; softmax applied by Java",
        "classesFile": "ml/class_mapping.json",
        "classes": classes,
        "trainingDataset": "Mendeley Data 10.17632/77383kmdnw.1, CC BY 4.0; six supported classes",
        "trainingSeed": SEED,
        "checkpoint": str(checkpoint),
    }, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "bestCheckpoint": str(checkpoint), "validationLoss": float(val_loss),
        "validationAccuracy": float(val_accuracy), "trainingSeconds": report["trainingSeconds"],
    }, indent=2))


if __name__ == "__main__":
    main()
