# Phase 15 — Sentient Render Route + Plugin Bridge

## Goal

Phase 14 attached a renderable sentient preview under `spec.dcsmRenderPayload`, but the default runtime contract still centered on `spec`.

Phase 15 makes the sentient take directly consumable by the existing frontend piano-roll and plugin-oriented flows by adding a dedicated render endpoint that returns:

- `spec`
- `drum_track`
- `midi_notes`
- `plugin_render` (when a plugin target is requested)

## What this patch adds

- `backend/backend/drummerbrain/render_take_sentient.py`
- `backend/backend/tests/test_phase15_render_take_sentient.py`
- updated `backend/llm_service/app.py`

## New endpoint

`POST /v1/render_sentient_take`

Request body matches the existing `/v1/performance_spec` payload:

```json
{
  "cfg": {...},
  "songmap_summary": {...},
  "drummer_profile": {...}
}
```

## Response shape

```json
{
  "ok": true,
  "spec": {...},
  "drum_track": {...},
  "midi_notes": [...],
  "plugin_render": {
    "plugin": "jamstix",
    "midi_base64": "...",
    "ticks_per_beat": 960
  },
  "metadata": {...}
}
```

## Behavior

1. Calls the existing `/v1/performance_spec` logic to preserve all prior sentient selection/rendering steps.
2. Resolves the sentient take from:
   - `spec.dcsmRenderPayload` when already present
   - or a Phase-14-style rebuild from phrase patterns when the helper exists
3. Mirrors the renderable take to top-level keys so existing frontend helpers can consume it directly.
4. Optionally builds plugin MIDI when `cfg.pluginTarget`, `cfg.plugin`, or `cfg.pluginName` is supplied.

## Why this matters

This is the first phase where the sentient drummer output becomes a **first-class render response** instead of remaining nested preview metadata.

That makes it much easier to connect to:

- frontend piano roll population
- plugin export / guide-track workflows
- legacy MIDI fallback consumers

## Suggested integration

Use `/v1/render_sentient_take` anywhere the UI or plugin path currently expects a concrete `drum_track` response rather than only a performance spec.

## Validation

Included tests cover:

- using an existing `dcsmRenderPayload` without rebuild
- generating a plugin render payload when a plugin target is requested
