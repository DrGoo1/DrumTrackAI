# DrumTracKAI v1.1.17 – Assimilation and Calibration System

## Overview
DrumTracKAI provides an end-to-end pipeline to assimilate a drummer’s style from analyzed performances and to generate calibrated candidates conditioned on that personality. The system includes:

- Database schemas and services for assimilation features, embeddings, and audits
- Feature extraction through Phase 7 (phrase features, microtiming, dynamics, cymbal language, limb coordination, fill behavior)
- Drummer personality embedding creation and confidence scoring
- Generation controls and a performance transformer for timing/velocity/cymbal/ghost/fill personality shaping with feasibility validation
- Evaluation: transform audit, render–reanalyze loop, AB-test export
- API endpoints for assimilation profile access and generation preview
- Calibration candidate generation that incorporates generation controls
- Admin UI helpers to run phases and track assimilation progress

## Key Paths
- Admin DB/Services: `admin/services/central_database_service.py`
- Assimilation API: `backend/app/assimilation/api/`
- Generation Transformers: `backend/app/assimilation/generation/`
- Performance Transformer Orchestration: `backend/app/assimilation/models/performance_transformer.py`
- Contrastive Trainer: `backend/app/assimilation/models/contrastive_trainer.py`
- Evaluation Helpers: `backend/app/assimilation/evaluation/`
- Calibration Generator: `backend/services/calibration_candidate_generator.py`
- Calibration API: `backend/calibration_api.py`
- Context Tools (Windsurf): `tools/drumtrackai_windsurf_context_tools/`

## Database Additions (Assimilation Phase 7)
New tables and indexes are created automatically by `CentralDatabaseService.initialize()`:
- `drummer_phrase_features` (phrase energy, density/accents, repetition/mutation)
- `drummer_microtiming_profiles` (mean/std/skew offsets, early/late probabilities, histogram)
- `drummer_dynamic_profiles` (velocity stats, ghost/accent probabilities, grids)
- `drummer_cymbal_language` (usage ratios, crash behavior, decay spacing)
- `drummer_limb_coordination` (simultaneous matrices, dependencies, feasibility)
- `drummer_fill_behavior` (probabilities/lengths/density/styles per section/phrase pos)
- `drummer_personality_embeddings` (vector, weights, confidence, source counts)
- `generated_drummer_transform_audits` (before/after features, deltas, scores)

## Pipeline Summary
- Phase 2: Hit events -> `drum_hit_events`
- Phase 3: Fills/techniques -> `fill_events`, `technique_events`
- Phase 4: Derived timing/dynamics in `song_performance_analysis`
- Phase 5: Drummer profile rollup into `drummer_profile_rollups`
- Phase 7: Assimilation profiles + personality embedding persisted across tables above
- Generation: Controls -> transformers -> feasibility -> audit -> (optional render–reanalyze loop)

## Generation Controls (active in pipeline)
- `personality_amount`: 0..1
- `preserve_original_groove`: 0..1
- `fill_aggression`, `ghost_note_detail`, `cymbal_personality`
- `timing_personality`, `velocity_personality`
- `physical_realism_strictness` (feasibility emphasis)
- `section_awareness` (boundary behaviors)

Applied in these components:
- `calibration_candidate_generator.generate_candidate_run()`
  - Applies rollup humanization, control-based blending, and personality transformers
- `performance_transformer.apply_personality_transform()`
  - Orchestrates timing, velocity, cymbal, ghost note, fill transformers
  - Runs feasibility validator and produces metadata

## Evaluation Components
- `render_reanalyze_loop(payload)`
  - Iteratively nudges target similarity while balancing feasibility and groove preservation. Returns iteration history, status, and final scores.
- `make_transform_audit(before_features, after_features)`
  - Computes structural and numeric deltas (added/removed/changed keys, numeric deltas, max delta key/value, aggregate metrics)
- `export_ab_test_rows(items)`
  - Normalizes AB judgment entries into a flat list of rows suitable for training/analysis

## APIs
- Profiles
  - GET `/assimilation/profiles/{drummer_id}?refresh=false`
  - POST `/assimilation/profiles/{drummer_id}/refresh`
- Generation Preview
  - POST `/assimilation/generation/preview`
    - Inputs: `target_drummer_id`, generation controls
    - Returns: scores, audit bundle, optional render–reanalyze loop
- Calibration
  - POST `/calibration/generate-candidates`
    - Inputs: base groove id, target drummer slug, generation controls, counts
    - Writes run versions, event streams, kicks off render service

## Admin/UI Notes
- Assimilation Dashboard (Phase 2–6 buttons) triggers Phase 5, which also runs Phase 7 internally via `run_phase5_profile_rollup_for_drummer()`
- YouTube collector optional auto-assimilate calls phases in order

## Fixing Context-Window Errors in Windsurf
Use the context builder to generate a compact context packet.

Examples:

```powershell
python tools/context_builder.py --files backend/app/assimilation/generation/timing_transformer.py `
  backend/app/assimilation/generation/velocity_transformer.py `
  --focus "Calibrate transformers for target drummer X" `
  --max-lines 1800 --max-file-lines 500 --max-tokens 20000 `
  --out docs/ai_context/context_packet.md
```

- New flag `--max-tokens` adaptively shrinks line budgets to fit target token limits, preventing model context overflow.
- Then paste only the generated `context_packet.md` into a fresh Windsurf chat with a single, bounded task.

## Local Development
- Start backend (FastAPI/Uvicorn) via existing project scripts (PowerShell launch provided in `scripts/start_backend_with_logging.ps1`).
- Frontend Calibration Lab is in `frontend/` (React). Use the existing README in that folder for dev server.

## Validation Checklist
- Import/DB init: check tables present in SQLite
- Run Phase 5 for a drummer; verify profiles and embeddings are created
- Call `/assimilation/profiles/{slug}?refresh=true`; confirm counts and latest embedding
- Call `/assimilation/generation/preview`; verify `render_reanalyze` and `transform_audit` objects present
- Call `/calibration/generate-candidates` with generation controls; verify controls/specs included in run metadata and event stream is transformed

## Updating the Assimilation Data Spreadsheet
File: `docs/assimilation_data_points.csv`
- The last section lists the performance spec mappings. Append Phase 7 profile, embedding, and generation audit rows (see below command block) to keep tracking fields in sync with DB.

## Safe Commands
Append Phase 7 rows to the CSV (PowerShell; review and approve before running):

```powershell
$rows = @'
phrase_index,drummer_phrase_features.phrase_index,phase 7 profiles,indirect (positioning)
phrase_length_bars,drummer_phrase_features.phrase_length_bars,phase 7 profiles,indirect (normalization)
bar_position_in_phrase,drummer_phrase_features.bar_position_in_phrase,phase 7 profiles,indirect (placement)
energy_start,drummer_phrase_features.energy_start,phase 7 profiles,yes (dynamics trend)
energy_end,drummer_phrase_features.energy_end,phase 7 profiles,yes (dynamics trend)
energy_slope,drummer_phrase_features.energy_slope,phase 7 profiles,yes (builds/drops)
pattern_repetition_score,drummer_phrase_features.pattern_repetition_score,phase 7 profiles,indirect
pattern_mutation_rate,drummer_phrase_features.pattern_mutation_rate,phase 7 profiles,indirect
density_curve_json,drummer_phrase_features.density_curve_json,phase 7 profiles,yes (fill/ghost shaping)
accent_curve_json,drummer_phrase_features.accent_curve_json,phase 7 profiles,yes (accent placement)
micro_instrument,drummer_microtiming_profiles.instrument,phase 7 profiles,yes (timing personality)
micro_subdivision,drummer_microtiming_profiles.subdivision,phase 7 profiles,yes (grid context)
mean_offset_ms,drummer_microtiming_profiles.mean_offset_ms,phase 7 profiles,yes
std_offset_ms,drummer_microtiming_profiles.std_offset_ms,phase 7 profiles,yes
skew_offset_ms,drummer_microtiming_profiles.skew_offset_ms,phase 7 profiles,indirect
early_hit_probability,drummer_microtiming_profiles.early_hit_probability,phase 7 profiles,yes
late_hit_probability,drummer_microtiming_profiles.late_hit_probability,phase 7 profiles,yes
pocket_bias,drummer_microtiming_profiles.pocket_bias,phase 7 profiles,yes
context_label,drummer_microtiming_profiles.context_label,phase 7 profiles,indirect
timing_histogram_json,drummer_microtiming_profiles.histogram_json,phase 7 profiles,indirect (sampling)
dyn_instrument,drummer_dynamic_profiles.instrument,phase 7 profiles,yes (velocity personality)
velocity_mean,drummer_dynamic_profiles.velocity_mean,phase 7 profiles,yes
velocity_std,drummer_dynamic_profiles.velocity_std,phase 7 profiles,yes
velocity_skew,drummer_dynamic_profiles.velocity_skew,phase 7 profiles,indirect
ghost_note_probability,drummer_dynamic_profiles.ghost_note_probability,phase 7 profiles,yes
accent_probability,drummer_dynamic_profiles.accent_probability,phase 7 profiles,yes
ghost_to_accent_ratio,drummer_dynamic_profiles.ghost_to_accent_ratio,phase 7 profiles,indirect
accent_grid_json,drummer_dynamic_profiles.accent_grid_json,phase 7 profiles,yes (accenting)
velocity_histogram_json,drummer_dynamic_profiles.velocity_histogram_json,phase 7 profiles,indirect (sampling)
phrase_dynamic_curve_json,drummer_dynamic_profiles.phrase_dynamic_curve_json,phase 7 profiles,yes (macro dynamics)
hihat_closed_ratio,drummer_cymbal_language.hihat_closed_ratio,phase 7 profiles,yes
hihat_open_ratio,drummer_cymbal_language.hihat_open_ratio,phase 7 profiles,yes
hihat_pedal_ratio,drummer_cymbal_language.hihat_pedal_ratio,phase 7 profiles,yes
hihat_bark_probability,drummer_cymbal_language.hihat_bark_probability,phase 7 profiles,yes
ride_usage_ratio,drummer_cymbal_language.ride_usage_ratio,phase 7 profiles,yes
ride_bell_probability,drummer_cymbal_language.ride_bell_probability,phase 7 profiles,yes
crash_frequency_per_min,drummer_cymbal_language.crash_frequency_per_min,phase 7 profiles,yes
crash_on_downbeat_probability,drummer_cymbal_language.crash_on_downbeat_probability,phase 7 profiles,yes
crash_on_transition_probability,drummer_cymbal_language.crash_on_transition_probability,phase 7 profiles,yes
cymbal_decay_spacing_score,drummer_cymbal_language.cymbal_decay_spacing_score,phase 7 profiles,indirect (feasibility)
cymbal_density_curve_json,drummer_cymbal_language.cymbal_density_curve_json,phase 7 profiles,indirect
simultaneous_hit_matrix_json,drummer_limb_coordination.simultaneous_hit_matrix_json,phase 7 profiles,indirect (feasibility)
kick_snare_dependency,drummer_limb_coordination.kick_snare_dependency,phase 7 profiles,indirect
kick_hat_dependency,drummer_limb_coordination.kick_hat_dependency,phase 7 profiles,indirect
snare_hat_dependency,drummer_limb_coordination.snare_hat_dependency,phase 7 profiles,indirect
independence_score,drummer_limb_coordination.independence_score,phase 7 profiles,indirect (constraints)
syncopation_score,drummer_limb_coordination.syncopation_score,phase 7 profiles,indirect (feel)
limb_feasibility_violation_rate,drummer_limb_coordination.limb_feasibility_violation_rate,phase 7 profiles,yes (validation)
common_limb_patterns_json,drummer_limb_coordination.common_limb_patterns_json,phase 7 profiles,indirect
section_label,drummer_fill_behavior.section_label,phase 7 profiles,yes (placement)
phrase_position,drummer_fill_behavior.phrase_position,phase 7 profiles,yes (placement)
fill_probability,drummer_fill_behavior.fill_probability,phase 7 profiles,yes
fill_length_mean_beats,drummer_fill_behavior.fill_length_mean_beats,phase 7 profiles,yes
fill_length_std_beats,drummer_fill_behavior.fill_length_std_beats,phase 7 profiles,indirect
fill_density_mean,drummer_fill_behavior.fill_density_mean,phase 7 profiles,yes (fill intensity)
tom_usage_probability,drummer_fill_behavior.tom_usage_probability,phase 7 profiles,indirect
snare_fill_probability,drummer_fill_behavior.snare_fill_probability,phase 7 profiles,indirect
kick_fill_probability,drummer_fill_behavior.kick_fill_probability,phase 7 profiles,indirect
cymbal_exit_probability,drummer_fill_behavior.cymbal_exit_probability,phase 7 profiles,yes (transition)
triplet_fill_probability,drummer_fill_behavior.triplet_fill_probability,phase 7 profiles,yes (style)
linear_fill_probability,drummer_fill_behavior.linear_fill_probability,phase 7 profiles,yes (style)
rudimental_fill_probability,drummer_fill_behavior.rudimental_fill_probability,phase 7 profiles,yes (style)
common_fill_shapes_json,drummer_fill_behavior.common_fill_shapes_json,phase 7 profiles,indirect
embedding_model_version,drummer_personality_embeddings.model_version,embedding,indirect
embedding_dim,drummer_personality_embeddings.embedding_dim,embedding,indirect
embedding_vector_json,drummer_personality_embeddings.embedding_vector_json,embedding,indirect
embedding_source_song_count,drummer_personality_embeddings.source_song_count,embedding,indirect
embedding_source_hit_count,drummer_personality_embeddings.source_hit_count,embedding,indirect
embedding_confidence_score,drummer_personality_embeddings.confidence_score,embedding,yes (overall bias)
embedding_timing_weight,drummer_personality_embeddings.timing_weight,embedding,yes
embedding_dynamics_weight,drummer_personality_embeddings.dynamics_weight,embedding,yes
embedding_fill_weight,drummer_personality_embeddings.fill_weight,embedding,yes
embedding_cymbal_weight,drummer_personality_embeddings.cymbal_weight,embedding,yes
embedding_coordination_weight,drummer_personality_embeddings.coordination_weight,embedding,yes
embedding_phrase_weight,drummer_personality_embeddings.phrase_weight,embedding,yes
audit_source_similarity,generated_drummer_transform_audits.source_similarity_score,generation audit,indirect (QA)
audit_target_similarity,generated_drummer_transform_audits.target_similarity_score,generation audit,indirect (QA)
audit_human_feasibility,generated_drummer_transform_audits.human_feasibility_score,generation audit,indirect (QA)
audit_groove_preservation,generated_drummer_transform_audits.groove_preservation_score,generation audit,indirect (QA)
audit_before_features_json,generated_drummer_transform_audits.before_features_json,generation audit,indirect
audit_after_features_json,generated_drummer_transform_audits.after_features_json,generation audit,indirect
audit_transform_delta_json,generated_drummer_transform_audits.transform_delta_json,generation audit,indirect
'@
Add-Content -LiteralPath 'docs/assimilation_data_points.csv' -Value $rows
```

Save changes (Git):

```powershell
git add -A
git commit -m "Assimilation: complete eval modules and personality transformers; integrate controls; add render-reanalyze + transform audit; context_builder --max-tokens; README added; docs updated"
# Optionally set upstream first time:
# git push -u origin main
```

## Stopping Background Processes
- Background ingestion/assimilation scripts are not currently running (no matching Python/Node processes were found). The backend (Uvicorn) may be listening on port 8000. If you want me to stop it, let me know and I’ll terminate that server.

## Status
- Assimilation modules completed and wired into generation/calibration
- Evaluation utilities implemented and used in APIs
- Context builder enhanced to prevent model context overflow
- Ready for validation and documentation finalized here
