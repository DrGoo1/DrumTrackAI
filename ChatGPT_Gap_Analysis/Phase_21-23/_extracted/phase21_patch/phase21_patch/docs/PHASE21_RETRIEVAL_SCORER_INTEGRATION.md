# Phase 21 — Retrieval scorer integration

This patch is the first point where the Phase 20 `retrievalHints` object can directly change candidate ranking.

## Adds

- `backend/backend/drummerbrain/catalog_scoring_sentient.py`
- `backend/backend/tests/test_phase21_catalog_scoring_sentient.py`

## Purpose

Phase 20 emitted section-aware retrieval preferences, but those preferences were still advisory metadata. Phase 21 introduces a concrete scorer that can rerank groove and fill candidates using:

- preferred families
- family weights
- timekeeper preference
- feel preference
- complexity fit

## Expected integration

Use this scorer after candidate discovery from the existing catalog and fill library:

- call `rerank_groove_candidates(...)` on groove catalog search results
- call `rerank_fill_candidates(...)` on fill-library candidates
- take the top result or top-N for downstream selection/adaptation

## Output shape

Each reranked candidate returns:

- `candidate`
- `score`
- `scoreBreakdown.family`
- `scoreBreakdown.timekeeper`
- `scoreBreakdown.feel`
- `scoreBreakdown.complexity`
- `scoreBreakdown.matchedFamilies`

## Why this phase matters

This is the point where section-specific sentient identity begins to affect **actual selection order**, not just later rendering behavior.
