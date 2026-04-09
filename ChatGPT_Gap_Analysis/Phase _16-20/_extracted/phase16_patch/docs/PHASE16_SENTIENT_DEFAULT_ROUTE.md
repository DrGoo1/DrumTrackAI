# Phase 16 — Sentient default route wiring

Phase 16 makes the sentient path the **default runtime path** for callers that already hit the generic generation endpoint.

## What this patch changes

- Adds `backend/backend/drummerbrain/sentient_request_routing.py`
- Adds `POST /api/generate-drums` and `POST /v1/generate-drums` compatibility routes to `backend/llm_service/app.py`
- Detects rich sentient drummer profiles automatically
- Normalizes existing top-level generation payloads into the existing `PerformanceSpecRequest` shape
- Prefers `/v1/render_sentient_take` when a sentient profile is present
- Falls back to `/v1/performance_spec` behavior for non-sentient requests
- Attaches top-level `drum_track`, `midi_notes`, and `plugin_render` when available so existing frontend consumers can continue working without change

## Detection heuristics

A request is treated as sentient when the supplied drummer profile contains one or more of:

- `profiles`
- `timing_profiles`
- `dynamic_profiles`
- `transition_model`
- `instrument_timing_profiles`
- `instrument_dynamic_profiles`
- `phrase_library` / `phrase_memory`

## Why this phase matters

The frontend already routes generation requests to `/api/generate-drums`.

That means the lowest-risk way to make the sentient drummer the default is **not** to rebuild frontend request flow first. It is to make the generic backend route smart enough to:

1. recognize a sentient request
2. normalize it
3. route it through `render_sentient_take`
4. return the same top-level `drum_track` shape the UI already knows how to consume

## Expected result

After this patch, the app can keep calling `/api/generate-drums`, but requests carrying a sentient drummer profile will automatically receive the Phase 15 render-take response.
