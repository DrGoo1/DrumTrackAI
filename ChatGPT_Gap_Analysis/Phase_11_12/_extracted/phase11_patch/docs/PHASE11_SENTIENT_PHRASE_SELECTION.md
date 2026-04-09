# Phase 11 — Sentient Phrase Selection Patch

This patch carries sentient-drummer identity into **phrase-family selection**.

## Added
- `backend/backend/drummerbrain/phrase_selection_sentient.py`
- `backend/backend/tests/test_phase11_phrase_selection_sentient.py`

## Modified
- `backend/llm_service/app.py`

## What it changes

### `/v1/song_roadmap`
Each section now emits an optional `phraseSelection` object when the sentient helper is available.
That object includes:
- `grooveFamily`
- `fillFamily`
- `grooveCandidates`
- `fillCandidates`
- `selectorWeights`

This means section planning now chooses drummer-specific phrase families, not just generic fill probabilities.

### `/v1/performance_spec`
Each phrase now carries through section-level `phraseSelection` hints. When no roadmap hint is already present,
the endpoint derives one on the fly from the drummer profile and section context.

The selected groove/fill families also shape runtime rendering by:
- choosing `phraseShape` (`flat`, `swell`, `push`)
- increasing ride accents for `ride_lead`
- increasing hat accents for `open_hat_lift`
- increasing snare flam/drag probability for fill families like `linear_burst`, `flam_tom`, and `triplet_turnaround`

## Result
The runtime is closer to a true phrase selector:
- roadmap sections now declare drummer-specific phrase families
- performance-spec phrases carry the same family decisions into rendering
- later runtime layers can use those family tags to choose concrete groove/fill assets

## Validation
Run:

```bash
PYTHONPATH=/path/to/backend pytest -q backend/tests/test_phase11_phrase_selection_sentient.py
```

## Recommended next step
Phase 12 should connect `phraseSelection.grooveFamily` / `fillFamily` to the actual phrase asset or pattern retrieval layer,
so the system chooses concrete drummer-specific grooves and fills rather than only emitting selection hints.
