# Phase 10 — Sentient Song Roadmap Patch

This patch extends the existing `song_roadmap` endpoint so section transitions, fill policy,
and orchestration become drummer-specific instead of globally generic.

## Added

- `backend/drummerbrain/song_roadmap_sentient.py`
- `backend/tests/test_phase10_song_roadmap_sentient.py`

## Modified

- `llm_service/app.py`

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

## Validation

Run with:

```bash
pytest -q backend/tests/test_phase10_song_roadmap_sentient.py
```
