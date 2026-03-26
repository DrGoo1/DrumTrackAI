# Timing Audit — Risks, Invariants, Tests

## Common failure modes

### 1) Mixed domains without a single source of truth

Symptoms:

- cursor drifts vs audible hits
- playhead “looks right” but sounds late/early

Causes:

- waveform timeline time and Tone/AudioContext time fight each other

### 2) Rounding drift at loop boundaries

Symptoms:

- end-of-phrase timing hiccups
- bar boundary flams

Causes:

- looping by `max(time_sec)+padding`
- repeated tick↔sec conversions

### 3) Off-by-beat shift

Symptoms:

- consistent N-beat cursor offset

Causes:

- incorrect `beatShift` inference
- incorrect bar-base normalization (bar 1 vs bar 0)

### 4) Triplets not landing on integer ticks

Symptoms:

- notes look off-grid when zoomed
- groove feels irregular even when intended to be steady

Causes:

- using float beat positions (e.g. 0.75) that don’t map to a true subdivision

## Recommended invariants

### Backend invariants

- all notes:
  - `barIndex >= 0`
  - `0 <= tickInBar < ticksPerBar`
  - `tickLength >= 1`
- track:
  - stable `resolution_ppq` (e.g. 960)

### Frontend invariants

- conversions always use track’s `resolution_ppq` for `ticksPerBeat`
- `ticksPerBar = ticksPerBeat * beatsPerBar`

### Conversion invariant

For any note:

- `tSec ≈ timeAtBeats( (barIndex*ticksPerBar + tickInBar)/ticksPerBeat - beatShift )`

## Suggested tests

### Unit tests

- MIDI parsing:
  - deterministic MIDI → expected `barIndex/tickInBar` positions
- loop boundary:
  - 2-bar phrase tiled to N bars has no drift at bar boundaries

### Integration tests

- render + playback sync:
  - schedule click track and validate hits occur near cursor

### Debug instrumentation

- log computed `beats` and `tSec` for events around bar boundaries
- log inferred `beatShift` and its application
