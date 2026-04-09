# Phase 8 Runtime Integration for Sentient Drummer

This patch does not replace the current runtime. It adds a small adapter that converts the Phase 7
**sentient profile JSON** into the lighter-weight `drummer_profile` shape already consumed by the
runtime generation endpoints.

## What already exists in the repo

The runtime `performance_spec` endpoint already accepts a `drummer_profile` object and uses keys like:

- `timing_tightness` / `timing_precision`
- `ghost_note_frequency`
- `preferred_feel` / `feel`
- `signature_techniques`

## New file

- `backend/drummerbrain/profile_adapter.py`

## Usage

### Option A: orchestration layer (recommended)

Build a sentient profile JSON from the Admin DB (Phase 7), then adapt it:

```python
from backend.drummerbrain.profile_adapter import load_runtime_drummer_profile

runtime_profile = load_runtime_drummer_profile(profile_path)
```

Then include `runtime_profile` in the existing payload you send to the runtime endpoint.

### Option B: accept sentient profiles directly in `llm_service/app.py`

In the endpoint that currently does:

```python
drummer_profile = req.drummer_profile or {}
```

Add a bridge:

```python
if "timing_profiles" in drummer_profile or "phrase_library" in drummer_profile:
    try:
        from backend.drummerbrain.profile_adapter import to_runtime_drummer_profile
        drummer_profile = to_runtime_drummer_profile(drummer_profile)
    except Exception:
        pass
```

This allows the endpoint to accept either:

- the old lightweight runtime profile, or
- the Phase 7 sentient profile object.

## Recommended next step

Use `build_instrument_phrase_profiles(...)` to derive per-instrument `microTiming` and `velocityProfile`
settings that are audible in playback/generation.
