# Phase 20 — Section-specific sentient retrieval scoring

This patch pushes section-resolved sentient identity into the **asset scoring layer**.

## What it adds

- `backend/backend/drummerbrain/section_asset_scoring_sentient.py`
- `backend/backend/tests/test_phase20_section_asset_scoring_sentient.py`
- updated `backend/llm_service/app.py`

## Goal

By Phase 19, section overrides already affected:
- roadmap feel
- humanize amount
- transition aggressiveness
- orchestration bias
- phrase rendering

But retrieval itself was still effectively downstream-agnostic. Phase 20 adds a stable scoring-hints object so each section can bias groove/fill ranking toward the **right vocabulary** before concrete retrieval happens.

## New runtime output

### `/v1/song_roadmap`
Each section now emits:
- `retrievalHints.preferredGrooveFamilies`
- `retrievalHints.preferredFillFamilies`
- `retrievalHints.grooveFamilyWeights`
- `retrievalHints.fillFamilyWeights`
- `retrievalHints.retrievalPolicy`

### `/v1/performance_spec`
Each phrase now carries the same `retrievalHints` payload, so the selected section identity can be used by any downstream groove/fill loader or reranker.

## Scoring inputs

The scorer uses:
- section type
- local time feel
- local timekeeper
- energy
- fill aggression
- ghost target
- syncopation target
- drummer profile signals:
  - instrument shares
  - fills per minute
  - humanness
  - pocket tightness
  - ghost note frequency
  - technique breakdown

## Example effects

- chorus + ride-leading drummer -> biases `ride_lead`, `open_hat_lift`
- shuffle bridge -> biases `shuffle_pocket`, `triplet_turnaround`
- tight verse player -> biases `pocket_backbeat`, `none`

## Why this matters

This is the missing bridge between:
- section identity
- profile-aware roadmap
- concrete phrase/pattern retrieval

After this phase, a retrieval layer can rank assets with section-specific sentient hints instead of relying only on generic family labels or post-selection rendering.
