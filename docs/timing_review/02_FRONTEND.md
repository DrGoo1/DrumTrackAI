# Timing Audit — Frontend

## Key files

- `frontend__src__pages__WebDAWAppV3.tsx`
- `frontend__src__components__drums__DrumPianoRoll.tsx`
- `frontend__src__midi__ui__DrumGrid.tsx`
- `frontend__src__utils__pianoRollGrid.ts`
- `frontend__src__audio__Scheduler.ts`
- `frontend__src__audio__AudioEngine.ts`
- `frontend__src__audio__drumPlayerEngine.ts`
- `frontend__src__state__v3__store.ts`
- `frontend__src__state__v3__types.ts`
- `frontend__src__integration__tempoBridge.ts`
- `frontend__src__types__songMap.ts`

## Source of truth

In V3 UI, the audio timeline tends to be the master clock.

Important mechanisms:

- `arrangement.beatTimes` (if present) is used for beat→sec conversions.
- otherwise `arrangement.tempoMap` drives beat→sec.

## Drum playback scheduling (sampler)

General scheduling algorithm:

- Convert `(barIndex, tickInBar)` → `totalTicks` → `beats` (apply `beatShift`)
- Convert `beats` → `tSec` via `beatTimes` or `tempoMap`
- Schedule one-shot audio slightly ahead of time (`AudioContext` lookahead)

See:

- `frontend__src__pages__WebDAWAppV3.tsx` (drum scheduling loop)

### Drift / desync risks

- **Multiple clocks:** waveform timeline clock vs AudioContext clock
- **Offset estimation:** `engineToCtxOffset` and output latency compensation
- **Beat shift errors:** consistent N-beat offsets
- **Rounding errors:** conversion in/out of seconds repeatedly

## Audition playback

Audition uses the same mapping but schedules relative to `startSec`.

See:

- `frontend__src__pages__WebDAWAppV3.tsx` (audition `useEffect`)

Risks:

- mixing note payloads that provide `tSec` directly with those that provide `barIndex/tickInBar`
- incorrect handling of clips whose bars start at 1 (bar-base normalization)

## Grid rendering

Grid rendering is controlled by:

- `resolution_ppq`
- `timeSignature`
- grid resolution (16ths, triplets, etc.)

See:

- `frontend__src__components__drums__DrumPianoRoll.tsx`
- `frontend__src__utils__pianoRollGrid.ts`

Risks:

- drawing grid at a resolution that doesn’t match note quantization
- triplets represented as floats instead of integer ticks
