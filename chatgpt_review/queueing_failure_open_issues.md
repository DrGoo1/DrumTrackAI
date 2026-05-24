# Open Queueing Failures — ChatGPT Handoff

## Current user-reported symptom
- Calibration page queueing still fails (user reports failure persists after recent CORS + Postgres-only patches).

## Scope
This document lists **likely unresolved failure points** and exact code locations to inspect/fix.

---

## 1) Browser-side network failure path (frontend)
If UI shows a generic network message, failure happened before app received an HTTP payload.

### Code references
- API base resolution:
  - `frontend/src/utils/apiBase.ts:2`
  - `frontend/src/utils/apiBase.ts:5`
  - `frontend/src/utils/apiBase.ts:10`
  - `frontend/src/utils/apiBase.ts:15`
- Axios client creation:
  - `frontend/src/pages/CalibrationLab.tsx:564`
  - `frontend/src/pages/CalibrationLab.tsx:565`
- Queue request call:
  - `frontend/src/pages/CalibrationLab.tsx:1194`
- Network error mapping:
  - `frontend/src/pages/CalibrationLab.tsx:724`
  - `frontend/src/pages/CalibrationLab.tsx:745`

### What ChatGPT should verify
1. The deployed frontend bundle actually contains current `apiBase.ts` logic.
2. Runtime `API_BASE` resolves to `https://drumtrackai-calibration-api.onrender.com` on production domain.
3. Browser devtools shows whether failing call is `OPTIONS` (CORS) vs `POST` timeout vs DNS/TLS.

---

## 2) CORS policy on backend (recently expanded, still must verify deployment)
### Code references
- CORS allowlist:
  - `backend/calibration_api.py:1710`
- CORS regex:
  - `backend/calibration_api.py:1721`
- Middleware setup:
  - `backend/calibration_api.py:1718`

### Expected allowed origins now
- `https://drumtrackai.netlify.app`
- `https://www.drumtrackai.netlify.app`
- `https://drumtrackai.net`
- `https://www.drumtrackai.net`
- localhost entries

### What ChatGPT should verify
1. Render service is running commit that contains these CORS lines.
2. Preflight response includes `Access-Control-Allow-Origin` matching actual frontend origin.
3. No upstream proxy/service-level CORS override stripping headers.

---

## 3) Backend hard gates that can block queueing even with good network
If request reaches backend, queue can still fail by design.

### Route and request model
- `POST /calibration/generate-candidates`:
  - `backend/calibration_api.py:2384`
- Request strict defaults:
  - `backend/calibration_api.py:368`
  - `backend/calibration_api.py:378`

### Strict gating in route
- Assimilation readiness gate:
  - `backend/calibration_api.py:2407`
- Strict baseline source gate:
  - `backend/calibration_api.py:2451`
- Strict baseline artifact creation gate:
  - `backend/calibration_api.py:2473`
- Artifact wait timeout path (504):
  - `backend/calibration_api.py:2620`

### What ChatGPT should verify
1. Whether failing requests return structured `detail.stage` (not a browser network error).
2. If failures are frequent from strict baseline creation, inspect baseline source URI accessibility + download path.
3. If frequent 504s, tune `artifact_wait_timeout_sec`/polling and verify render jobs actually start.

---

## 4) Postgres-only runtime enforcement may cause hard startup/runtime failures if env missing
Recent cleanup removed calibration SQLite fallbacks.

### Code references
- Calibration API DB service guard:
  - `backend/calibration_api.py:296`
- Service init requires Postgres config:
  - `admin/services/central_database_service.py:4765`

### What ChatGPT should verify
1. Render has `DB_BACKEND=postgres` and valid `DATABASE_URL`.
2. Health endpoint confirms engine active and calibration tables present.
3. If backend starts degraded, queue endpoint can fail early.

---

## 5) Frontend retry logic may hide stage details when no status is returned
### Code references
- Queue retry loop:
  - `frontend/src/pages/CalibrationLab.tsx:1187`
- Error-to-message mapping:
  - `frontend/src/pages/CalibrationLab.tsx:1301`
- Item ID recovery from error payload:
  - `frontend/src/pages/CalibrationLab.tsx:753`

### What ChatGPT can improve
1. Surface `error.code`, origin, and request URL in UI when status is missing.
2. Log preflight/transport diagnostics in dev mode for faster triage.
3. Add temporary endpoint probe before queueing (`/calibration/health`) to detect CORS/env issues earlier.

---

## Recommended immediate debugging sequence
1. In production browser devtools, inspect failing request + preflight entries.
2. Confirm backend deployment commit includes CORS + Postgres-only changes.
3. Hit `/calibration/health` and `/calibration/db-diagnostics` directly on deployed backend.
4. If request reaches backend, capture `detail.stage` from response payload and patch specific stage.

---

## Existing prior handoff
- `chatgpt_review/queueing_failure_review.md` (previous summary)

This file (`queueing_failure_open_issues.md`) is intended as the **current unresolved issue list** for ChatGPT to action.
