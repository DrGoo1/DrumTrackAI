# ChatGPT Gap Analysis — Implementation Notes

This folder contains the ChatGPT gap analysis report and the follow-on implementation work to bridge the Admin assimilation DB (Phases 1–6) into a backend-consumable **Sentient Profile** artifact.

## Source report

- `SENTIENT_DRUMMER_GAP_ANALYSIS (1).md`

Key missing capabilities highlighted by the report:

- canonical phrase layer
- directional timing fingerprint
- context-conditioned dynamics
- phrase transition model
- limb/physical identity summaries
- a versioned identity bridge from Admin DB → runtime generation

## What was implemented (Phase 7 bridge)

Implemented an **additive, low-risk backend module** that reads the existing Admin SQLite schema and exports a single JSON profile that downstream generation/runtime components can consume.

### New files

- `backend/drummerbrain/sentient_profile.py`
  - Core logic:
    - loads Admin SQLite DB
    - derives phrase windows from `fill_events`
    - derives timing profiles from `drum_hit_events.timing_offset_ms`
    - derives dynamics profiles from `drum_hit_events.velocity_est` + role tags (`is_ghost`, `is_accent`)
    - infers a conservative limb summary mapping (heuristic)
    - derives phrase transition probabilities (groove↔fill)
    - exports `sentient_profile_v1`

- `backend/drummerbrain/build_sentient_profile.py`
  - CLI entrypoint for building/exporting the profile JSON.

- `backend/tests/test_sentient_profile.py`
  - Creates a minimal SQLite DB with the relevant tables and asserts the profile builder returns expected structure.

## How to run

### Build a sentient profile from the local Admin DB

From repo root:

```bash
python -m backend.drummerbrain.build_sentient_profile --drummer stewart_copeland
```

Optional overrides:

- Custom DB path:

```bash
python -m backend.drummerbrain.build_sentient_profile --db F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db --drummer stewart_copeland
```

- Custom output path:

```bash
python -m backend.drummerbrain.build_sentient_profile --drummer stewart_copeland --out .\database\sentient_profiles\stewart_copeland\sentient_profile.json
```

### Output location

Default output path:

- `database/sentient_profiles/<drummer_slug>/sentient_profile.json`

## What’s in the output JSON

Top-level keys:

- `schema_version`: `sentient_profile_v1`
- `generated_at`
- `source`: Admin DB path + drummer slug + drummer FK
- `counts`: songs/hits/phrase_windows
- `phrase_library`: list of groove/fill windows (per analysis)
- `timing_profiles`: stats by instrument and subdivision
- `dynamics_profiles`: stats by instrument and role (`ghost`/`accent`/`normal`)
- `limb_summary`: heuristic limb mapping + observed shares
- `phrase_transition`: per-song + global transition probabilities

## How to test

From repo root:

```bash
pytest -q
```

Or target the new test:

```bash
pytest -q backend\tests\test_sentient_profile.py
```

## Notes / current limitations

- Phrase windows are currently derived from `fill_events` only (groove segments are inferred as the regions between fills).
- The timing and dynamics profiles are **summary statistics**; they are not yet full distribution models.
- Limb identity inference is heuristic; it is intended as a placeholder until analysis-time limb inference exists.

