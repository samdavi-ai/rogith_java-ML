# Render deployment

## Repository

- GitHub: https://github.com/samdavi-ai/rogith_java-ML
- Blueprint: `render.yaml`
- The repository root is the build context. Do not set the backend root directory to `backend`; the Docker build also needs `ml/models/ewaste.onnx` and `ml/class_mapping.json`.

## Live URLs

- Frontend: https://recolens-h55g.onrender.com (Render appended `-h55g` because `recolens.onrender.com` is globally unavailable).
- Backend: https://rogith-ewaste-api.onrender.com
- Health: https://rogith-ewaste-api.onrender.com/health

## Services in the Blueprint

1. `recolens`: Render Static Site; build command `node deployment/build-frontend.js`; publish directory `frontend-dist`.
2. `rogith-ewaste-api`: Docker Web Service; Dockerfile `backend/Dockerfile`; Docker context `.`; health check `/health`.
3. `rogith-ewaste-db`: Render PostgreSQL.

The frontend build copies only the required HTML/CSS/JS files and writes `api-config.js` from `EWASTE_API_BASE_URL`. It uses Node's built-in modules only: there is no `package.json`, `npm install`, or frontend framework. The API image contains the validated ONNX model and canonical `class_mapping.json`; it does not depend on a mounted model volume. The API image also packages `database/schema.sql`, and Spring runs its idempotent `CREATE ... IF NOT EXISTS` statements at startup against the Render database.

## Environment variables

The Blueprint wires `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD` from the PostgreSQL resource. It sets:

- API: `PORT=10000`, `CORS_ALLOWED_ORIGINS=https://recolens-h55g.onrender.com,https://rogith-ewaste-web.onrender.com` (keep both origins allowed while the old Render hostname remains available), `EWASTE_MODEL_PATH=/app/ml/models/ewaste.onnx`, `EWASTE_CLASS_MAPPING_PATH=/app/ml/class_mapping.json`, `EWASTE_MIN_CONFIDENCE=0.66`.
- Static site: `EWASTE_API_BASE_URL=https://rogith-ewaste-api.onrender.com`.
- PostgreSQL: `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD` reference the Render database's private connection values. `ipAllowList: []` blocks external DB connections; the API uses Render's private network.

If Render assigns a suffixed service hostname because a name is unavailable, update both the frontend API origin and API CORS origin in the Dashboard (and in `render.yaml` if continuing to use Blueprint sync).

## Dashboard deployment steps

1. Confirm `main` is pushed to `https://github.com/samdavi-ai/rogith_java-ML` and sign in to the Render Dashboard with the account that owns or can connect this repository.
2. Choose **New → Blueprint**, connect `samdavi-ai/rogith_java-ML`, select `main`, and review the proposed static site, Docker web service, and PostgreSQL resources before applying. This Blueprint requests Free plans; it does not configure a custom domain or embed credentials.
3. Allow Render to create the database and attach its private URL to the API. The API runs `database/schema.sql` on startup; the schema creates tables and indexes without dropping data. Confirm the database and API are in the same Render region.
4. Wait for both API and static-site deployments to finish. Render issues HTTPS URLs for the static site and public API.
5. In the API's Environment page, verify the effective `CORS_ALLOWED_ORIGINS` is the exact HTTPS origin of the deployed static site. If Render assigned different service slugs, also set the static site's `EWASTE_API_BASE_URL` to the actual API URL and rebuild the static site. Keep the CORS origin specific; do not use `*`.
6. Open the API URL's `/health`. Confirm HTTP 200, `status: UP`, and `modelStatus: MODEL_READY` (the model path is not returned).
7. Upload a supported JPG/PNG and confirm a real prediction. Test a low-confidence image and confirm `UNSURE` is shown without category-specific advice.
8. On desktop, grant camera permission, confirm preview and sampled classifications, then stop and restart the camera. On Android Chrome and iPhone Safari, repeat the check with the rear camera if physical devices are available.
9. Confirm the guide matches classified categories. History is browser-local and is not stored in PostgreSQL or tied to an account.

Do not report a step as complete until it has been checked at the deployed URL or device.

## PostgreSQL note

The Blueprint selects Render's Free PostgreSQL plan for a no-cost preview. Render says Free Postgres expires after 30 days, has a 1 GB limit, and has no backups; Free web services spin down after 15 minutes idle and may take about a minute to wake. Render explicitly positions Free instances for preview/hobby use, not production. Before real users or durable data, choose paid always-on web and database plans, enable backups, and review database retention. No paid resources have been created or authorized by this code change. [Render Free plan limits](https://render.com/docs/free).

## Troubleshooting

- **CORS error:** check the API's `CORS_ALLOWED_ORIGINS` matches the exact static-site origin, including `https://` and without a trailing slash.
- **Frontend cannot reach API:** check `EWASTE_API_BASE_URL`; the static build fails if it is missing or is not HTTPS.
- **Model unavailable:** check the Docker image includes `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`; verify the two model-path environment variables.
- **Model load error:** inspect server startup logs and verify model/mapping artifact integrity; health returns `MODEL_LOAD_ERROR` without exposing local paths.
- **Database connection error:** check the Blueprint database is running and that the API has its internal `DATABASE_URL`, user and password values. The URI host is converted to JDBC format; credentials are passed separately.
- **Image rejected:** upload a JPEG or PNG at least 32 pixels per side, within the 10 MB limit and 40-megapixel decoded limit.
- **Camera blocked:** use the HTTPS static site and grant browser camera permission. The app prefers a rear camera on mobile where the browser provides that capability.
- **Flashlight unavailable:** the flashlight control appears only when the active camera/browser exposes torch support; laptop webcams and some mobile browsers do not.

## Local verification already run

- A local Spring Boot HTTP smoke test loaded the real model; `GET /health` returned `MODEL_READY` and a measured 1,063 ms load time. For this isolated inference test, database/JPA auto-configuration was excluded because no local PostgreSQL server was available.
- `POST /api/classifications` on a held-out mobile phone returned `CLASSIFIED`, “Mobile phone”, 99.13% confidence (HTTP 200, 25.99 ms). The known held-out battery error returned `UNSURE`, `categoryName: null`, 56.55% confidence (HTTP 200, 78.87 ms on the first request).
- A 30-request sequential HTTP sample with the held-out phone image measured 11.31 ms median, 13.87 ms p95, and 15.46 ms max (local machine).
- The browser samples at a configured 1,000 ms interval, one request at a time (nominally about one analyzed frame per second). Camera capture/encoding was not separately timed. Process memory and a Docker-contained runtime were not measured.
- A live webcam room frame returned Light bulb at 89.4%; no target e-waste object was deliberately presented, so this is not an accuracy measurement.
- The configured model confidence floor is `EWASTE_MIN_CONFIDENCE=0.66`; below it the response is `UNSURE` with `categoryName: null`, and the browser shows photo tips without class-specific guidance.
- Docker Compose and the Render Blueprint parse successfully. A Docker image build and Render smoke test have not been verified in this environment.
