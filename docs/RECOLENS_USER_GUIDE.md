# RecoLens User Guide

RecoLens gives a visual estimate for six supported e-waste categories and general preparation suggestions. It is an experimental aid, not a certified diagnostic service or local disposal authority. Confirm handling rules with your local waste authority or an authorized recycler.

## Open RecoLens

Visit the live site: <https://recolens-h55g.onrender.com>. Use HTTPS. Render assigned this suffixed hostname because the exact `recolens.onrender.com` hostname was unavailable. The page works in a modern desktop or mobile browser; the current production UI is English.

## Identify an item from a photo

1. Scroll to **Identify an item**.
2. Choose **Upload a photo** or **Choose image**.
3. Select a clear JPG or PNG. Keep the file under 10 MB; the server also checks that the actual image is readable and within its pixel limits.
4. Review the preview, then press **Identify item**.
5. Wait for the result. RecoLens shows the estimated supported category, confidence, and possible matches when the model returns a sufficiently confident class.
6. Read the preparation and safety notes. Guidance is general and may not match rules where you live.
7. Choose **Identify another item** to clear the result and start again.

Your chosen file is previewed in the browser and sent to the classification API to process. The current page does not store the uploaded image on its server or database. The browser keeps a short local history entry with the result metadata; it is stored in this browser only.

## Use a camera

1. Open **Identify** and select **Use camera**.
2. Select **Start camera**.
3. Allow camera access when the browser asks. On mobile, RecoLens requests the rear-facing camera when available; otherwise the browser may choose another camera.
4. Hold one supported electronic item in focus and show as much of it as possible. Keep the lens steady and use good lighting.
5. Wait while RecoLens samples still frames and requests classifications. It does not upload a continuous video stream. It waits for repeated matching predictions before presenting a stable result.
6. On devices that expose torch support to the browser, use **Turn flashlight on/off** to toggle the camera light. This control is hidden when the browser/device does not support torch controls.
7. Use **Switch camera** if more than one camera is available. Select **Stop camera** when finished.

Camera access requires HTTPS for the deployed site (or a browser's trusted local-development origin). The camera and the API both need network access. If identification pauses after service errors, use **Retry classification** or upload a photo instead.

## Understand the result

- **Classified:** one of six supported categories passed the model's configured confidence floor. A score is the model's softmax score, not a guarantee of correctness.
- **Not sure:** confidence did not reach the current floor. Try a closer, sharper, brighter photo with the full object visible. The app does not show category-specific guidance for this result.
- **Identification unavailable:** the API, model, or network could not return an analysis. You can still browse the general guide.

Supported model categories are battery waste, keyboard, light bulb, mobile phone, mouse, and printed circuit board. A supported prediction does not prove that an object is electronic waste; similar-looking non-electronic items may be forced into a supported category.

## Browse the e-waste guide

Open **Guide** and search or expand a topic. The page contains general guidance for phones/tablets, computers/laptops, batteries/power banks, displays, light bulbs, circuit boards, printers/peripherals, and cables/small electronics. The guide is static content in the web page, not a live local-recycler directory. Local acceptance rules vary.

## Review browser-local history

Open **History** on the same browser and device. It contains up to 20 recent result summaries in browser `localStorage`. It does not sync between devices or accounts and is not stored in PostgreSQL. Clearing site data/browser storage removes it.

## Sign-in status

The **Sign in** button is a placeholder. The page currently shows a notice that account authentication requires a configured authentication service. Do not enter credentials; no sign-in workflow is implemented.

## Get more help

For camera, upload, or result issues, see [RECOLENS_TROUBLESHOOTING.md](RECOLENS_TROUBLESHOOTING.md). For a technical description of results, see [RECOLENS_API_REFERENCE.md](RECOLENS_API_REFERENCE.md).
