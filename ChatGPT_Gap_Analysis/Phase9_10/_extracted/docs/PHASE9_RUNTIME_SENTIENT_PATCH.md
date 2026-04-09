# Phase 9 runtime sentient patch

This patch upgrades `backend/llm_service/app.py` so `/v1/performance_spec` can consume the richer drummer identity exported by the Phase 7 sentient profile pipeline and exposed by the Phase 8 runtime adapter.

## What it changes

- Adds `backend/backend/drummerbrain/performance_spec_sentient.py`
- Enhances `backend/llm_service/app.py`
- Adds `backend/backend/tests/test_phase9_sentient_performance_spec.py`

## Runtime behavior

When `drummer_profile` contains any of the following keys, the service now prefers sentient-profile-derived instrument rendering over the generic fallback profiles:

- `instrument_timing_profiles`
- `instrument_dynamic_profiles`
- `timing_profiles`
- `dynamic_profiles`
- `transition_model`

The helper supports both of these shapes:

1. Phase 7 raw profile style:
   - `timing_profiles = {"profiles": [...]}`
   - `dynamic_profiles = {"profiles": [...]}`
   - `transition_model = {"transitions": [...]}`

2. Phase 8 adapted runtime style:
   - `instrument_timing_profiles`
   - `instrument_dynamic_profiles`
   - `transition_model`

## What becomes audibly better

- Role-aware snare backbeat timing
- Instrument-specific push / laid-back behavior
- Drummer-specific velocity centroids
- Phrase-shape decisions influenced by the transition model

## Integration order

1. Apply Phase 7 sentient profile export.
2. Apply Phase 8 runtime adapter.
3. Apply this Phase 9 patch.
4. Feed the adapted profile into `/v1/performance_spec`.
