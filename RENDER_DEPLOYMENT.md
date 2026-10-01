# Render deployment

## Repository

- GitHub: https://github.com/samdavi-ai/rogith_java-ML
- Blueprint: `render.yaml`
- The repository root is the build context. Do not set the backend root directory to `backend`; the Docker build also needs `ml/models/ewaste.onnx` and `ml/classes.json`.

## Services in the Blueprint

1. `rogith-ewaste-web`: Render Static Site; build command `node deployment/build-frontend.js`; publish directory `frontend-dist`.
2. `rogith-ewaste-api`: Docker Web Service; Dockerfile `backend/Dockerfile`; Docker context `.`; health check `/health`.
3. `rogith-ewaste-db`: Render PostgreSQL.

The frontend build copies only the required HTML/CSS/JS files and writes `api-config.js` from `EWASTE_API_BASE_URL`. The API image contains the validated ONNX model and canonical `classes.json`; it does not depend on a mounted model volume.

## Environment variables

The Blueprint wires `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD` from the PostgreSQL resource. It sets:

- API: `PORT=8080`, `CORS_ALLOWED_ORIGINS=https://rogith-ewaste-web.onrender.com`, `EWASTE_MODEL_PATH=/app/ml/models/ewaste.onnx`, `EWASTE_CLASS_MAPPING_PATH=/app/ml/classes.json`.
- Static site: `EWASTE_API_BASE_URL=https://rogith-ewaste-api.onrender.com`.

If Render assigns a suffixed service hostname because a name is unavailable, update both the frontend API origin and API CORS origin in the Dashboard (and in `render.yaml` if continuing to use Blueprint sync).

## Deployment sequence

1. Push `main` to the configured GitHub repository.
2. In Render, choose **New → Blueprint**, connect `samdavi-ai/rogith_java-ML`, select `main`, and review the three resources and their Free plans before applying.
3. Wait for the API health check and static site build to pass. Render builds static sites with HTTPS; the camera requires HTTPS outside localhost.
4. Verify `GET https://rogith-ewaste-api.onrender.com/health` returns `{"status":"UP"}`.
5. Open the static site, upload a valid photo, and test the camera. Confirm requests reach the API and return real model output.

## PostgreSQL note

The Blueprint selects Render's Free PostgreSQL plan for a no-cost preview. Render documents that Free Postgres databases expire after 30 days, have a 1 GB limit, and do not include backups. Upgrade or select a suitable paid plan before relying on persistent production data. Free web services can spin down when idle.

## Troubleshooting

- **CORS error:** check the API's `CORS_ALLOWED_ORIGINS` matches the exact static-site origin, including `https://` and without a trailing slash.
- **Frontend cannot reach API:** check `EWASTE_API_BASE_URL`; the static build fails if it is missing or is not HTTPS.
- **Model unavailable:** check the Docker image includes `/app/ml/models/ewaste.onnx` and `/app/ml/classes.json`; verify the two model-path environment variables.
- **Database connection error:** check the Blueprint database is running and that the API has its internal `DATABASE_URL`, user and password values.
- **Image rejected:** upload a JPEG or PNG at least 32 pixels per side, within the 10 MB limit and 40-megapixel decoded limit.
- **Camera blocked:** use the HTTPS static site and grant browser camera permission. The app prefers a rear camera on mobile where the browser provides that capability.

## Local verification already run

- `GET /health` returned `{"status":"UP"}` from a running Spring Boot process.
- `POST /api/classifications` returned a real ONNX prediction for a held-out image.
- A 30-request sequential latency sample on localhost reported median 10.85 ms and p95 16.39 ms (warm-up excluded; local CPU only, includes HTTP serialization).
- A live webcam room frame returned Light bulb at 89.4%; no target e-waste object was deliberately presented, so this is not an accuracy measurement.
