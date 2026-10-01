# Render deployment

## Repository

- GitHub: https://github.com/samdavi-ai/rogith_java-ML
- Blueprint: `render.yaml`
- The repository root is the build context. Do not set the backend root directory to `backend`; the Docker build also needs `ml/models/ewaste.onnx` and `ml/class_mapping.json`.

## Services in the Blueprint

1. `rogith-ewaste-web`: Render Static Site; build command `node deployment/build-frontend.js`; publish directory `frontend-dist`.
2. `rogith-ewaste-api`: Docker Web Service; Dockerfile `backend/Dockerfile`; Docker context `.`; health check `/health`.
3. `rogith-ewaste-db`: Render PostgreSQL.

The frontend build copies only the required HTML/CSS/JS files and writes `api-config.js` from `EWASTE_API_BASE_URL`. The API image contains the validated ONNX model and canonical `class_mapping.json`; it does not depend on a mounted model volume.

## Environment variables

The Blueprint wires `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD` from the PostgreSQL resource. It sets:

- API: `PORT=8080`, `CORS_ALLOWED_ORIGINS=https://rogith-ewaste-web.onrender.com`, `EWASTE_MODEL_PATH=/app/ml/models/ewaste.onnx`, `EWASTE_CLASS_MAPPING_PATH=/app/ml/class_mapping.json`.
- Static site: `EWASTE_API_BASE_URL=https://rogith-ewaste-api.onrender.com`.

If Render assigns a suffixed service hostname because a name is unavailable, update both the frontend API origin and API CORS origin in the Dashboard (and in `render.yaml` if continuing to use Blueprint sync).

## Deployment sequence

1. Push `main` to the configured GitHub repository.
2. In Render, choose **New → Blueprint**, connect `samdavi-ai/rogith_java-ML`, select `main`, and review the three resources and their Free plans before applying.
3. Wait for the API health check and static site build to pass. Render builds static sites with HTTPS; the camera requires HTTPS outside localhost.
4. Verify `GET https://rogith-ewaste-api.onrender.com/health` returns `status: UP` and `modelStatus: MODEL_READY`; that endpoint does not expose artifact paths.
5. Open the static site, upload a valid photo, and test the camera. Confirm requests reach the API and return real model output.

## PostgreSQL note

The Blueprint selects Render's Free PostgreSQL plan for a no-cost preview. Render documents that Free Postgres databases expire after 30 days, have a 1 GB limit, and do not include backups. Upgrade or select a suitable paid plan before relying on persistent production data. Free web services can spin down when idle.

## Troubleshooting

- **CORS error:** check the API's `CORS_ALLOWED_ORIGINS` matches the exact static-site origin, including `https://` and without a trailing slash.
- **Frontend cannot reach API:** check `EWASTE_API_BASE_URL`; the static build fails if it is missing or is not HTTPS.
- **Model unavailable:** check the Docker image includes `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`; verify the two model-path environment variables.
- **Model load error:** inspect server startup logs and verify model/mapping artifact integrity; health returns `MODEL_LOAD_ERROR` without exposing local paths.
- **Database connection error:** check the Blueprint database is running and that the API has its internal `DATABASE_URL`, user and password values.
- **Image rejected:** upload a JPEG or PNG at least 32 pixels per side, within the 10 MB limit and 40-megapixel decoded limit.
- **Camera blocked:** use the HTTPS static site and grant browser camera permission. The app prefers a rear camera on mobile where the browser provides that capability.

## Local verification already run

- A local Spring Boot HTTP smoke test loaded the real model; `GET /health` returned `MODEL_READY` and a measured 1,063 ms load time. For this isolated inference test, database/JPA auto-configuration was excluded because no local PostgreSQL server was available.
- `POST /api/classifications` on a held-out mobile phone returned `CLASSIFIED`, “Mobile phone”, 99.13% confidence (HTTP 200, 25.99 ms). The known held-out battery error returned `UNSURE`, `categoryName: null`, 56.55% confidence (HTTP 200, 78.87 ms on the first request).
- A 30-request sequential HTTP sample with the held-out phone image measured 11.31 ms median, 13.87 ms p95, and 15.46 ms max (local machine).
- The browser samples at a configured 1,000 ms interval, one request at a time (nominally about one analyzed frame per second). Camera capture/encoding was not separately timed. Process memory and a Docker-contained runtime were not measured.
- A live webcam room frame returned Light bulb at 89.4%; no target e-waste object was deliberately presented, so this is not an accuracy measurement.
- The configured model confidence floor is `EWASTE_MIN_CONFIDENCE=0.66`; below it the response is `UNSURE` with `categoryName: null`, and the browser shows photo tips without class-specific guidance.
- Docker Compose and the Render Blueprint parse successfully. A Docker image build and Render smoke test have not been verified in this environment.
