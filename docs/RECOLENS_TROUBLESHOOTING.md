# RecoLens Troubleshooting

## Site opens but classification fails

- Check API health at `https://rogith-ewaste-api.onrender.com/health`. Expect HTTP 200 and `modelStatus: MODEL_READY`.
- If the health request is slow after inactivity, a Free Render service may be waking. Retry after it responds.
- In browser developer tools, inspect the failed network request to `/api/classifications`. Confirm the request is going to `https://rogith-ewaste-api.onrender.com` and that the page is loaded over HTTPS.
- For CORS errors, set `CORS_ALLOWED_ORIGINS` to exact page origins including scheme, no trailing slash. Current configured origins are `https://recolens-h55g.onrender.com` and `https://rogith-ewaste-web.onrender.com`.
- After changing the static site's API origin, rebuild/redeploy it; `api-config.js` is generated during build.

## Health reports model unavailable or load error

`MODEL_UNAVAILABLE` means the configured ONNX or mapping artifact could not be found. `MODEL_LOAD_ERROR` indicates a model/session/metadata problem. Check startup logs and ensure the Docker image contains:

```text
/app/ml/models/ewaste.onnx
/app/ml/class_mapping.json
```

Verify `EWASTE_MODEL_PATH` and `EWASTE_CLASS_MAPPING_PATH` match those paths. Compare model output count/order with `ml/class_mapping.json`. Do not expose local file paths in public health responses.

## Image upload rejected

The API accepts JPEG and PNG images using the multipart field `image`. The maximum upload size is 10 MiB; decoded width and height must each be at least 32 and no more than 12,000, with no more than 40 megapixels total. Re-export an image as JPEG or PNG if its extension and actual file format disagree. A corrupt or truncated image can fail even when its filename looks valid.

Expected errors include `INVALID_IMAGE` (400), `IMAGE_TOO_LARGE` (413), model unavailable/load errors (503), and `INTERNAL_ERROR` (500). See [RECOLENS_API_REFERENCE.md](RECOLENS_API_REFERENCE.md) for the error envelope.

## Camera preview is blank or permission is denied

- Use the deployed HTTPS origin or `localhost`; browser camera access is restricted in insecure contexts.
- Grant camera permission in the browser's site settings and reload.
- Close other apps/tabs that may hold the camera, then stop and restart the RecoLens camera.
- On mobile, the app prefers an environment-facing camera when supported. Use the camera switch control if multiple devices are available.
- Camera capture sends resized still frames periodically; a delayed result is not a live video stream failure.

## Flashlight button is missing or does not illuminate

The flashlight toggle is offered only when the selected video track reports `torch` capability and accepts torch constraints. Many laptop webcams lack a light; some mobile browsers/drivers also do not expose torch control. Select the rear camera where possible, use a supported browser/device, and check browser permission. This cannot turn on the phone screen flash when the browser does not provide camera torch support. Physical device verification is not recorded as completed.

## Predictions are wrong or often Unsure

The model has six fixed classes and no unknown-class detector. It may assign an out-of-scope object to one of the supported categories. `UNSURE` is returned when confidence is below the configured `EWASTE_MIN_CONFIDENCE` (default 0.66); it does not guarantee that higher-confidence results are correct. Photograph one clearly visible item with good light and limited background clutter. The dataset test set is small, and the recorded accuracy should not be treated as real-world accuracy.

## Guide, login, history, or database behavior is unexpected

- Preparation guides are static, general advice and are not sourced from local authorities or a live recycler directory.
- The sign-in action is a placeholder; user authentication is not implemented.
- History is stored in browser `localStorage` under `sc-history`, is limited to 20 entries, and is not synced between devices.
- PostgreSQL tables are initialized, but current app code does not store prediction history there.

## Local development problems

- **Docker Compose cannot start:** ensure Docker Engine is running and `.env` exists with a non-empty `DATABASE_PASSWORD`.
- **Port already in use:** free host port 8088 or adjust the frontend port mapping in `docker-compose.yml`.
- **Backend cannot connect to DB:** check Compose service name and credentials; inside Compose, use the configured `db` service rather than `localhost`.
- **Maven uses wrong Java:** use a Java 17 runtime for the backend. The project targets Java 17 even if a host's default Java is newer.
- **ML dependency install fails:** use Python 3.11 and `ml/requirements.txt`; the ML stack is pinned and may not support newer Python runtimes.
- **Frontend tests fail to launch:** Node.js is required; there is no `npm install` step.
- **ONNX file missing locally:** obtain the project model artifact or follow the ML guide to reproduce it. Keep generated data and model output directories distinct; dataset preparation removes its configured output folders before rebuilding.

The repository documents Node, Maven, and Python test commands in the developer guide. They were not run during this documentation update.
