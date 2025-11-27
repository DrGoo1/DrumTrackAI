# DrumTracKAI Admin & Operator Guide

This document is for operators and power users who manage the DrumTracKAI environment, admin flows, and LLM integration.

---

## 1. High-Level Architecture

### 1.1 Components

- **Backend API (Python / aiohttp)**
  - File: `drumtrackai_api_server_clean.py`
  - Responsibilities: file upload, waveform analysis, tempo/section analysis, DCSM drum generation, articulation assignment, plugin MIDI export, session handling.
- **Rust `audio-core`**
  - Called via CLI or PyO3.
  - Handles heavy audio tasks: analysis, smart sectionization, drum pattern generation.
- **Frontend WebDAW / DCSM (React/TypeScript)**
  - Folder: `web-frontend/src/`
  - Contains the modern DAW shell (`AppDAW`), MIDI store (`midiStore.ts`), DrumGrid editor, articulation inspector, export dialog.
- **JUCE / tracktion-hybrid components** (optional desktop integration)
  - Folder: `tracktion-hybrid/cpp/`
  - `DCSMOrchestrator`, `DCSMAdapter` integrate Rust core with Tracktion Engine and JUCE timeline.
- **Articulation mapping & selection**
  - `backend/articulation_selector.py` – chooses `articulationId` per note based on performance spec, section labels, and instrument logic.
  - `backend/articulation_mapper.py` – loads plugin articulation maps (JSON) and can classify MIDI → articulation or provide metadata for each `articulationId`.
  - `backend/render_to_plugin_midi.py` – converts logical notes + `articulationId` → plugin-specific MIDI (notes + CC states).

---

## 2. Backend Structure & Key Endpoints

### 2.1 Server entrypoint

- `drumtrackai_api_server_clean.py`
  - Sets up aiohttp app and CORS.
  - Configures `UPLOAD_DIR`, `SESSIONS_DIR`, `AUDIO_CORE_BIN`, `USE_RUST`, `AUDIO_CORE_MODE`.
  - Provides helpers for invoking `audio-core` via CLI or PyO3.

### 2.2 Analysis and session endpoints

- `GET /healthz` – health check.
- `POST /files/upload` or `/api/upload` – save audio, compute waveform.
- `GET /files/waveform` – retrieve waveform/peaks.
- `GET /files/audio` – serve raw audio.
- `GET /analyze/tempo` – tempo + beat grid.
- `GET /analyze/onsets` – onset times (Python fallback).
- `POST /analyze/tempo_sections` – tempo per section (if implemented).
- `POST /align/sections` – align sections to beats.
- `POST /session/{sid}` / `GET /session/{sid}` – save/load analysis or DAW state.

### 2.3 DCSM-specific endpoints

- `GET /dcsm/sectionize`  
  - Mode `simple` or `smart` (Rust) to detect sections with labels.
- `POST /dcsm/generate`  
  - Input: `{ bpm, section: { start, end, density, swing, humanize, style, label? }, performance_spec? }`.
  - Pipeline:
    1. Calls Rust `audio-core` to generate notes.
    2. Augments each note with `articulationId` via `select_articulation_for_note`.
    3. Returns JSON notes and optionally base64 MIDI.
- `POST /dcsm/export_midi`  
  - Input: `{ plugin, ppq, notes: [{ t0, t1, pitch, vel, chan, articulationId }] }`.
  - Uses `render_articulated_notes_to_midi` to map into plugin-specific note/CC patterns.
  - Returns `{ plugin, midi_base64, ticks_per_beat, filename }`.

### 2.4 Benchmarks & legacy

- `GET /bench/*` – performance benchmarking for peaks/analysis/generation.
- `POST /generate/midi_sections` – older multi-track MIDI generator (not DCSM-specific).

---

## 3. LLM & Performance Spec Integration

### 3.1 Concept

The LLM produces a **performance specification** for drums per section, describing:

- Style (e.g. rock, funk, halftime).
- Density and complexity.
- Articulation tendencies (e.g. tight hats in verses, more open hats in choruses).
- Humanization and swing profiles.

This **performance_spec** is fed into `dcsm_generate` and then into `articulation_selector` to assign `articulationId` per note.

### 3.2 Flow

1. Frontend or orchestration layer asks LLM (outside this repo) for a performance spec, based on:
   - Song analysis.
   - User preferences (drummer archetype, intensity, etc.).
2. The spec is sent to the backend along with `bpm` and section info:
   ```json
   {
     "bpm": 120,
     "section": { "start": 0.0, "end": 8.0, "density": 0.7, "swing": 0.1, "style": "modern rock", "label": "verse" },
     "performance_spec": { ... }
   }
   ```
3. `dcsm_generate` calls Rust `audio-core` to get raw notes, then:
   - For each note, calls `select_articulation_for_note(note, performance_spec, section_label)`.
   - Writes `articulationId` back into the note dict.
4. Frontend receives notes with `articulationId` and shows them in DrumGrid / articulation inspector.

### 3.3 `articulation_selector` overview

- Module: `backend/articulation_selector.py`.
- Core function: `select_articulation_for_note(note, performance_spec, section_label)`.
- Uses:
  - `note.lane` / `pitch` to determine instrument family (kick/snare/hh/ride/tom/crash).
  - Section label (e.g. `verse`, `chorus`, `bridge`) to adjust patterns.
  - Performance spec knobs (e.g. hat openness in choruses, ghost notes in verses).
- Returns canonical articulation IDs like `hh_closed_tight`, `ride_bell`, `snare_rimshot`.

Admin can tune this module to reflect house style preferences.

---

## 4. Articulation Maps & Plugin Integration

### 4.1 Map format

Directory: `config/articulation_maps/`

Example structure per file (pseudo‑JSON):

```json
{
  "plugin_name": "Jamstix",
  "articulations": {
    "hh_closed_tight": {
      "note": 42,
      "cc": [ { "controller": 4, "value": 0 } ]
    },
    "hh_fully_open": {
      "note": 46,
      "cc": [ { "controller": 4, "value": 127 } ]
    },
    "snare_rimshot": {
      "note": 40,
      "cc": []
    }
  }
}
```

- `note` – MIDI note number to trigger that articulation.
- `cc` – optional list of CC settings to apply at note‑on time.

### 4.2 `ArticulationMapper`

- Loads a map file and exposes:
  - `all_articulations()` – raw map.
  - `get_articulation(articulation_id)` – returns config dict.
  - `classify_from_midi(pitch, cc_state)` – best matching `articulationId` from live MIDI.

This is used by `render_to_plugin_midi` to go from semantic IDs to concrete MIDI events.

### 4.3 `render_to_plugin_midi`

- Maps plugin IDs to map files:
  - `jamstix -> jamstix.json`
  - `sd3 -> superior_drummer3.json`
  - `ssd5 -> ssd5.json`
- For each logical note:
  - Look up `articulationId` in the map.
  - Use `note` from the map if present; otherwise fall back to original pitch.
  - Emit CC changes specified in `cc` before the note_on.
- Produces a Type‑1 MIDI file with:
  - A tempo meta event (currently constant 120 BPM by default).
  - A single performance track for drums.

Admins can extend mappings (add articulations, support new plugins) by editing / adding JSON maps.

---

## 5. Frontend DAW & MIDI Store

### 5.1 MIDI store (Zustand)

- File: `web-frontend/src/midi/midiStore.ts`
- State: `MidiSong` with fields:
  - `ppq`, `tempoMap`, `timeSig`, `sections`, `tracks`.
- Exposed methods:
  - Track management: `addTrack`, `removeTrack`, `updateTrack`, `toggleMute`, `toggleSoloExclusive`.
  - Clip management: `addClip`, `removeClip`, `updateClip`.
  - Note management: `updateNotes`, `addNote`, `removeNote`, `updateNote`.
  - Utility: `getTrack`, `getClip`, `getAllNotes`, `clearAll`, `importSong`, `exportSong`.
- `MidiNote` now includes optional `articulationId?: string`.

### 5.2 DCSM App shell

- File: `web-frontend/src/daw/AppDAW.tsx`
- Responsibilities:
  - Initialize `DrumEngine` with kitMap.
  - Maintain playback cursor synced with Tone.Transport.
  - Derive visible timeline length from project.
  - Ensure a `drums` track + default clip exists for the Drum Editor.
  - Layout panels: Transport, Timeline, Mixer, Drum Editor, ImpactDrums, GrooveCoach, Review, Kit/Export/Pocket modals.

### 5.3 Drum Editor & articulation UI

- `DrumEditorPanel.tsx`
  - Accepts `trackId` and `clipId`.
  - Ensures the track is `kind === 'drums'`.
  - Hosts `DrumGrid` (canvas) and `DrumArticulationInspector`.
  - Provides a **Generate Groove** button wired to `/dcsm/generate`.

- `DrumGrid.tsx`
  - Canvas drum editor bound to `useMidi`.
  - Renders notes and selection.
  - Draws small articulation label (H/R/S/T/C) based on `articulationId` prefix.
  - Exposes `onSelectionChange` to notify parent of selected note IDs.

- `DrumArticulationInspector.tsx`
  - Reads notes from `useMidi` for a given track/clip.
  - Shows articulation dropdown based on instrument family.
  - Calls `updateNote` to change `articulationId` for selected notes.

### 5.4 Export dialog

- `ExportDialog.tsx`
  - Modes:
    - `stereo` – queue stereo audio export via `/api/exports`.
    - `stems` – queue multi‑track stems.
    - `midi_plugin` – new plugin‑specific MIDI export.
  - MIDI plugin export mode:
    - Reads current drums track (`kind === 'drums'`) and its first clip.
    - Collects notes with `t0`, `t1`, `pitch`, `vel`, `chan`, `articulationId`.
    - Calls `dcsmExportMidi` (frontend helper for `/dcsm/export_midi`).
    - Downloads the returned `.mid` file.

Admins should verify the mapping between DAW’s drums clip and physical kit (via kitMap) to ensure consistent exports.

---

## 6. Operational Practices

### 6.1 Environment management

- Keep a dedicated virtualenv (`drumtrackai_env`) with locked dependencies.
- Ensure `audio-core` binary or PyO3 module is compatible with the backend.
- Configure environment variables via `.env` or process manager (systemd, PM2, etc.).

### 6.2 Backups & versioning

- Use Git for version control:
  - Commit after major feature additions (e.g. articulation/export).
  - Tag stable milestones.
- Optionally schedule:
  - Periodic zip backups of the repo.
  - Backups of `uploads/` and `sessions/` if you care about stored analysis.

### 6.3 Monitoring & logging

- The backend logs via Python `logging` to stdout.
- Monitor:
  - Errors from Rust CLI (`run_audio_core_cli`).
  - JSON decode errors from `audio-core`.
  - Errors in `dcsm_generate` and `dcsm_export_midi`.

### 6.4 Extensibility

As an admin you can:

- Add new plugins:
  - Create a new JSON map in `config/articulation_maps/`.
  - Extend `_load_mapper` in `render_to_plugin_midi.py` to recognize the plugin id.
  - Add the plugin to the Export dialog dropdown.
- Tune articulation behavior:
  - Edit `articulation_selector.py` heuristics (e.g. more open hats in choruses, ghost notes before downbeats).
- Integrate new LLM models:
  - Plug new prompt templates or models into the orchestration layer that produces `performance_spec`.

---

## 7. Admin Checklist

- [ ] Backend API running, `USE_RUST=1` when applicable.
- [ ] `audio-core` binary or PyO3 module installed and tested (bench endpoints).
- [ ] Articulation maps validated for each supported plugin.
- [ ] Web frontend builds and loads DCSM DAW without TypeScript errors.
- [ ] Drum Editor successfully generates grooves and shows articulation labels.
- [ ] Export dialog can produce plugin‑specific MIDI that behaves correctly in target DAWs/plugins.
