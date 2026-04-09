# Phase 12 — Sentient Pattern Retrieval Patch

This patch connects the Phase 11 `phraseSelection` family hints to a **concrete phrase/pattern retrieval layer**.

## Added
- `backend/backend/drummerbrain/phrase_retrieval_sentient.py`
- `backend/backend/tests/test_phase12_phrase_retrieval_sentient.py`

## Modified
- `backend/llm_service/app.py`

## What it changes

### Concrete groove asset retrieval
The new helper maps section-level sentient phrase families such as:
- `ride_lead`
- `pocket_backbeat`
- `syncopated_kick`
- `open_hat_lift`
- `shuffle_pocket`

into **actual groove assets** by querying the existing groove catalog when a manifest is configured via one of:
- `DTK_GROOVE_MANIFEST_PATHS`
- `DTK_GROOVE_MANIFEST_PATH`
- `GROOVE_CATALOG_MANIFESTS`
- `GROOVE_CATALOG_MANIFEST`

The helper scores groove candidates using:
- style-group match
- groove-family tags
- timekeeper bias (ride vs hats vs mixed)
- bar-length match
- groove complexity vs section energy

### Concrete fill asset retrieval
The patch also maps fill families such as:
- `linear_burst`
- `triplet_turnaround`
- `tom_lift`
- `flam_tom`
- `snare_roll`
- `cymbal_wash`
- `snare_pickup`

into **actual fill-library assets** and resolves a fill pattern payload.

## Runtime behavior

### `/v1/song_roadmap`
Each section now emits:
- `phraseSelection`
- `phraseAssets`

`phraseAssets` contains:
- `selectedGrooveAsset`
- `grooveAssetCandidates`
- `selectedFillAsset`
- `retrievalHints`

### `/v1/performance_spec`
Each generated phrase now carries through the same `phraseAssets` payload, reusing roadmap data when present or deriving it on the fly.

That means the runtime can now advance from:
- “use groove family `ride_lead`”

to:
- “use concrete groove asset `egmd:rock_ride_09` plus concrete fill asset `Nasty-Lick-34`”

## Notes
- If the groove catalog manifest is not available, the helper falls back to a deterministic `family:*` groove asset marker so the downstream runtime still receives a stable selection object.
- Fill selection remains deterministic even without the live fill library module, because the helper includes safe fallback pattern templates.

## Validation
Run:

```bash
PYTHONPATH=/path/to/backend pytest -q backend/tests/test_phase12_phrase_retrieval_sentient.py
```

## Recommended next step
Phase 13 should connect `phraseAssets.selectedGrooveAsset` into the actual event- or MIDI-level phrase loader so the runtime not only chooses an asset id, but actually renders or adapts the chosen phrase content directly into the generated take.
