# RecoLens Developer Guide

## Repository map

```text
./                         Static frontend: index.html, styles.css, app.js, camera-controller.js, api-config.js
backend/                   Spring Boot API, ONNX inference and Java tests
ml/                        Dataset, training, evaluation, export and model artifacts
database/schema.sql        Idempotent PostgreSQL schema
deployment/                Static Render frontend build helper
tests/                      Node tests for frontend/deployment behavior
docker-compose.yml          Local database + API + Nginx stack
 render.yaml                Render Blueprint
```


Important implementation files include `app.js`, `camera-controller.js`, `backend/src/main/java`, `backend/src/main/resources/application.yml`, `ml/class_mapping.json`, `ml/models/ewaste.onnx`, and `database/schema.sql`.

## Prerequisites

- Java 17 and Maven for backend development. The Maven compiler and Spring Boot target Java 17.
- Node.js for the built-in test runner and `deployment/build-frontend.js`; there is no `package.json` and no `npm install` step.
- Python 3.11 for the pinned TensorFlow/ONNX ML toolchain.
- Docker Engine and Compose for the integrated local stack.

See [RECOLENS_COMPLETE_SETUP_GUIDE.md](RECOLENS_COMPLETE_SETUP_GUIDE.md) for installation and first-run steps.

## Local development workflow

Start the whole application from the repository root:

```bash
cp .env.example .env
# Set DATABASE_PASSWORD in .env to a non-empty local value.
docker compose up --build
```

Open `http://localhost:8088`. Nginx serves the static files and proxies API traffic. To stop, use `docker compose down`; `docker compose down -v` also deletes the local database volume.

For backend-only work, `cd backend && mvn spring-boot:run` starts the Java process, but database/JPA initialization requires a reachable PostgreSQL instance and matching environment settings. Do not assume the API will start without that dependency. Backend tests run with `cd backend && mvn test`; packaging uses `mvn package`.

Frontend tests use Node's built-in runner:

```bash
node --test tests/*.test.cjs
```

ML checks and training instructions are in [RECOLENS_ML_GUIDE.md](RECOLENS_ML_GUIDE.md). Dataset preparation deletes and recreates its configured output folders, so inspect the configured paths before running it.

## Frontend behavior

The app is plain browser JavaScript. `api-config.js` sets the optional API base URL. An empty base URL makes the browser use same-origin paths, which works behind local Nginx. The Render build helper requires `EWASTE_API_BASE_URL` to be an HTTPS origin and writes the generated config to `frontend-dist`.

`app.js` owns upload, display, local history (`sc-history`), and the static category guide mapping. The sign-in button is a UI placeholder. Guides are static frontend content; the database guide tables are not currently read.

`camera-controller.js` requests a video-only media stream, prefers the environment-facing camera on mobile, and supports device switching where multiple cameras are enumerated. Captured frames are reduced to at most 640 pixels on the longest edge and encoded as JPEG. Only one inference request is allowed at a time. Torch controls are shown only when the selected track reports torch capability and successfully accepts torch constraints. Camera and torch behavior varies by browser and hardware.

## Backend behavior

The Spring Boot service validates the multipart image and runs inference through ONNX Runtime. Keep the Java and Python preprocessing implementations aligned:

1. Decode a valid JPEG or PNG.
2. Convert to RGB.
3. Bilinear resize to 224×224.
4. Normalize channels using `pixel / 127.5 - 1`.
5. Arrange float32 values as `[1,3,224,224]` (NCHW).
6. Interpret output by the ordered IDs in `ml/class_mapping.json`.

The model path and mapping path are configured through `EWASTE_MODEL_PATH` and `EWASTE_CLASS_MAPPING_PATH`. Production Docker paths are `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`. The confidence floor is controlled by `EWASTE_MIN_CONFIDENCE` (default 0.66). Keep response category IDs consistent with the frontend guide mapping and canonical class map.

CORS origins are configured by `CORS_ALLOWED_ORIGINS`, as a comma-separated list of exact origins. The API currently allows GET, POST, and OPTIONS and does not use credentials or authentication.

## Database reality

`database/schema.sql` creates the configured tables idempotently. Spring runs schema initialization at startup and JPA validates the schema. Current feature code does not save uploaded images, predictions, user profiles, or history to PostgreSQL. The browser history is local storage. If adding persistence, design explicit repositories, transaction boundaries, retention/deletion behavior, migrations, access control, and tests before describing the feature as complete.

## Configuration reference

| Variable | Purpose |
|---|---|
| `PORT` | HTTP listen port; Render supplies 10000, local container uses 8080 internally |
| `DATABASE_URL` | PostgreSQL connection URL; Render private URL is converted to JDBC form |
| `DATABASE_USER`, `DATABASE_PASSWORD` | Database credentials |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed browser origins |
| `EWASTE_MODEL_PATH` | ONNX file location |
| `EWASTE_CLASS_MAPPING_PATH` | Ordered model label mapping JSON |
| `EWASTE_MIN_CONFIDENCE` | Minimum confidence before returning a named category |
| `EWASTE_API_BASE_URL` | Frontend build-time HTTPS API origin for static hosting |

Never commit local `.env` secrets. `.env.example` contains the local configuration template.

## Code change checklist

- Preserve API multipart field `image` and existing response envelope unless coordinating a versioned contract change.
- Update API and user documentation if a class ID, endpoint, validation limit, or user-visible behavior changes.
- Keep the class mapping, training labels, exported ONNX output order, and Java interpretation synchronized.
- Avoid committing raw data, training environments, credentials, or `.keras` checkpoints unless explicitly intended.
- For any model replacement, validate preprocessing parity and ONNX outputs before deployment.
- Keep CORS origins exact and HTTPS in production.

## Tests and commands

The repository provides these test commands:

```bash
node --test tests/*.test.cjs
(cd backend && mvn test)
ml/.venv/bin/python -m unittest discover -s ml/tests -v
```

They are listed for developer use; they were not run as part of creating these guides. See [RECOLENS_TROUBLESHOOTING.md](RECOLENS_TROUBLESHOOTING.md) for common failures.
