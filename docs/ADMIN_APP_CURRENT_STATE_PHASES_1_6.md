# Admin App — Current State (Ingestion + Drummer Persona Pipeline, Phases 1–6)

This document captures the **current implemented state** of the DrumTracKAI Admin application's local-folder ingestion workflow and the drummer persona pipeline as of the Phase 6 implementation.

It is intended for:

- sharing with an LLM (ChatGPT) to discuss **testing methodology**, **accuracy validation**, and **next feature additions**
- protecting engineering progress before major modifications
- providing a single “map” of what exists today: **tables, fields, algorithms, UI entry points, and known limitations**

## 0) Key goals

- Ingest a local `database/processed_stems/<drummer_slug>/<song_folder>/` tree into SQLite.
- Populate drummer “sentience” data across multiple phases:
  - Phase 2: hit events
  - Phase 3: fills + technique events
  - Phase 4: microtiming + dynamics summaries
  - Phase 5: drummer-level rollup (aggregated profile)
  - Phase 6: persona inference + preset generation + exported drummer profile JSON

## 1) Primary code entry points

### Admin services

- `admin/services/central_database_service.py`
  - Primary ingestion & DB API used by the UI.
  - Defines schema creation (`_create_tables`), DB connection config (WAL, timeouts), ingestion, and Phases 2–6.

- `admin/services/phased_drum_analysis.py`
  - Multi-stage analysis pipeline orchestration (download, mvsep, drum_analysis, export, etc.).
  - Not the center of the Phase 2–6 “persona” logic, but informs how analysis outputs appear on disk.

### Admin UI

- `admin/ui/assimilation_dashboard_widget.py`
  - Main operator UI for the pipeline.
  - Buttons exist for:
    - ingest processed stems folder
    - run Phase 2
    - run Phase 3
    - run Phase 4
    - run Phase 5
    - run Phase 6

## 2) Data storage (SQLite) — tables and purpose

SQLite DB file(s) (common locations in this repo):

- `admin/drumtrackai.db` (main Admin DB)
- associated WAL files:
  - `admin/drumtrackai.db-wal`
  - `admin/drumtrackai.db-shm`

### Core entity tables

- `drummers`
  - Canonical Admin schema uses `id` as INTEGER PK and `drummer_id` as TEXT slug.

- `songs` (if present/used)
  - Drummer-linked song catalog.

### Ingestion / provenance tables

- `song_performance_analysis`
  - One row per song analysis (analysis_id).
  - Stores per-analysis metadata and Phase 4 summaries.

- `analysis_artifacts`
  - Tracks presence of analysis artifacts for a given analysis_id/drummer.

- `stem_artifacts`
  - Tracks stems per analysis_id/drummer.

### Performance event tables

- `drum_hit_events` (Phase 2)
  - Per-hit records derived from analysis/stems.

- `fill_events` (Phase 3)
  - Per-fill event records.

- `technique_events` (Phase 3)
  - Per-technique event records (baseline heuristics).

### Drummer-level aggregation

- `drummer_profile_rollups` (Phase 5)
  - One row per drummer (unique on drummer_id).
  - Stores `rollup_json` + `rollup_version`.

### Presets

- `drummer_presets` (Phase 6B)
  - Stores parameter deltas/policies used by downstream generation/humanization layers.

## 3) Phase-by-phase: what is computed and stored

### Phase 1 — Ingest processed stems folder (per-song)

**Input on disk**

- `database/processed_stems/<drummer_slug>/<song_folder>/drum_analysis.json`
- stem audio files inside each `song_folder`

**Primary method**

- `CentralDatabaseService.ingest_processed_stems_song_folder(drummer_id, song_folder)`

**DB writes**

- Upsert into `song_performance_analysis`
- Insert into `analysis_artifacts`
- Insert into `stem_artifacts`

**Notes**

- SQLite is configured for WAL mode and busy timeouts to reduce `database is locked` failures.
- Drummer FK correctness is handled by schema-aware `_ensure_drummer_exists`.

### Phase 2 — Hit-event extraction (per-hit)

**Primary method**

- `CentralDatabaseService.run_phase2_hit_event_extraction_for_drummer(drummer_slug)`

**Stored in**

- `drum_hit_events`

**Key fields**

- `instrument`
- `onset_time_sec`
- enrichment:
  - `onset_strength`
  - `velocity_est`
  - `beat_index`, `bar_index`, `subdivision`
  - `timing_offset_ms`

**Current limitations**

- Grid alignment is approximate (constant tempo fallback when no tempo-map).
- No explicit ground-truth labeling workflow integrated yet.

### Phase 3 — Fill + technique event extraction (heuristics)

**Primary method**

- `CentralDatabaseService.run_phase3_fills_and_techniques_for_drummer(drummer_slug)`

**Stored in**

- `fill_events`
- `technique_events`

**Outputs (per-analysis extractor)**

- fill event count
- technique event count
- derived reporting:
  - `fills_per_min`
  - `technique_breakdown` (counts by technique_name)

**Current limitations**

- Heuristic-only; likely false positives/false negatives.
- Technique taxonomy is minimal (baseline flam/roll style detection).

### Phase 4 — Microtiming + dynamics summaries (per-analysis)

**Primary method**

- `CentralDatabaseService.run_phase4_microtiming_and_dynamics_for_drummer(drummer_slug)`

**Computed from**

- `drum_hit_events`

**Written into**

- `song_performance_analysis`:
  - `groove_micro_timing_variance` (used as “timing std ms”)
  - `groove_pocket_tightness` (0–1)
  - `humanness_score` (0–1)
  - `hit_counts_json`
  - `hit_density_json`
  - `dynamics_json` (velocity stats)
  - `groove_swing_factor` (placeholder / not reliably estimated yet)

**Current limitations**

- No tempo-map-aware microtiming; relies on the Phase 2 grid approximation.
- Swing is not meaningfully computed yet.

### Phase 5 — Drummer profile rollup (per-drummer aggregation)

**Primary method**

- `CentralDatabaseService.run_phase5_profile_rollup_for_drummer(drummer_slug)`

**Reads from**

- `song_performance_analysis`
- `drum_hit_events`
- `fill_events`
- `technique_events`

**Writes to**

- `drummer_profile_rollups.rollup_json`

**Rollup keys (current)**

- `songs`
- `hits`
- `instrument_counts`
- `instrument_shares`
- `fills`
- `fills_per_min`
- `techniques`
- `technique_breakdown`
- `timing_std_ms` (avg of `groove_micro_timing_variance`)
- `pocket_tightness` (avg)
- `humanness` (avg)
- `velocity_mean` (avg extracted from `dynamics_json`)
- `velocity_std` (avg extracted from `dynamics_json`)

**Current limitations**

- Aggregation is largely unweighted averages across songs.
- Does not yet compute deeper stylistic signatures (limb independence, groove vocabulary, meter preferences, etc.).

### Phase 6 — Persona inference + preset generation + exported drummer profile JSON

**Primary method (single entrypoint)**

- `CentralDatabaseService.run_phase6_persona_preset_export_for_drummer(drummer_slug)`

#### 6A) Persona inference

**Implemented in**

- `CentralDatabaseService.infer_persona_from_rollup(rollup)`

**Rollup inputs used**

- `pocket_tightness`
- `humanness`
- `fills_per_min`
- `instrument_shares` (checks `ride` and `hihat` shares)

**Outputs**

- `persona = { label, confidence, tags }`

**Stored**

- persisted back into `drummer_profile_rollups.rollup_json.persona`

#### 6B) Preset generation

**Implemented in**

- `CentralDatabaseService.generate_preset_from_rollup(drummer_slug, rollup, persona)`

**Maps rollup → deltas**

- `pocket_tightness` → `humanizeAmount` (inversely mapped)
- `humanness` → `ghostNoteAmount`
- `fills_per_min` → `fillDensity`
- `swingAmount` currently constant

**Stored**

- upsert into `drummer_presets` via `upsert_drummer_preset(...)`
- `preset_id` persisted into `drummer_profile_rollups.rollup_json.preset_id`

#### 6C) Export drummer profile JSON

**Export path**

- `database/drummer_profiles_generated/<drummer_slug>/drummer_profile.json`

**Export payload**

- `drummer_id` (slug)
- `generated_at`
- `persona`
- `preset` (subset: id/type/tier/deltas/policies)
- `rollup` (full rollup object)

**Stored**

- file path persisted into `drummer_profile_rollups.rollup_json.export_path`

## 4) Assimilation UI: operator workflow

In `admin/ui/assimilation_dashboard_widget.py`:

- Ingest processed stems folder
- Run Phase 2
- Run Phase 3
- Run Phase 4
- Run Phase 5
- Run Phase 6

The dashboard also shows:

- counts of songs/artifacts/stems/hit events/fills/techniques
- avg timing std / pocket / humanness
- computed assimilation percentage

## 5) Known gaps / likely “significant additions” for a more sentient drummer

These are not implemented yet, but are common next steps for improving both **accuracy** and **expressiveness**:

### A) Ground-truth evaluation harness

- Human-labeled validation sets:
  - onset correctness
  - instrument classification correctness
  - fill boundaries
  - technique labels
- Dataset versioning + metrics reports (precision/recall, calibration curves)
- Per-drummer QA dashboards: failures clustered by song/stem quality/tempo

### B) Tempo-map-aware timing model

- Real tempo map inference (per-song)
- Beat tracking aligned to audio, not constant BPM
- Microtiming measured relative to local tempo and groove grid

### C) Richer “style signature” features

- limb independence (kick/snare/hat coordination patterns)
- groove vocabulary clustering (beat archetypes)
- ghost-note detection (snare dynamics modeling)
- cymbal time-feel (ride vs hat leadership beyond raw share)
- fill vocabulary (tom vs snare-centric; linear vs layered)

### D) Persona model upgrades

- From rule tags → probabilistic persona model
- Confidence calibration
- Persona drift checks (song-to-song stability)

### E) Preset model upgrades

- Separate deltas per instrument group (kick/snare/hats/toms/cymbals)
- Velocity curve shaping
- Microtiming distribution shaping (not a single scalar)
- Context-aware presets (genre/tempo dependent)

## 6) Suggested testing questions for ChatGPT

Use these as prompts to design an accuracy test plan:

- "Given the current stored fields (hit events, fill events, technique events, microtiming summaries, rollups), propose an end-to-end evaluation plan with measurable acceptance criteria."
- "How should we validate pocket_tightness and humanness_score against human ratings?"
- "What ground-truth labeling strategy is most efficient for fill boundaries and technique detection?"
- "What additional features are most predictive of drummer identity/style beyond fills/min and instrument shares?"

## 7) Safety / backup guidance

Before large changes:

- close the Admin app (to flush WAL)
- archive `admin/` code and `admin/drumtrackai.db` (+ `-wal` and `-shm`)

