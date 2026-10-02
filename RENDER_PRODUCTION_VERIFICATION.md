# RecoLens Render production verification — Phase 11A

Audit date: 2026-10-03 (Asia/Calcutta). Source commit pushed: `f325c6bf8e8efa93b357ece898d29d81aa1568a0`.

## Deployment and URLs

| Item | Status | Evidence |
|---|---|---|
| Target frontend | `https://recolens-h55g.onrender.com` | Homepage responds HTTP 200. |
| Additional live frontend origin | `https://rogith-ewaste-web.onrender.com` | Also responds HTTP 200 with the same branding and API configuration; retained as an active allowed CORS origin. |
| API | `https://rogith-ewaste-api.onrender.com` | Independent Spring Boot Docker service in `render.yaml`. |
| Deployment of Phase 11A frontend commit | **FAIL / NOT DEPLOYED** | After commit `f325c6b` was pushed, both frontend hosts continued serving the old build (Last-Modified `2026-10-01T23:23:41Z` for `recolens-h55g`, `2026-10-01T23:18:50Z` for `rogith-ewaste-web`). The served HTML still contains `accountButton`; served `app.js` does not contain `captureAndClassify`. |
| Render dashboard deployment status | **NOT CONFIRMED** | Render dashboard required GitHub sign-in; no authenticated dashboard session was available. No manual deployment was triggered. Git push alone is not treated as a successful deploy. |
| Deployment date | **NOT CONFIRMED** | No successful Phase 11A frontend deploy was observed. |

The Phase 11A source fixes and tests are committed and pushed, but they are not live in the served frontend at the time of this report. Do not tell users the sign-in button or the old automatic camera workflow has been removed from production yet.

## Frontend and user flows

| Check | Status | Evidence |
|---|---|---|
| Homepage and assets | `PASS` | Homepage, `api-config.js`, logo, favicon, CSS, and JavaScript returned HTTP 200 on both static hosts. |
| RecoLens branding | `PASS` | Logo and favicon assets return HTTP 200. |
| Sign-in UI removed from Phase 11A source | `PASS` (source only) | The current repo has no sign-in, login, or account control. Production still serves the previous sign-in button until redeployed. |
| Upload input and preview | `PASS` (automated source checks); `NOT TESTED` on the updated live UI | Current source accepts JPEG/PNG, has no `capture` attribute, and keeps upload separate from camera. The live frontend is stale. |
| Mobile upload picker | `NOT TESTED` on a physical phone | No physical mobile OS picker was available. The updated frontend has not reached the live host. |
| Camera permission and preview | `PASS` (automated controller tests); `NOT TESTED` on a physical production device | Camera access is requested only by the Start camera button. A capture is sent only after Capture and identify. No physical camera was exercised in this audit. |
| Mobile camera and capture | `NOT TESTED` | No iPhone or Android device was available. |
| Desktop/mobile navigation | `PASS` (automated source checks); `NOT TESTED` in the updated live build | History remains a main navigation target; mobile uses an accessible menu button. The current production HTML remains old. |
| History | `PASS` (automated source/storage tests); `NOT TESTED` in the updated live build | History remains browser-local. The new source formats Today/Yesterday, shows “Unable to identify” and “No classification” for failed/unsure results, and adds a Clear history action. No server-side history is claimed. |
| Result UI | `PASS` (automated source tests) | Known labels and confidence remain user-facing; absent/unsure categories do not invent a label. |
| Accessibility source checks | `PASS` | Named controls, keyboard focus styles, menu state/escape handling, preview alt text, and clear camera labels are present in source. Automated checks are not a substitute for assistive-technology review. |
| Responsive layout | `PASS` (source breakpoints); `NOT TESTED` on physical mobile/tablet | Existing responsive layouts were retained; the user-facing fixes stack upload/camera choices and preserve camera control wrapping. |

## API, model, CORS, and database

| Check | Status | Evidence |
|---|---|---|
| API availability | `PASS` after wake; intermittent delay observed | A request timed out during restart/wake; a subsequent request succeeded. Render's current free service can sleep when idle. |
| Health | `PASS` | `GET /health` returned HTTP 200: `{"status":"UP","modelStatus":"MODEL_READY","modelLoadTimeMs":2010}`. No paths, credentials, or environment variables are returned. |
| Model status | `PASS` | Production API reports `MODEL_READY`. The hosted ONNX hash is not exposed by this endpoint. |
| V1 model unchanged in repository | `PASS` | `ml/models/ewaste.onnx` SHA-256 is `91abc9882697638edff03bf226c08119b53e13c135b3e1a85af5c394741a90c5`, matching the archived V1 artifact. No model, metadata, or class-map file was changed. |
| Production model generation | `PASS` | Production remains on the V1 configuration; V2 is unchanged and not deployed. The remote artifact hash itself is not independently verifiable. |
| CORS for `recolens-h55g` | `PASS` | OPTIONS preflight returned HTTP 200 and `Access-Control-Allow-Origin: https://recolens-h55g.onrender.com`. |
| CORS for `rogith-ewaste-web` | `PASS` | OPTIONS preflight returned HTTP 200 and exactly allowed `https://rogith-ewaste-web.onrender.com`. No wildcard is configured. |
| Live classification API | `PASS` (single-image smoke test only) | Multipart POST returned HTTP 200 in 4,199 ms. Input: existing diagnostic `bottle_challenge.jpg` screenshot crop. V1 returned `CLASSIFIED`, `Mouse`, confidence `0.806026`. This known diagnostic result is not a camera metric or accuracy claim. |
| Database | `NOT TESTED` | Render PostgreSQL is configured through `DATABASE_URL`, `DATABASE_USER`, and `DATABASE_PASSWORD`; startup runs idempotent `schema.sql`. The health endpoint does not report database connectivity, and no destructive or reset operation was run. History is not stored in PostgreSQL. |

## Build and tests

- `node --test tests/camera-controller.test.cjs tests/frontend-ux.test.cjs`: **PASS**, 21 tests.
- `node --check app.js`, `node --check camera-controller.js`, and checks of the built frontend JavaScript: **PASS**.
- `EWASTE_API_BASE_URL=https://rogith-ewaste-api.onrender.com node deployment/build-frontend.js`: **PASS**.
- `mvn -f backend/pom.xml clean package -DskipTests`: **PASS**.
- Full backend Maven tests: **FAIL in the local environment**. The installed JDK is Java 27, but the repository's Mockito/Byte Buddy version supports class files through Java 23; six tests error while mocking application classes. `DatabaseConfigTest` passes. Retrying with Byte Buddy's experimental flag did not resolve it. The Docker daemon is unavailable, so the configured Java 17 container build/test could not be run locally. No backend source was changed in Phase 11A.
- `git diff --check`: **PASS** before the source commit.

## Render configuration and limits

`render.yaml` keeps the existing three-service layout: a static frontend, the Spring API Docker service with `/health`, and Render PostgreSQL. The frontend build injects `EWASTE_API_BASE_URL=https://rogith-ewaste-api.onrender.com`. API configuration points to `/app/ml/models/ewaste.onnx` and `/app/ml/class_mapping.json`; CORS remains restricted to the two active frontend origins. Database secrets remain Render-provided environment variables. No secret or paid plan was added, and no production data was reset.

The Blueprint uses Render's Free plan. A delayed wake response occurred during this audit. The dashboard was not available without GitHub sign-in, so an updated frontend deploy could not be confirmed or manually triggered. The code is ready in commit `f325c6b`; complete the Render dashboard sign-in and deployment, then repeat the frontend, physical mobile, and flashlight checks.

## Current disposition

- Production model: **V1 — unchanged**.
- V2: **not deployed**.
- API health, model readiness, CORS, and API classification smoke: **PASS**.
- Updated frontend deployment: **FAIL / NOT LIVE**.
- Physical mobile upload/camera/flashlight: **NOT TESTED**.
