# Phase 11 — Sentient Phrase Selection Patch

This patch carries sentient-drummer identity into **phrase-family selection**.

## Added

- `backend/drummerbrain/phrase_selection_sentient.py`
- `backend/tests/test_phase11_phrase_selection_sentient.py`

## Modified

- `llm_service/app.py`

## What it changes

### `/v1/song_roadmap`

Each section now emits an optional `phraseSelection` object when the sentient helper is available.
That object includes:

- `grooveFamily`
- `fillFamily`
- `grooveCandidates`
- `fillCandidates`
- `selectorWeights`

### `/v1/performance_spec`

Each phrase now carries through section-level `phraseSelection` hints. When no roadmap hint is already present,
the endpoint derives one on the fly from the drummer profile and section context.

The selected groove/fill families can also shape runtime rendering by influencing `phraseShape` and other
instrument-level decisions.

## Validation

Run:

```bash
pytest -q backend/tests/test_phase11_phrase_selection_sentient.py
```
