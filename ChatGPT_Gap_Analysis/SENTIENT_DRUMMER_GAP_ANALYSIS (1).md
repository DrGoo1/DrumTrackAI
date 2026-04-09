# DrumTracKAI v1.1.17 — Sentient Drummer Gap Analysis

Snapshot reviewed
- Repo snapshot: `DrumTracKAI_v1.1.17`
- Git commit: `24ff6d74e76f04d35a80c077b5ba8fd562f3b3e8`
- Branch: `full-snapshot`

## What already exists

### Admin assimilation pipeline
Implemented and wired enough to be operational:
- ingestion/provenance tables
- Phase 2 hit event extraction
- Phase 3 fill + technique heuristics
- Phase 4 microtiming/dynamics summaries
- Phase 5 drummer rollups
- Phase 6 persona inference, preset generation, JSON export

### Backend generation stack
Present in codebase today:
- `backend/drum_generation/*`
- DCSM/Jamstix-style rich note schema with limb, hit style, timing offsets, hat openness, performance groups
- performance spec builder and tests
- `llm_service/app.py` endpoints for humanization params, performance spec, and song roadmap

### DrummerBrain runtime groundwork
Present in codebase today:
- deterministic dataset ingestion for audio phrases, drumbeats, written references, transcription artifacts
- runtime selection against a clip database
- evaluation harness and tests

### Frontend + plugin integration groundwork
Present in codebase today:
- DCSM track types and track utilities
- rehumanization utilities and panel
- drummer/persona related UI state
- plugin connector with guide-track transport concepts

## What is missing for a true Sentient Drummer

### 1. Canonical phrase layer
Current system stores hits, fills, techniques, and rollups, but not a reusable phrase library that generation can retrieve from.

Impact:
- no phrase-level memory
- no phrase embeddings
- no stable groove/fill vocabulary per drummer

### 2. Directional timing fingerprint
Current system stores timing variance and per-hit offset, but not an aggregated timing fingerprint by instrument + subdivision + role.

Impact:
- can describe tight/loose
- cannot reproduce pushed kick / laid-back snare / ride lead timing character

### 3. Context-conditioned dynamics
Current system stores summary dynamics, but not velocity profiles by musical role.

Impact:
- backbeat, ghost, fill, and timekeeping behavior are not independently modeled

### 4. Transition model
Current system counts fills and techniques, but does not model groove→fill→groove decisions.

Impact:
- generated drums can sound assembled rather than intentional

### 5. Limb/physical identity at analysis time
The DCSM generation schema supports limb IDs, but the assimilation pipeline does not infer and store limb behavior from analyzed performances.

Impact:
- no physical identity loop between analysis and generation

### 6. Hi-hat state model
The runtime/generation schema can represent hat openness, but the assimilation side does not build a drummer-specific hi-hat behavior profile.

### 7. Identity bridge from admin DB → runtime generation
There is currently no strong, versioned sentient profile artifact that plugs the admin assimilation output into the runtime generator.

### 8. Product-grade style validation
You already have evaluation infrastructure, but not the right sentient-drummer validation layers:
- reconstruction similarity
- persona consistency
- style transfer preservation
- blind ranking harness

## Recommended implementation order
1. Add phrase windows and sentient profile export from the current admin DB.
2. Add timing profiles by instrument/subdivision/role.
3. Add dynamics profiles by instrument/role.
4. Add phrase transition matrix.
5. Add limb summary inference.
6. Consume the sentient profile in generation and rehumanization.
7. Add objective validation harnesses.

## Patch included with this report
This patch adds a backend-facing Phase 7 bridge:
- `backend/backend/drummerbrain/sentient_profile.py`
- `backend/backend/drummerbrain/build_sentient_profile.py`
- `backend/backend/tests/test_sentient_profile.py`

What it does:
- loads the current admin SQLite schema
- builds phrase windows from bar/fill structure
- derives timing profiles
- derives dynamic profiles
- derives limb summary
- derives phrase transition probabilities
- exports a single sentient profile JSON artifact

This is intentionally additive and low-risk. It does not overwrite your Phase 1–6 pipeline.
