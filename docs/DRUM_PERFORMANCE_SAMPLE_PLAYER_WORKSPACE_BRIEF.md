---
description: Drum Performance Sample Player workspace brief
---

# Goal
Build a state-of-the-art drum performance sample player for DrumTracKAI using studio-sampled drums (your kit), with a repeatable sample-factory pipeline and a modern playback engine that fits the existing DrumTracKAI scaffold.

This document is intended to be copied into a separate Windsurf workspace dedicated to the new sample player + library production pipeline.

# Current DrumTracKAI sample playback scaffold (as-is)

## Frontend: `DrumPlayerEngine` (Web Audio sample player)
File: `frontend/src/audio/drumPlayerEngine.ts`

- **Audio API**
  - Uses a shared `AudioContext` (`getSharedAudioContext`).
  - Loads samples via `fetch(url) -> arrayBuffer -> decodeAudioData`.
  - Plays samples using `AudioBufferSourceNode` one-shots.

- **Mixer topology**
  - Per-channel nodes:
    - `GainNode` (fader)
    - `StereoPannerNode` (pan)
    - 2 send gain nodes: `sendOhNode`, `sendRoomNode`
    - Per-channel `AnalyserNode`
  - Buses:
    - `oh` bus gain -> oh analyser -> master
    - `room` bus gain -> room analyser -> master
  - Master gain -> analyser -> destination

- **Channels (current IDs)**
  - `kick`, `kick_sub`
  - `snare_top`, `snare_bottom`
  - `tom1`..`tom5`, `tom_fx`
  - `hat`, `ride`, `spot_ride`, `crash`

- **Onset/trim handling (important)**
  - Implements a robust onset/trim inference (`inferTrimOffsetSec`) and tracks diagnostics.
  - Trim config is controlled by localStorage: `dtk_sample_trim_ms`.

- **What this means**
  - The app already has a working, reasonably modern, multi-channel WebAudio “kit player” with a small mixer.
  - The missing piece is an *industry-grade kit format* (articulations, velocity layers, RR, multi-mics), and higher-level performance behaviors.

## Frontend UI: `DrumPlayerModal` (kit + sample selection UI)
File: `frontend/src/components/drums/DrumPlayerModal.tsx`

- Can load a built-in default kit from static URLs:
  - `/samples/drums/kick.wav`, `/samples/drums/snare.wav`, `/samples/drums/hihat.wav`, etc.
- Can also load kits from backend:
  - `listKits()` -> `/api/kits`
  - `getKitManifest(kitId)` -> `/api/kits/{kitId}/manifest`
- Can browse a sample DB:
  - `/api/sample-collections`
  - `/api/drum-samples?collection_id=...`
  - `/api/drum-samples/{id}/audio`

## Kit manifest contract (already defined)
File: `frontend/src/types/kits.ts`

`KitManifestV1` supports:
- `mics`: list of mic definitions (id/label/default gain)
- `articulations`: per-instrument articulation definitions
  - per mic -> velocity layers -> round robin sample URLs
- optional `chokeGroups` for cymbals/hats

This is the correct place to “land” your studio library format so the player can read it.

## Backend: sample DB + kit manifest endpoints
File: `dcsm_backend.py`

- **Sample DB endpoints**
  - `GET /api/sample-collections`
  - `GET /api/drum-samples`
  - `GET /api/drum-samples/{sample_id}/audio`

- **Path resolution + portability**
  - `_resolve_sample_file_path()` supports:
    - relative (preferred) paths under `SAMPLES_ROOT`
    - legacy absolute Windows paths (e.g. `E:\Drum Samples\...`) with optional prefix mapping via `SAMPLE_PATH_MAP_FROM` -> `SAMPLE_PATH_MAP_TO`

- **Kit endpoints**
  - `GET /api/kits`
  - `GET /api/kits/{kit_id}/manifest`

- **Special kit: `sneap_erkan_local_v1`**
  - Backend constructs a manifest dynamically by querying the sample DB using folder prefixes like:
    - `E:/Drum Samples/Kick Samples/Andy Sneap Kick`
  - It returns URLs of the form:
    - `/api/drum-samples/{id}/audio`

# What we should build next (new workspace scope)

You want two related products:

1. **Sample Factory** (internal pipeline)
2. **Performance Sample Player** (the engine that consumes the library)

They should be coupled only by a stable manifest format (and test fixtures).

# A. Sample Factory (internal drum library production pipeline)

## Outcomes
- A guided recording workflow that produces:
  - trimmed, labeled, velocity-layered, round-robin grouped samples
  - mic-coherent sample sets (close, OH, room, etc.)
  - QA reports + outlier flags
  - a playable `KitManifestV1` output

## Canonical session plan format
Use a strict session plan JSON (close to what you drafted):
- kit name / id
- sample rate / bit depth
- mic list
- targets: instrument + articulation + velocity bins + RR per bin

This session plan is the authoritative input for recording and post.

## Naming convention (machine readable)
Keep your strict convention (kit/instrument/articulation/vel/rr/mic). This is the foundation for automation.

## AI-assisted automation targets (practical)
- Transient/onset detection + trimming
- Feature extraction per hit (RMS/peak/crest/centroid/attack)
- Velocity clustering and binning
- Outlier detection (double hits, flams, clipping, mis-trims)
- Similarity checks for RR consistency

## Deliverable artifacts
- `trimmed/` audio
- `features/*.json` per hit
- `reports/*.json` QA + clustering
- `manifests/kit_manifest_v1.json` compatible with DrumTracKAI

# B. Performance Sample Player (innovative playback engine)

## Primary goal
Turn a DrumTracKAI drum track (MIDI-like notes + articulation IDs) into a realistic, mixable, expressive drum performance using your sampled kit.

## What “innovative” means here (concrete)
Build beyond a simple sampler:

- **Humanized selection (non-repetition)**
  - Round-robin selection that avoids immediate repeats
  - “neighbor-aware” selection for fast rolls (choose alternates)

- **Velocity-aware layers (musical)**
  - Smooth velocity crossfades or hard-switch layers per articulation
  - Optional per-instrument velocity curves (ghost notes vs accents)

- **Articulation system that matches drummers**
  - Hi-hat openness ladder (tight closed -> open)
  - Snare: center / rimshot / sidestick / ghost
  - Ride: bow/tip / bell / edge (and later, inferred timbral variants via velocity)

- **Choke groups & muting rules**
  - Cymbal chokes (grab)
  - Hi-hat mutual exclusion (closed/open/pedal)

- **Multi-mic coherence**
  - One “hit event” triggers a *bundle* of mic samples (close/OH/room), not independent randomization.
  - Per-mic gain defaults and mixer routing.

- **Fast audition + streaming strategy**
  - Preload “core” articulations.
  - Lazy-load rare articulations.
  - Consider sample caching by URL + decode cache.

- **Future advanced realism (phased, not v1)**
  - bleed modeling
  - resonance layers
  - sympathetic shell response
  - cymbal interaction rules

## How this fits the current scaffold
- Keep the **manifest contract** aligned with `KitManifestV1`.
- Initially, keep the **player in the browser** (WebAudio) using `DrumPlayerEngine`.
- Optionally, later add:
  - `AudioWorklet` voice engine for tighter scheduling and DSP
  - or a native plugin target

# Integration plan (phased)

## Phase 0: Documentation + contracts (1–2 days)
- Freeze:
  - kit/articulation vocabulary (`DrumInstrumentId` + articulation IDs)
  - mapping from generated notes -> articulation IDs
  - manifest schema versioning (`KitManifestV1`, later `V2`)

## Phase 1: Factory tools (first usable pipeline)
- Implement the pipeline scaffold you drafted (ingest/features/clustering/qa/manifest writer).
- Ensure output can generate:
  - a valid `KitManifestV1`
  - sample URLs that DrumTracKAI can fetch (either local dev server paths, or via `/api/drum-samples/{id}/audio`).

## Phase 2: Pilot library (minimal kit)
- Record:
  - kick center
  - snare center
  - closed hat
  - ride bow
- Validate:
  - naming
  - RR + velocity
  - multi-mic bundle triggering
  - choke groups

## Phase 3: Full flagship kit
- Execute full capture protocol (shells, cymbals, specialty articulations).
- Expand manifest articulations and mic definitions.

## Phase 4: Musical intelligence + QA at scale
- Add classifiers for articulation detection where relevant (especially hats).
- Add advanced QA (duplicate hits, polarity checks, noise profiling).

# Code starter kit (recommended repo layout in the new workspace)

Create a new folder (in that workspace) like:

- `sample_factory/`
  - `session_plan.json`
  - `config.py`
  - `features.py`
  - `ingest.py`
  - `cluster_velocity.py`
  - `qa.py`
  - `build_manifest.py`

Then extend `build_manifest.py` to emit **exactly** the `KitManifestV1` structure used by the app.

# Key repo touchpoints (for developers)

## Frontend
- `frontend/src/audio/drumPlayerEngine.ts`
  - WebAudio playback, mixer, trim inference
- `frontend/src/components/drums/DrumPlayerModal.tsx`
  - kit selection UI, sample browsing
- `frontend/src/types/kits.ts`
  - `KitManifestV1` contract

## Backend
- `dcsm_backend.py`
  - `/api/kits/*` manifest endpoints
  - `/api/drum-samples/*` audio streaming
  - `_resolve_sample_file_path` (important for Windows + Docker portability)

# Open questions to resolve early
- Are we storing new studio samples in:
  - a new kit-pack folder under `KITS_ROOT`, with relative paths under `SAMPLES_ROOT` (recommended)
  - or in the sample DB only (works, but kit-pack manifests are easier to version and distribute)
- Do we want `KitManifestV2` soon for:
  - per-articulation envelope/ADSR
  - per-mic phase/polarity metadata
  - per-hit feature embeddings for smarter RR selection

# Immediate next actions
- Decide where the flagship kit will live on disk (portable layout).
- Implement `sample_factory/` pipeline and ensure it outputs:
  - trimmed WAVs
  - `KitManifestV1`
- Add a small “kit-pack loader” path in backend so manifests can reference local relative sample files safely.
