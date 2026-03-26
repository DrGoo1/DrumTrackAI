# DrumTracKAI Timing Audit (Backend + Frontend)

This document summarizes how DrumTracKAI represents, converts, displays, and plays time for drum events, and where sync drift can be introduced.

This is intended for a deep review with an LLM and/or human reviewer.

## Snapshot folder

A curated copy of key files is in:

`docs/timing_review/code_snapshot/`

Files are copied with path separators replaced by `__` so they can live in a single folder.

### Included files (code snapshot)

Backend:

- `drum_generation_api.py`
- `dcsm_backend.py`
- `backend__dcsmpiano__dcsm_drumtrack_builder.py`
- `backend__dcsmpiano__dcsm_drumtrack_schema.py`
- `backend__drum_generation__pattern_layer.py`
- `backend__drum_generation__jamstix_attributes.py`
- `backend__drum_generation__llm_performance_spec.py`
- `backend__drum_generation__local_humanization_model.py`

Frontend:

- `frontend__src__pages__WebDAWAppV3.tsx`
- `frontend__src__components__drums__DrumPianoRoll.tsx`
- `frontend__src__midi__ui__DrumGrid.tsx`
- `frontend__src__audio__Scheduler.ts`
- `frontend__src__audio__AudioEngine.ts`
- `frontend__src__audio__drumPlayerEngine.ts`
- `frontend__src__state__v3__store.ts`
- `frontend__src__state__v3__types.ts`
- `frontend__src__integration__tempoBridge.ts`
- `frontend__src__utils__pianoRollGrid.ts`
- `frontend__src__types__songMap.ts`
- `frontend__src__components__v3__V3DrumEditorPane.tsx`
- `frontend__src__components__v3__V3ImportAnalysisHeader.tsx`

## Terminology: timing domains and conversions

DrumTracKAI uses (at least) these timing domains:

### 1) MIDI tick domain (PPQ)

- MIDI files store event deltas in ticks.
- PPQ (ticks-per-quarter-note) varies by file (`mid.ticks_per_beat`).

### 2) DrumTrack grid domain (barIndex/tickInBar)

Frontend editing and most scheduling uses a grid-like representation:

- `barIndex` (0-indexed)
- `tickInBar` (integer tick offset within bar)
- `resolution_ppq` (ticks per beat for the grid used by the track)

See schema:

- `backend__dcsmpiano__dcsm_drumtrack_schema.py` (`DrumNoteEvent`)

Invariants we want:

- `0 <= tickInBar < resolution_ppq * beatsPerBar`
- `barIndex` is consistent with `time_sec` mapping

### 3) Musical beat domain (beats)

Frontend often maps ticks → beats via:

- `beats = (totalTicks / ticksPerBeat) - beatShift`

Then beats → seconds using either:

- `beatTimes` (explicit) or
- `tempoMap` (piecewise)

### 4) Seconds domain (tSec)

Seconds are used for:

- audio timeline cursor
- visible playhead position
- scheduling drum sampler events in `AudioContext`

## Frontend: core timing responsibilities

### A) Source of truth

In V3 UI, the audio timeline tends to be the master clock.

Key file:

- `frontend__src__pages__WebDAWAppV3.tsx`

Notable mechanisms:

- `arrangement.beatTimes` (if present) is used for beat→sec conversions.
- Otherwise `arrangement.tempoMap` drives beat→sec.

### B) Drum playback scheduling

Scheduling is done by taking each note:

- Convert `(barIndex, tickInBar)` → `beats`
- Convert `beats` → `tSec`
- Schedule an engine one-shot slightly ahead of time

Relevant area:

- `frontend__src__pages__WebDAWAppV3.tsx` (look at the drum scheduling `useEffect` and `scheduleWindow`)

Risk factors:

- Using multiple clocks simultaneously (waveform clock vs AudioContext clock)
- Insufficient lookahead
- Incorrect `engineToCtxOffset` estimation
- Incorrect `beatShift` (off-by-N beats)

### C) Audition playback

Audition uses the same mapping but schedules relative to `startSec`:

- `frontend__src__pages__WebDAWAppV3.tsx` (audition `useEffect`)

Risk factors:

- Mixing `tSec`-based notes with `barIndex/tickInBar` notes
- Incorrect assumptions about bar base (some clips start at bar 1)

### D) Grid rendering and “does it look on-grid?”

Grid display depends on:

- `resolution_ppq`
- `timeSignature`
- selected grid resolution (16ths, triplets, etc.)

Relevant files:

- `frontend__src__components__drums__DrumPianoRoll.tsx`
- `frontend__src__utils__pianoRollGrid.ts`
- `frontend__src__midi__ui__DrumGrid.tsx`

Risk factors:

- Rendering grid from one resolution while notes are authored in another
- Triplet representation: fractional beats must map cleanly to integer ticks

## Backend: core timing responsibilities

### A) Generation output shape

Backend ultimately sends a `DrumTrackForDCSM` to the frontend.

Schema + builder:

- `backend__dcsmpiano__dcsm_drumtrack_schema.py`
- `backend__dcsmpiano__dcsm_drumtrack_builder.py`

Key responsibility:

- Ensure every returned note has consistent `barIndex/tickInBar/tickLength` at a known `resolution_ppq`.

### B) Pinned-MIDI / exact phrase playback

Pinned MIDI is handled in:

- `drum_generation_api.py`

Historically, drift can occur if we parse MIDI into `time_sec` using floating conversions then “loop” by approximate phrase lengths.

For exact/pinned playback, the safest model is:

- parse MIDI into ticks
- normalize to a target `resolution_ppq`
- assign `barIndex/tickInBar`
- derive `time_sec` from the grid (tempo + ppq)
- loop using whole-bar lengths (not inferred by max `time_sec`)

### C) LLM / humanization performance spec

LLM-derived performance specs can change micro-timing.

File:

- `backend__drum_generation__llm_performance_spec.py`

Risk factors:

- Applying micro-timing to patterns that should be exact
- Unavailable providers/models causing generation failures

## Where sync can break (failure modes)

### 1) Mixed domains without a single source of truth

Symptoms:

- cursor drifts vs audible hits
- playhead “looks right” but sounds late/early

Common causes:

- mixing waveform timeline time and Tone/AudioContext time without a stable mapping

### 2) Rounding drift at loop boundaries

Symptoms:

- missing/extra feel at the end of a loop
- bar boundary flams

Common causes:

- looping by `max(time_sec)+padding`
- converting tick deltas to seconds and back multiple times

### 3) Off-by-beat shift

Symptoms:

- consistent N-beat cursor offset

Common causes:

- beatShift inference wrong
- wrong bar base (events start at bar 1 but code assumes bar 0)

### 4) Triplet feel not landing on integer ticks

Symptoms:

- notes appear off-grid when zoomed
- the groove sounds “pushed/pulled” unintentionally

Common causes:

- authoring triplet positions as floats (e.g. 0.75) that do not map to a clean subdivision

## Recommended invariants (should be enforced/logged)

### Backend invariants

- All notes have:
  - `barIndex >= 0`
  - `0 <= tickInBar < ticksPerBar`
  - `tickLength >= 1`
- Track has stable:
  - `resolution_ppq` (e.g. 960)

### Frontend invariants

- `ticksPerBeat` used for conversion must match the track’s `resolution_ppq`.
- `ticksPerBar = ticksPerBeat * beatsPerBar`

### Conversion invariants

For any note:

- `tSec ≈ timeAtBeats( (barIndex*ticksPerBar + tickInBar)/ticksPerBeat - beatShift )`

If this is violated, either:

- tempo/beatTimes are not consistent with note timing
- beatShift is wrong
- notes aren’t actually on the grid

## Suggested test plan

### Unit tests

- MIDI parsing tests:
  - given a deterministic MIDI file, produced `barIndex/tickInBar` match expected subdivisions
- Loop boundary tests:
  - a 2-bar phrase tiled to 8 bars must have identical bar boundaries (no drift)

### Integration tests

- Render + playback sync test:
  - schedule a click track and verify hits occur near cursor times

### Debug instrumentation

Add temporary logging (and remove after validation) for:

- computed `beats` and `tSec` for a handful of notes around bar boundaries
- detected beatShift and how it’s applied

## What to review next

If the goal is “accurately create, display, and playback complex drum playing”, focus on these questions:

1. What is the single authoritative timing source during playback?
2. Are there any paths that schedule drums using `time_sec` directly (bypassing tick grid)?
3. Do we ever apply micro-timing on patterns that are intended to be exact?
4. Is triplet timing consistently represented as integer ticks?
5. Are loop lengths computed from musical structure (bars) vs from inferred phrase duration?
