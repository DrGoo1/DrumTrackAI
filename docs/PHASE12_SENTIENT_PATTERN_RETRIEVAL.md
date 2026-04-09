# Phase 12 — Sentient Pattern Retrieval Patch

This patch connects the Phase 11 `phraseSelection` family hints to a **concrete phrase/pattern retrieval layer**.

## Added

- `backend/drummerbrain/phrase_retrieval_sentient.py`
- `backend/tests/test_phase12_phrase_retrieval_sentient.py`

## Modified

- `llm_service/app.py`

## What it changes

### Concrete groove asset retrieval

The helper maps phrase families (e.g. `ride_lead`, `pocket_backbeat`, `open_hat_lift`) into **actual groove assets**
by querying the existing groove catalog when a manifest is configured via one of:

- `DTK_GROOVE_MANIFEST_PATHS`
- `DTK_GROOVE_MANIFEST_PATH`
- `GROOVE_CATALOG_MANIFESTS`
- `GROOVE_CATALOG_MANIFEST`

If no catalog is available, it falls back to deterministic `family:*` asset ids.

### Concrete fill asset retrieval

The helper maps fill families into **fill assets** and resolves a safe fallback `patternSteps` payload if the
fill library module isn’t available.

## Runtime behavior

### `/v1/song_roadmap`

Each section can emit:

- `phraseSelection`
- `phraseAssets`

### `/v1/performance_spec`

Each generated phrase can carry through the same `phraseAssets` payload.

## Validation

Run:

```bash
pytest -q backend/tests/test_phase12_phrase_retrieval_sentient.py
```
