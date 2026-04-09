# Phase 19 — Section-Level Sentient Override Execution

## Goal
Honor `sentientProfile` / `drummerProfile` overrides at the **section level** all the way through the roadmap and performance-spec stages, so different song sections can genuinely render from different drummer identities.

## What this patch adds

### New helper
- `backend/backend/drummerbrain/section_sentient_overrides.py`

This module provides:
- sentient-profile detection
- per-section profile resolution
- section profile maps keyed by `index:sectionType`
- derived transition bias
- derived orchestration bias
- derived time feel

### Updated runtime
- `backend/llm_service/app.py`

Changes in `POST /v1/song_roadmap`:
- reads per-section overrides from `cfg.songSections`
- uses the resolved section profile for:
  - `timeFeel`
  - `humanizeAmount`
  - fill aggression / pickup enablement
  - timekeeper choice
  - hat-open bias
  - ride bell probability
  - crash downbeat probability
- emits a `sentientOverride` block per section for visibility

Changes in `POST /v1/performance_spec`:
- reads per-section overrides from `songmap_summary.sections`
- uses the resolved section profile for each phrase
- adjusts phrase rendering metadata for:
  - section-specific feel
  - section-specific humanize amount
  - section-specific transition bias
  - section-specific orchestration bias
- emits `sectionMeta` per phrase

## Why this matters
Before this phase, the frontend could attach different sentient artifacts for different sections, but the backend mostly treated the request as one global drummer identity.

After this phase:
- verse can be one drummer identity
- chorus can switch to another
- bridge can become more ride-led / fill-heavy
- phrase rendering becomes section-specific instead of globally averaged

## Files
- `backend/backend/drummerbrain/section_sentient_overrides.py`
- `backend/backend/tests/test_phase19_section_sentient_overrides.py`
- `backend/llm_service/app.py`

## Integration notes
This patch is intentionally additive and conservative:
- no schema change
- no route rename
- no frontend contract break

It builds directly on the Phase 17–18 frontend behavior where section overrides are already preloaded and attached to generation requests.
