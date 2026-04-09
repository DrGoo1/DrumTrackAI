# Phase 10 — Sentient Song Roadmap Patch

This patch extends the existing `song_roadmap` endpoint so section transitions, fill policy,
and orchestration become drummer-specific instead of globally generic.

## Added
- `backend/backend/drummerbrain/song_roadmap_sentient.py`
- `backend/backend/tests/test_phase10_song_roadmap_sentient.py`

## Modified
- `backend/llm_service/app.py`

## What it does
The patch reads sentient-profile cues already available from the Phase 7–9 bridge:
- `transition_model`
- `fills_per_min`
- `humanness`
- `pocket_tightness`
- `instrument_shares`
- `technique_breakdown`
- optional nested `rollup`

It then applies drummer-specific overrides to `/v1/song_roadmap`:
- fill probability and frequency
- fill length and fill family
- transition pickup behavior
- timekeeper selection (hats / ride / mixed)
- hat-open bias
- ride bell probability
- crash-downbeat probability
- section-level humanize amount
- syncopation bias

## Result
The roadmap now carries drummer identity into section planning, so the runtime is no longer limited
to only per-hit microtiming and velocity identity.

## Validation
Focused tests included:
- fill-heavy ride-leading drummer profile
- conservative tight hat-player profile

Run with:

```bash
PYTHONPATH=/path/to/backend pytest -q backend/tests/test_phase10_song_roadmap_sentient.py
```

## Integration order
1. Apply Phase 7 sentient profile export.
2. Apply Phase 9 sentient performance-spec patch.
3. Apply this Phase 10 roadmap patch.
4. Re-run end-to-end generation using the same drummer profile payload.
5. Compare roadmap + spec output before/after with the same song map.
