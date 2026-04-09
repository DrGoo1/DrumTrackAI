# Assimilation / Sentience Scoring Rubric (Admin UI)

This document describes how the **Assimilation** dashboard score is computed today, and what each phase contributes.

## Current Assimilation Score (0–100)

The current UI score is computed in:

- `admin/ui/assimilation_dashboard_widget.py` (`_compute_assimilation_score`)

It is a simple additive score:

- **Song coverage (0–50 points)**
- **Data richness (0–50 points)**

### 1) Song coverage (0–50)

- Target songs = `20`
- Score = `min(50, (songs_ingested / 20) * 50)`

This rewards ingesting more songs for the drummer.

### 2) Data richness (0–50)

Richness points are currently:

- **+10** if `artifacts > 0`
- **+15** if `stems >= 6`
- **+7** if `0 < stems < 6`
- **+25** if `hit_events > 0`

So the maximum richness score is:

- `10 + 15 + 25 = 50`

## Phase contributions

### Phase 1 — Ingest processed stems folder

Populates (per analysis):

- `song_performance_analysis`
- `analysis_artifacts`
- `stem_artifacts`

Assimilation impact (current rubric):

- increases **songs_ingested** (coverage)
- likely enables **+10 artifacts** and **+7/+15 stems** (richness)

### Phase 2 — Hit-event extraction (onsets)

Populates:

- `drum_hit_events`

Current implementation stores (baseline):

- `instrument` (stem→kit mapping when available)
- `onset_time_sec`

Current implementation stores (enrichment):

- `onset_strength`
- `velocity_est`
- `beat_index`, `bar_index`, `subdivision`, `timing_offset_ms` (grid approximation)

Assimilation impact (current rubric):

- enables **+25** richness (any hit events > 0)

### Phase 3 — Baseline fills + techniques

Populates:

- `fill_events`
- `technique_events`

Assimilation impact (current rubric):

- **no direct points yet**

Phase 3 is still important because it enables more advanced drummer profiling and will be used by future scoring (not yet implemented).

## Notes / Known limitations

- The rubric is intentionally simple and does not currently validate *quality* of data, only presence.
- Phase 3 is not currently counted in the score.
- Tempo-map-aware grid alignment is not currently implemented; the Phase 2 grid fields use a constant tempo (from `song_performance_analysis.tempo_bpm` when present, otherwise a fallback).

## Suggested future scoring extensions

If you want Phase 3+ to affect the dashboard score, recommended additive richness points:

- **+10** if `fill_events > 0`
- **+10** if `technique_events > 0`
- **+10** if `drum_hit_events` has >X% of rows with non-null `timing_offset_ms` + `velocity_est`

This would preserve the “presence-based” progression while encouraging richer extraction.
