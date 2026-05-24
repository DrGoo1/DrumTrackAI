# Calibration Queue Failure Review (for ChatGPT)

## Symptom
- Frontend shows: `Network error contacting <api-base>. (endpoint: /calibration/generate-candidates)`
- This indicates the browser request failed before receiving a usable HTTP response payload (often CORS/preflight, TLS, DNS, or hard network failure).

## Primary likely cause identified
### 1) Backend CORS did not include custom domain traffic
- Before fix, CORS regex effectively allowed `*.netlify.app` but not `drumtrackai.net` custom domain requests.
- If frontend is served from `https://drumtrackai.net` or `https://www.drumtrackai.net`, browser preflight can fail and surface as Axios network error.

### Code references
- `backend/calibration_api.py:1710` (`_allowed_origins`)
- `backend/calibration_api.py:1721` (`allow_origin_regex`)
- CORS middleware registration:
  - `backend/calibration_api.py:1718`

### Fix applied
- Added explicit allowlist entries:
  - `https://drumtrackai.net`
  - `https://www.drumtrackai.net`
- Expanded regex:
  - from netlify-only style to `https://(?:.*\.netlify\.app|(?:.*\.)?drumtrackai\.net)`

## Request path confirmation
### Frontend queue call wiring
- API client base and timeout:
  - `frontend/src/pages/CalibrationLab.tsx:564`
  - `frontend/src/pages/CalibrationLab.tsx:565`
- Queue action posts to endpoint:
  - `frontend/src/pages/CalibrationLab.tsx:1194` (`api.post('generate-candidates', ...)`)
- Network error mapping:
  - `frontend/src/pages/CalibrationLab.tsx:724` (`extractApiErrorMessage`)
  - `frontend/src/pages/CalibrationLab.tsx:745` (`Network error contacting ...`)

### API base resolution
- Production calibration base:
  - `frontend/src/utils/apiBase.ts:2`
- Netlify/custom-domain routing to calibration base:
  - `frontend/src/utils/apiBase.ts:5`
  - `frontend/src/utils/apiBase.ts:10`
  - `frontend/src/utils/apiBase.ts:15`

## Additional backend constraints that can fail queueing (non-network)
If request reaches backend, these are expected hard-gates:
- Route:
  - `backend/calibration_api.py:2384` (`POST /generate-candidates`)
- Strict assimilation readiness gate:
  - `backend/calibration_api.py:2407`
- Strict baseline source + artifact gate:
  - `backend/calibration_api.py:2451`
  - `backend/calibration_api.py:2473`
- Postgres-only service init requirement:
  - `backend/calibration_api.py:296`
  - `admin/services/central_database_service.py:4765`

These backend gate failures should return structured HTTP 4xx/5xx details, not generic network errors.

## Why this still might fail after code fix
1. Backend service not yet redeployed with latest commit.
2. Frontend still running old build artifact.
3. DNS/cache/stale service worker serving old JS bundle.
4. Requests still routed to an outdated API host via env override.

## Targeted verification checklist
1. Confirm deployed backend CORS includes custom domain entries above.
2. In browser devtools, inspect failing `OPTIONS`/`POST` to `/calibration/generate-candidates`:
   - confirm origin
   - confirm CORS headers (`Access-Control-Allow-Origin`)
3. Confirm frontend loaded bundle resolves API base from `apiBase.ts` to intended host.
4. If request reaches backend and fails with status code, inspect returned `detail.stage` for exact failure stage.

## Files changed during this pass
- `backend/calibration_api.py` (CORS expansion + prior Postgres-only calibration cleanup)
- `admin/services/central_database_service.py` (Postgres-only init enforcement)

## Note for ChatGPT reviewer
Prioritize diagnosing browser preflight/CORS behavior first when the user sees Axios “Network error” and no status code.
