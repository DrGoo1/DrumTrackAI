# Phase 14 — Sentient Phrase Event → DCSM Bridge

## Goal

Phase 13 selected concrete groove/fill assets and produced `phraseEventPattern.events` inside `/v1/performance_spec`.

Phase 14 turns those selected events into the actual payload shape expected by the existing DCSM note-builder path already present in the repo snapshot.

## What this patch adds

- `backend/backend/drummerbrain/performance_to_dcsm_sentient.py`
- `backend/backend/tests/test_phase14_performance_to_dcsm_sentient.py`
- updated `backend/llm_service/app.py`

## Runtime behavior

When `/v1/performance_spec` is called and the spec contains `phraseEventPattern` data on its phrases, the service now tries to build:

- a synthetic song map from phrase bar ranges + tempo config
- DCSM-compatible internal drum events
- a full `drum_track` payload using the existing `backend.dcsmpiano.drumtrack_builder_dcsmpiano` builder
- backward-compatible `legacy_midi_notes`

The result is attached as:

```json
spec.dcsmRenderPayload
```

### `dcsmRenderPayload` fields

- `available`
- `resolution_ppq`
- `internalEventCount`
- `drum_track`
- `legacy_midi_notes`

## Why this matters

This is the first phase where selected sentient phrase assets become **editable note data** suitable for the existing DCSM piano-roll pipeline, instead of remaining only as selection metadata.

## Constraints

This patch deliberately uses a **synthetic song map** because `/v1/performance_spec` does not yet receive the full backend SongMap object. That keeps the change additive and low-risk.

## Recommended next step

Phase 15 should wire `spec.dcsmRenderPayload.drum_track` directly into the backend route that feeds the frontend piano roll / plugin render path, so the sentient selection becomes the default rendered take instead of only an attached preview payload.
