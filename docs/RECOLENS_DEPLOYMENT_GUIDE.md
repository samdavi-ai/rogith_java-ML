# RecoLens Deployment Guide

## Current Render deployment

The live static app is [https://recolens-h55g.onrender.com/](https://recolens-h55g.onrender.com/). The API is [https://rogith-ewaste-api.onrender.com](https://rogith-ewaste-api.onrender.com) and its health endpoint is [https://rogith-ewaste-api.onrender.com/health](https://rogith-ewaste-api.onrender.com/health). Render assigned the `-h55g` suffix because the unsuffixed `recolens` hostname was unavailable. The older `https://rogith-ewaste-web.onrender.com` origin remains allowed by API CORS.

The repository is [samdavi-ai/rogith_java-ML](https://github.com/samdavi-ai/rogith_java-ML), branch `main`. Blueprint: [`render.yaml`](../render.yaml). Resources:

| Resource | Render type | Blueprint name |
|---|---|---|
| Frontend | Static Site | `recolens` |
| API | Docker Web Service | `rogith-ewaste-api` |
| Database | PostgreSQL | `rogith-ewaste-db` |

Current Blueprint plan is Free for all three. Check the Render dashboard for current resource status and changing plan limits. The configured Free PostgreSQL service is scheduled to expire on 1 November 2026 under the plan policy in effect when this project was configured; arrange a durable database plan and backups before depending on it.

## Blueprint deployment and sync

1. Push the desired commit to `main` in the repository above.
2. In Render, open the existing Blueprint or choose **New → Blueprint** and connect the repository/branch.
3. Review the resources and environment variable references before applying a first-time Blueprint.
4. Confirm the API and database are in the same region and the DB's private connection values are attached to the API.
5. Wait for API and static site deploys to finish. With `autoDeployTrigger: commit`, later pushed commits can trigger deploys; verify the Render service's deploy event rather than assuming a push succeeded.
6. Confirm the environment values below match the actual service URLs. If Render changes a service slug, update both the frontend API origin and API CORS allowlist, then rebuild/redeploy the frontend.

The Docker build context must be the repository root, not `backend`, because the image copies the ONNX model, class map, and SQL schema from other root directories.

## Environment configuration

`render.yaml` currently declares:

- Static site build: `node deployment/build-frontend.js`; publish directory `frontend-dist`; `EWASTE_API_BASE_URL=https://rogith-ewaste-api.onrender.com`.
- API Dockerfile `backend/Dockerfile`, context `.`, health check `/health`, and `PORT=10000`.
- `CORS_ALLOWED_ORIGINS=https://recolens-h55g.onrender.com,https://rogith-ewaste-web.onrender.com`.
- `EWASTE_MODEL_PATH=/app/ml/models/ewaste.onnx`, `EWASTE_CLASS_MAPPING_PATH=/app/ml/class_mapping.json`, and `EWASTE_MIN_CONFIDENCE=0.66`.
- `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD` from `rogith-ewaste-db`; database IP allowlist is empty so the API uses the private network.

Do not use a wildcard CORS origin or put credentials in source control. Render's API database URL is converted to JDBC form by application configuration. The schema is initialized idempotently on API startup. This schema setup does not mean predictions are saved to the database.

## Deployment verification checklist

Use the deployed URL and check each result:

1. Open `/health`; expect HTTP 200, `status: UP`, and `modelStatus: MODEL_READY`.
2. Upload a valid JPEG/PNG; confirm an expected category and sensible confidence are displayed.
3. Try an image that does not produce a confident category; confirm the UI shows Unsure without category-specific advice.
4. Inspect browser developer tools if the page cannot reach the API; resolve mixed content or CORS before camera checks.
5. Allow camera access over HTTPS, confirm preview and sampled classifications, then stop and restart the camera.
6. On a physical mobile device, verify rear-camera selection/switching and torch separately. The torch control is conditional on browser/device support; no physical Android/iPhone torch verification is recorded in this guide.
7. Confirm browser history remains local and does not appear in a PostgreSQL user account.

A previously recorded live smoke test reported `MODEL_READY` and a held-out mobile-phone prediction. Treat that as a historical check, not proof of the current deployment's status; repeat the checklist after each deployment.

### Live HTTP recheck (2026-10-02)

- Frontend `GET https://recolens-h55g.onrender.com/`: HTTP 200 in 0.49 seconds.
- API `GET https://rogith-ewaste-api.onrender.com/health`: the first request timed out after 40 seconds with no response; the retry returned HTTP 200 in 13.38 seconds with `{"modelStatus":"MODEL_READY","status":"UP","modelLoadTimeMs":3299}`.
- API CORS preflight for `POST /api/classifications` from `https://recolens-h55g.onrender.com`: HTTP 200; `Access-Control-Allow-Origin` matched the site and methods included GET, POST, OPTIONS.
- This recheck confirms the frontend root, API health/model readiness, and the CORS preflight only. It does not re-verify upload, current camera cleanup, physical phone behavior, torch, or database writes. The initial timeout may be a cold/sleeping service response; its cause was not established.

## Local Docker deployment

From the repository root:

```bash
cp .env.example .env
# Set DATABASE_PASSWORD in .env
docker compose up --build
```

Visit `http://localhost:8088`. Compose starts PostgreSQL, the API, and Nginx. Nginx serves the frontend and proxies API requests. Stop with `docker compose down`. `docker compose down -v` deletes the persistent local database volume.

## Operational limits

Free web services may spin down while idle. First requests can be delayed while a service wakes. A Free database is unsuitable for durable production data and has limited storage/backup guarantees. The app currently has no authentication, server-side classification history, or database persistence for predictions. Treat this deployment as a demonstration. Choose paid always-on services, backups, retention controls, and security controls before using it for sustained production traffic.

See [RECOLENS_TROUBLESHOOTING.md](RECOLENS_TROUBLESHOOTING.md) for deployment diagnosis and [RENDER_DEPLOYMENT.md](../RENDER_DEPLOYMENT.md) for the original operational notes.
