# Phase 13 — Sentient Phrase Event Loading Patch

This patch connects `phraseAssets.selectedGrooveAsset` to an actual phrase-event loader so the runtime can emit a resolved event pattern rather than only selection hints.

## Added
- `backend/backend/drummerbrain/phrase_event_loader_sentient.py`
- `backend/backend/tests/test_phase13_phrase_event_loader_sentient.py`

## Modified
- `backend/llm_service/app.py`

## What it changes

### Concrete phrase-event pattern generation
The new helper builds a `phraseEventPattern` payload for each phrase by:
- preferring inline `patternSteps` on a selected groove asset when present
- otherwise attempting MIDI extraction from `selectedGrooveAsset.midiPath` when `mido` is available
- otherwise falling back to deterministic family patterns keyed off the sentient groove family
- overlaying the selected fill asset's `patternSteps` into the final bar of the phrase

### Runtime behavior
`/v1/performance_spec` now adds `phraseEventPattern` to each phrase when `phraseAssets` and/or `phraseSelection` are present in the section summary.

The payload contains:
- `sourceGrooveAssetId`
- `sourceFillAssetId`
- `resolution`
- `bars`
- `events`
- `eventSummary`

This makes the selected groove/fill asset actionable for downstream adaptation, DCSM note-building, or plugin rendering.

## Notes
- The helper is additive and safe: if the sentient patch is not installed, `/v1/performance_spec` continues to behave as before.
- MIDI parsing is optional and activates only when `mido` is installed and the groove asset exposes a `midiPath`.
- Family fallbacks ensure deterministic behavior even without external catalogs or MIDI parsing.

## Validation
Run:

```bash
PYTHONPATH=/path/to/backend pytest -q backend/tests/test_phase13_phrase_event_loader_sentient.py
```

## Recommended next step
Phase 14 should consume `phraseEventPattern.events` inside the actual note-builder / DCSM builder so the selected phrase asset becomes editable rendered note data, not just a runtime phrase payload.
