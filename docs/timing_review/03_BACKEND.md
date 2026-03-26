# Timing Audit — Backend

## Key files

- `drum_generation_api.py`
- `dcsm_backend.py`
- `backend__dcsmpiano__dcsm_drumtrack_schema.py`
- `backend__dcsmpiano__dcsm_drumtrack_builder.py`
- `backend__drum_generation__pattern_layer.py`
- `backend__drum_generation__jamstix_attributes.py`
- `backend__drum_generation__llm_performance_spec.py`
- `backend__drum_generation__local_humanization_model.py`

## Output data model

Backend ultimately returns a `DrumTrackForDCSM`.

Key timing fields:

- `resolution_ppq` (track-level)
- per-note:
  - `barIndex`
  - `tickInBar`
  - `tickLength`

See:

- `backend__dcsmpiano__dcsm_drumtrack_schema.py`

## Internal events and conversion

Many generators operate on an internal “event list” representation that includes:

- `time_sec` (seconds)
- optionally `barIndex` / `tickInBar`

That representation is then converted to the rich track schema.

Sentient Drummer (DrummerBrain) note:

- Some DrummerBrain clips are stored as tempo-adaptive grid events (beat-domain) and may not provide `time_sec`.
- Runtime selection converts these events into seconds using request tempo + meter.
- See `README_SENTIENT_DRUMMER.md` for operational details and provenance fields.

Risk:

- if events are only second-based and later converted to bars/ticks, rounding and tempo-map changes can cause instability.

## Pinned MIDI / exact phrase playback

Pinned MIDI is driven via config fields:

- `egmd_midi_path` (also used for DTK pinned MIDI)
- `grooveMode` + `grooveSource`

Timing-safe behavior for “exact” playback should be:

- parse MIDI ticks
- normalize to `resolution_ppq`
- assign `barIndex/tickInBar`
- derive seconds from grid (tempo + ppq)
- loop by whole bars / known phrase length

## LLM / humanization layer

LLM-derived performance specs can add micro-timing offsets.

See:

- `backend__drum_generation__llm_performance_spec.py`

Risks:

- applying micro-timing when the user expects exact/pinned playback
- generation failure when a provider/model is unavailable

Recommendation:

- explicit rule: exact/pinned playback must not depend on LLM providers
