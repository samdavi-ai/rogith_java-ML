# RecoLens API Reference

This reference describes the endpoints declared by the current Spring source. Base URL examples use the deployed API `https://rogith-ewaste-api.onrender.com`; local Compose serves the same API through `http://localhost:8088`.

## Common response envelope

Successful responses use `ApiModels.Envelope<T>`:

```json
{"success":true,"data":{"classification":{}},"error":null}
```

Errors use:

```json
{"success":false,"data":null,"error":{"code":"INVALID_IMAGE","message":"..."}}
```

The API currently has no authentication requirement. Spring Security permits all requests and disables CSRF for this public API. CORS permits configured exact origins only; the production allowlist is in `render.yaml`.

## `GET /health`

- **Purpose:** reports API process and ONNX model initialization status. It does not return local file paths.
- **Request:** no body or special header.
- **Success:** HTTP 200.
- **Example:**

```bash
curl -i https://rogith-ewaste-api.onrender.com/health
```

Possible response fields:

```json
{"status":"UP","modelStatus":"MODEL_READY","modelLoadTimeMs":2999}
```

`modelStatus` values in source: `MODEL_READY`, `MODEL_UNAVAILABLE`, `MODEL_LOAD_ERROR`. `modelLoadTimeMs` appears only for `MODEL_READY`. A process can return `status: UP` while the model is unavailable; inspect both fields.

## `POST /api/classifications`

- **Purpose:** validates and classifies one uploaded JPEG or PNG.
- **Content type:** `multipart/form-data`.
- **Required part:** `image` (file bytes; client filename is not used for class selection).
- **Limits:** 10 MiB upload; decoded format must match `image/jpeg` or `image/png`; width and height must each be 32–12,000 pixels; decoded pixel count must not exceed 40,000,000.
- **Success status:** HTTP 200, including for `UNSURE` results.
- **Example:**

```bash
curl -i -X POST \
  -F 'image=@/path/to/item.jpg;type=image/jpeg' \
  https://rogith-ewaste-api.onrender.com/api/classifications
```

A production-origin smoke request can include an `Origin` header; browsers also perform CORS preflight automatically:

```bash
curl -i -X OPTIONS \
  -H 'Origin: https://recolens-h55g.onrender.com' \
  -H 'Access-Control-Request-Method: POST' \
  https://rogith-ewaste-api.onrender.com/api/classifications
```

Expected classification response shape:

```json
{
  "success": true,
  "data": {
    "classification": {
      "status": "CLASSIFIED",
      "categoryName": "Mobile phone",
      "confidence": 0.991269696,
      "confidenceLevel": "HIGH",
      "alternatives": [
        {"category":"Keyboard","confidence":0.0047},
        {"category":"Printed circuit board","confidence":0.0015},
        {"category":"Mouse","confidence":0.0013}
      ],
      "guide": null
    }
  },
  "error": null
}
```

The sample values are illustrative of a previously observed production prediction, not a deterministic response for every image. `confidence` and alternative scores are in the 0–1 range. The class list/order is `ml/class_mapping.json`. The API currently sends `guide: null`; the browser chooses general local guidance from `app.js`.

For low confidence (`EWASTE_MIN_CONFIDENCE`, default `0.66`), HTTP is still 200 and the result is `status: "UNSURE"`, `categoryName: null`, and `confidenceLevel: "UNSURE"`. The API may still return the other model alternatives; the UI suppresses those for unsure results.

### Errors and statuses

| HTTP | Error code | Cause in current code | Example remedy |
|---:|---|---|---|
| 400 | `INVALID_IMAGE` | Missing part, empty bytes, wrong MIME/content, corrupt/unsupported image, or dimensions outside limits | Attach a readable JPG/PNG in the stated size/dimension bounds. |
| 413 | `IMAGE_TOO_LARGE` | Spring multipart limit exceeded | Select an image below 10 MB. |
| 503 | `MODEL_UNAVAILABLE` | Configured model or mapping file is absent | Check `EWASTE_MODEL_PATH`, `EWASTE_CLASS_MAPPING_PATH`, and artifact copy in the Docker image. |
| 503 | `MODEL_LOAD_ERROR` | ONNX session, mapping, or tensor-shape validation failed at startup | Check startup logs, model compatibility and class-map/output dimensions. |
| 500 | `INTERNAL_ERROR` | Unhandled error | Inspect backend logs; the response intentionally avoids exposing internal details. |
| 403 on CORS preflight | No JSON contract | Origin is not in `CORS_ALLOWED_ORIGINS` | Add the exact frontend origin and redeploy the API. |

## CORS contract

`CORS_ALLOWED_ORIGINS` is a comma-separated allowlist. `SecurityConfig` trims values and permits `GET`, `POST`, and `OPTIONS`; allowed headers are `Content-Type` and `Authorization`; credentials are disabled. Render currently allows the deployed RecoLens site and the legacy static-site origin while it remains a fallback. Keep the list to exact origins; do not use `*`.

## Endpoints not present

No classification-history, login, user, database-backed guide, image-download, or model-management REST endpoint is declared in the current backend. Tables for users, uploaded images, classifications, predictions, sources, categories, recycling guides, and activity logs exist in SQL, but current API methods do not read or write them.
