# Timing Audit — Overview

## Snapshot folder

Curated code copies:

- `docs/timing_review/code_snapshot/`

## Timing domains (authoritative definitions)

DrumTracKAI uses (at least) these timing domains:

### 1) MIDI tick domain (PPQ)

- MIDI files store event deltas in ticks.
- PPQ (ticks-per-quarter-note) varies by file (`mid.ticks_per_beat`).

### 2) DrumTrack grid domain (barIndex/tickInBar)

Frontend editing and most scheduling uses a grid representation:

- `barIndex` (0-indexed)
- `tickInBar` (integer tick offset within bar)
- `resolution_ppq` (ticks per beat for the grid used by the track)

Schema reference:

- `backend__dcsmpiano__dcsm_drumtrack_schema.py` (`DrumNoteEvent`)

Core invariants:

- `0 <= tickInBar < resolution_ppq * beatsPerBar`
- `barIndex` is consistent with any derived seconds mapping

### 3) Musical beat domain (beats)

Frontend commonly maps ticks → beats via:

- `beats = (totalTicks / ticksPerBeat) - beatShift`

Then beats → seconds using either:

- `beatTimes` (explicit per-beat timeline) or
- `tempoMap` (piecewise tempo curve)

### 4) Seconds domain (tSec)

Seconds are used for:

- audio timeline cursor
- playhead display
- scheduling drum sampler events in `AudioContext`

## Design goal (single source of truth)

To accurately create/display/play complex drum performance, the system should have:

- a single authoritative clock during playback
- deterministic conversions between grid (ticks) and seconds
- explicit rules for when micro-timing is allowed vs prohibited
