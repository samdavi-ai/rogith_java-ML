# RecoLens Complete Setup Guide

Audience: students and developers setting up the current repository on a workstation. This is a repository-root guide. Commands below are based on checked-in files; run them from the repository root unless stated otherwise.

## 1. What this project is

RecoLens is a static HTML/CSS/JavaScript application, a Spring Boot 3.3.5 API, an ONNX Runtime Java classifier, and PostgreSQL schema initialization. Docker Compose is the supported one-command local stack. There is no npm package, frontend framework, Maven wrapper, or bundled raw dataset.

## 2. Requirements and version policy

| Tool | Purpose | Required / repository evidence | Check | Install and verify |
|---|---|---|---|---|
| macOS, Linux, or Windows with Docker Desktop/Engine | Host development and containers | No OS gate in code. The checked-in ML report was produced on Apple Silicon macOS; Dockerfiles build Linux images. | `uname -a` (macOS/Linux); `sw_vers` (macOS) | Install a supported OS release and Docker Desktop/Engine. Verify with `docker version`. |
| Java | Run and test the Spring backend | Java 17 is set in `backend/pom.xml`; `backend/Dockerfile` builds and runs on Temurin 17. | `java -version`; `mvn -version` | Install a Java 17 JDK (for example, Temurin 17). On macOS, select it with `export JAVA_HOME=$(/usr/libexec/java_home -v 17)`. Verify both commands report Java 17. |
| Maven | Resolve dependencies, tests, and executable JAR | No Maven Wrapper or Maven version property is checked in. The backend image uses Maven 3.9. | `mvn -version` | Install Maven 3.x or later. Verify its Java line reports Java 17. |
| Node.js | Run `deployment/build-frontend.js` when building a Render static site | The script uses Node built-ins only. There is no `package.json`, lockfile, or npm dependency installation. Render's recorded build used Node 24.21.0; the repo does not pin that version. | `node --version`; `npm --version` | Install a current Node.js release. npm is included with Node, but is not used by this frontend. Verify `node deployment/build-frontend.js` only after setting the required HTTPS API URL. |
| Python | Prepare data, train, evaluate, and export the model | ML report used Python 3.11.15. Use Python 3.11 for the pinned TensorFlow stack in `ml/requirements.txt`; Python is not needed to run the deployed Java API. | `python3.11 --version`; `ml/.venv/bin/python --version` | Install Python 3.11 and pip/venv. Create `ml/.venv` as shown in the ML guide and verify the interpreter. |
| Git | Clone and contribute | Repository has a Git remote; no minimum Git version is specified. | `git --version` | Install Git from your OS package manager or git-scm.com. |
| Docker + Compose plugin | Build and run the complete local app | `docker-compose.yml` uses Compose service definitions and Dockerfiles. | `docker version`; `docker compose version` | Install Docker Desktop or Docker Engine with the Compose plugin. Verify both commands. |
| PostgreSQL | Local Compose database | Direct host PostgreSQL is optional: Compose runs `postgres:16-alpine`. The deployed Render database is managed by Render; its exact server version is shown in the Render dashboard. | In Compose: `docker compose exec db pg_isready -U ewaste -d ewaste` (with default local names) | No host install is needed for Compose. If running Java outside Compose, install a PostgreSQL server and create the schema described in `database/schema.sql`. |

### Environment snapshot recorded while writing this guide

The current authoring host reported Maven 3.10.0, Node 26.0.0, npm 11.12.1, Python 3.14.7 and Python 3.11.15, Git 2.54.0, Docker 29.4.0, and Docker Compose 5.1.2. `psql` was not installed. `mvn -version` was using Java 27, which is outside the project's Java 17 target; set Java 17 before running Maven. Version snapshots describe this host, not minimum project requirements. The training report records macOS 26.6.2, Apple Silicon, TensorFlow 2.17.0 and Keras 3.15.1.

## 3. Clone and verify the repository

```bash
git clone https://github.com/samdavi-ai/rogith_java-ML.git
cd rogith_java-ML
git remote -v
git status --short
```

The commands fetch the actual public repository and enter its root. `git remote -v` should show `https://github.com/samdavi-ai/rogith_java-ML.git`; an empty `git status --short` means the checkout has no tracked changes.

## 4. Repository map

```text
rogith_java-ML/
├── index.html, app.js, styles.css, camera-controller.js, api-config.js
├── assets/branding/                 # RecoLens SVG logo/icon/favicon assets
├── backend/
│   ├── pom.xml
│   ├── Dockerfile
│   └── src/main/java/org/secondcircuit/assistant/
│       ├── api/                     # REST controllers, response records, errors
│       ├── config/                  # CORS/security and PostgreSQL URL setup
│       └── service/                 # image checks, ONNX inference
├── database/schema.sql              # idempotent PostgreSQL schema, no seed data
├── deployment/                      # static build and Nginx reverse proxy
├── ml/
│   ├── class_mapping.json           # ordered six-class contract
│   ├── models/ewaste.onnx           # tracked production model
│   ├── scripts/                     # data audit, split, evaluation, ONNX checks
│   ├── training/train.py
│   └── reports/                     # recorded metrics and model/data reports
├── tests/camera-controller.test.cjs # Node built-in camera-controller tests
├── docker-compose.yml
├── render.yaml
└── README.md, RENDER_DEPLOYMENT.md
```

Raw/extracted data, prepared data, the local virtualenv, frontend build output, `.env`, and Keras checkpoints are intentionally excluded by `.gitignore`/`.dockerignore`. The ONNX model, class mapping and JSON/Markdown reports are tracked.

## 5. Configure and start the local application

### Step 1 — Create a local environment file

```bash
cp .env.example .env
```

Edit `.env` and set a non-empty `DATABASE_PASSWORD`. Do not commit `.env`. Compose reads these values; blank `DATABASE_PASSWORD` causes Compose configuration to fail intentionally. The remaining defaults use database `ewaste`, user `ewaste`, and browser port `8088`.

### Step 2 — Build and start PostgreSQL, API, and frontend

```bash
docker compose up --build
```

Compose builds the Java API image from `backend/Dockerfile`, builds the Nginx image from the repository-root `Dockerfile`, and starts a `postgres:16-alpine` database. The API waits for the database health check. PostgreSQL initializes a fresh data volume from `database/schema.sql`. Nginx serves the static page on host port `8088` and proxies `/api/` to the backend container on port `8080`.

### Step 3 — Confirm readiness

In another terminal:

```bash
docker compose ps
curl -i http://localhost:8088/health
```

Expected health JSON includes `"status":"UP"` and `"modelStatus":"MODEL_READY"`. A ready model also includes `modelLoadTimeMs`. Open <http://localhost:8088> and try the upload and guide. If the host port is busy, set `WEB_PORT` in `.env` to another available port and open that port instead.

### Step 4 — Stop the stack

```bash
docker compose down
```

The named `postgres-data` volume remains. To delete the local database contents as well, use `docker compose down -v`; that removes this local volume and its records.

## 6. Local frontend and API configuration

There is no standalone development server command in the repository. The checked-in `api-config.js` sets an empty API origin so local Compose uses same-origin `/api/...` requests through Nginx. The production frontend build is `node deployment/build-frontend.js`; it requires `EWASTE_API_BASE_URL` to be set to an HTTPS API origin and writes the resulting `frontend-dist/api-config.js`. Do not set a production API URL to HTTP.

## 7. Test commands available in the repository

The commands below are documented from the checked-in test files; they were not run as part of this documentation-only task.

```bash
node --test tests/*.test.cjs
```

```bash
cd backend
mvn test
mvn package
```

The Maven commands require Java 17 and resolve the dependencies declared in `backend/pom.xml`. `mvn package` creates `backend/target/ewaste-assistant-0.1.0.jar`. ML commands, test prerequisites, and destructive output behavior are in [RECOLENS_ML_GUIDE.md](RECOLENS_ML_GUIDE.md).

## 8. Current state

- **IMPLEMENTED:** static UI, image upload, live-camera sampling, conditional torch toggle, Spring API, six-class ONNX inference, startup schema initialization, Compose and Render Blueprint.
- **PRODUCTION VERIFIED (prior deployment checks):** RecoLens frontend at <https://recolens-h55g.onrender.com>, API at <https://rogith-ewaste-api.onrender.com>, API health/model readiness, CORS, and a real mobile-phone classification. Render's exact `recolens.onrender.com` hostname was unavailable; Render assigned the `-h55g` suffix.
- **NOT TESTED:** physical Android/iPhone camera and flashlight behavior. A camera browser/device must report torch support for the flashlight control to appear.
- **NOT IMPLEMENTED:** server-persisted classification history, live database-backed recycling guidance, and working sign-in.
- **CONFIGURATION REQUIRED:** local `.env` password and a licensed/extracted dataset for retraining.

See [RECOLENS_COMPLETE_TECHNICAL_REPORT.md](RECOLENS_COMPLETE_TECHNICAL_REPORT.md) for scope and status, and [RECOLENS_DEPLOYMENT_GUIDE.md](RECOLENS_DEPLOYMENT_GUIDE.md) for the Render procedure and production settings.
