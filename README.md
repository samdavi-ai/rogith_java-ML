# RecoLens — AI-Powered E-Waste Identification & Recycling Assistant

## Overview

RecoLens is a practical e-waste utility for identifying selected electronics from a photo or webcam frame and reviewing general handling guidance. Image identification is experimental and should be treated as a suggestion for human review.

## Features

- Desktop webcam and mobile rear-camera preference where available
- JPG/PNG upload and preview
- Six-class MobileNetV2 image classifier served through Java and ONNX Runtime
- Recycling preparation guide and local browser history
- Explicit low-confidence and unavailable-model states

## Architecture

```text
Static HTML/CSS/JavaScript → Spring Boot REST API → ONNX Runtime
                                              └── PostgreSQL configuration
```

The static site can be served by the included Nginx image or deployed as a Render Static Site. A configurable API origin lets the static site call a separately hosted HTTPS backend.

## Webcam Detection

The browser captures and compresses JPEG frames, submits one request at a time to `POST /api/classifications`, and stops requesting after repeated service errors. The browser does not upload a continuous video stream. A camera run on an unspecified room frame returned **Light bulb, 89.4% confidence**; no supported target object was deliberately presented, so this is not a known-item accuracy test; it demonstrates that a room scene may be associated with a supported class.

## Image Upload

The backend validates MIME type, decoded file format, image dimensions and maximum file size before inference. The ONNX model returns one of six supported categories; it does not detect unknown classes.

## Recycling Guide

The guide contains general preparation advice. It does not claim to verify local recyclers or jurisdiction-specific requirements.

## Technology Stack

- Vanilla JavaScript, HTML and CSS
- Java 17, Spring Boot 3.3.5, Maven
- ONNX Runtime Java 1.20.0
- TensorFlow/Keras MobileNetV2 training and tf2onnx export
- PostgreSQL
- Docker, Docker Compose and Render

## Machine Learning

The trained model and complete experiment reports are in `ml/`. Dataset sources and licensing are documented in [`ml/DATASET_SOURCES.md`](ml/DATASET_SOURCES.md), and the test metrics and limitations are in [`ml/reports/TRAINING_REPORT.md`](ml/reports/TRAINING_REPORT.md) and [`ml/MODEL_CARD.md`](ml/MODEL_CARD.md). The latest camera-error audit and the rejected negative-class experiment are recorded in [`docs/ML_AUDIT.md`](docs/ML_AUDIT.md) and [`docs/MODEL_IMPROVEMENT_REPORT.md`](docs/MODEL_IMPROVEMENT_REPORT.md).

The final ONNX artifact is `ml/models/ewaste.onnx`. Its preprocessing contract is RGB, bilinear 224×224 stretch, float32, NCHW, values normalized as `pixel / 127.5 - 1`. Python and Java share the ordered mapping in `ml/class_mapping.json`.

The model scored 98.33% accuracy on 60 held-out images from a small dataset. The bulb test support is three images. It also made confident forced predictions on excluded classes; it is not an open-set detector. Do not use these numbers as a field-performance guarantee.

## Backend

- `POST /api/classifications` accepts a multipart field named `image`.
- `GET /health` returns application status and model readiness (`MODEL_READY`, `MODEL_UNAVAILABLE`, or `MODEL_LOAD_ERROR`) without revealing artifact paths.
- `EWASTE_MODEL_PATH` and `EWASTE_CLASS_MAPPING_PATH` configure model artifacts.
- `PORT`, `DATABASE_URL`, `DATABASE_USER`, `DATABASE_PASSWORD`, and `CORS_ALLOWED_ORIGINS` configure service runtime.

## Database

PostgreSQL remains configured for the application. Fresh databases are initialized from the idempotent `database/schema.sql` at Spring startup; Render injects its private PostgreSQL URL and the app converts the `postgresql://` URI into JDBC form. The current app does not yet write classifications or history to PostgreSQL: history remains in browser local storage.

## Local Development

Requirements: Java 17, Maven, Python 3.11 for ML work, and Docker for the full local stack.

```bash
cp .env.example .env
# Set a local DATABASE_PASSWORD before using Docker Compose.
docker compose up --build
```

Open `http://localhost:8088`. To run backend tests:

```bash
cd backend
mvn clean test
mvn package
```

To run the Python artifact checks:

```bash
ml/.venv/bin/python -m unittest discover -s ml/tests -v
```

## Render Deployment

The checked-in `render.yaml` defines the deployed static site, Docker API service, and PostgreSQL database. See [deployment guide](docs/RECOLENS_DEPLOYMENT_GUIDE.md) for URLs, Blueprint details, and verification steps.

## Current ML Status

A real MobileNetV2 model has been trained, evaluated, exported to ONNX, integrated into the API, and exercised through the live camera flow. The model is available in the local repository and is included in the Docker build. Recognition remains experimental: the held-out sample is small, source data lacks physical-item IDs, and an unspecified webcam scene produced a confident bulb prediction.

The API exposes model readiness at `/health` as `MODEL_READY`, `MODEL_UNAVAILABLE`, or `MODEL_LOAD_ERROR`. `EWASTE_MIN_CONFIDENCE` defaults to 0.66 based on validation data; lower-confidence results are returned as `UNSURE` and do not receive category-specific recycling advice. Run `ml/.venv/bin/python ml/scripts/validate_dataset.py --data-root ml/data/raw/roboflow_v5` for the read-only source audit and `ml/.venv/bin/python ml/scripts/validate_onnx.py` to compare the existing Keras and ONNX artifacts on validation images. A seven-class `not_ewaste` experiment was rejected because it reduced e-waste recall and mislabeled a charger; production remains on v1.

## Documentation

- [Complete technical report](docs/RECOLENS_COMPLETE_TECHNICAL_REPORT.md)
- [Setup guide](docs/RECOLENS_COMPLETE_SETUP_GUIDE.md)
- [User guide](docs/RECOLENS_USER_GUIDE.md)
- [Developer guide](docs/RECOLENS_DEVELOPER_GUIDE.md)
- [Deployment guide](docs/RECOLENS_DEPLOYMENT_GUIDE.md)
- [API reference](docs/RECOLENS_API_REFERENCE.md)
- [ML guide](docs/RECOLENS_ML_GUIDE.md)
- [Troubleshooting](docs/RECOLENS_TROUBLESHOOTING.md)
