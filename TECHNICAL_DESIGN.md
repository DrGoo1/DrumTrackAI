# DrumTracKAI Technical Design

This document describes the architecture and technical implementation details of DrumTracKAI with a focus on DCSM integration, drum articulations, and plugin‑specific export.

---

## 1. System Overview

DrumTracKAI consists of four main layers:

1. **Frontend WebDAW (React/TypeScript)** – User interface for audio/MIDI visualization, drum editing, articulation control, and export.
2. **Backend API (Python / aiohttp)** – Orchestrates file storage, analysis, drum generation, articulation assignment, and export.
3. **Rust `audio-core`** – High‑performance engine for waveform analysis, tempo detection, sectionization, and raw drum pattern generation.
4. **Plugin / DAW integration** – JUCE/Tracktion components (optional) and plugin‑specific MIDI export via articulation maps.

Data flows between these layers are JSON over HTTP for the web path and in‑process or CLI for backend to Rust.

---

## 2. Backend Architecture

### 2.1 Server stack

- Framework: `aiohttp`
- File: `drumtrackai_api_server_clean.py`
- Key responsibilities:
  - File upload and waveform generation.
  - Onset / tempo / section analysis.
  - DCSM drum generation (`/dcsm/generate`).
  - Articulation assignment via `articulation_selector`.
  - Plugin‑specific MIDI export (`/dcsm/export_midi`).

### 2.2 Rust integration

Configuration:

- `AUDIO_CORE_BIN` – location/name of Rust CLI.
- `USE_RUST` – enable/disable Rust usage.
- `AUDIO_CORE_MODE` – `auto`, `cli`, or `pyo3`.

Helpers:

- `run_audio_core(args: list) -> dict` – central access point that prefers PyO3 when available, otherwise falls back to CLI.
- `run_audio_core_pyo3` – maps subcommands like `peaks`, `analyze`, `sectionize-smart`, `generate` to corresponding Rust functions.
- `run_audio_core_cli` – spawns the `audio-core` process with given args, parses JSON stdout.

Rust `generate` output is expected to be JSON with at least a `notes` array for drums.

### 2.3 DCSM drum generation

Endpoint: `async def dcsm_generate(request)`

1. Parse JSON body:
   ```python
   data = await request.json()
   bpm = data.get("bpm", 120.0)
   section = data.get("section", {})
   start = section.get("start", 0.0)
   end = section.get("end", 4.0)
   density = section.get("density", 0.6)
   swing = section.get("swing", 0.1)
   humanize = section.get("humanize", 0.15)
   style = section.get("style", "rock")
   performance_spec = data.get("performance_spec") or {}
   section_label = section.get("label", "section")
   ```

2. Invoke Rust `audio-core` with generation arguments (implementation depends on core version).

3. Receive a `result` dict containing, at minimum, `notes`:
   ```python
   notes = result.get("notes")
   ```

4. If `notes` is a list and `performance_spec` is provided, iterate and assign articulations:
   ```python
   if isinstance(notes, list) and performance_spec:
       for n in notes:
           n["articulationId"] = select_articulation_for_note(n, performance_spec, section_label)
   ```

5. Return JSON to the frontend: `web.json_response(result)`.

The server therefore centralizes semantic articulation assignment after raw pattern generation.

---

## 3. Articulation Selection Logic

Module: `backend/articulation_selector.py`

### 3.1 Inputs

- `note` – raw note dict from Rust (contains at least `time` and `lane`, optionally `pitch`, `vel`).
- `performance_spec` – structured description from LLM/orchestrator (style, density, hat openness pattern, etc.).
- `section_label` – human label for the section (e.g. `intro`, `verse`, `chorus`).

### 3.2 Process

1. **Instrument classification** – map note lane/pitch to a family:
   - Kick, Snare, Hi‑hat, Ride, Tom, Crash, Other.
2. **Section context** – adjust rules based on `section_label`.
   - Verses may favor tighter hats.
   - Choruses may introduce more ride/cymbal action.
3. **Performance spec interpretation** – inspect LLM knobs, such as:
   - `hat_openness_chorus`, `ghost_notes_enabled`, `ride_usage`, `crash_density`.
4. **Articulation choice** – for each note:
   - Choose one from a finite set per family (e.g. `hh_closed_tight`, `hh_half_open`, `ride_bell`, `snare_rimshot`).

### 3.3 Output

- A canonical `articulationId` string, e.g.: `"hh_closed_tight"`, `"ride_bell"`, `"snare_ghost"`.

The exact heuristics are implemented within this module and can be iterated over time without touching the Rust core.

---

## 4. Articulation Maps and MIDI Export

### 4.1 Map loader

Module: `backend/articulation_mapper.py`

- Loads JSON map from `config/articulation_maps/*.json`.
- Data model:
  - `self.articulations: Dict[str, Any]` keyed by `articulationId`.
- Methods:
  - `all_articulations()` – returns the full articulation dict.
  - `get_articulation(articulation_id)` – per‑ID config (note/CCs/etc.).
  - `classify_from_midi(pitch, cc_state)` – (future use) guess `articulationId` from incoming notes/CCs.

### 4.2 Plugin MIDI rendering

Module: `backend/render_to_plugin_midi.py`

#### 4.2.1 `_load_mapper(plugin: str)`

- Maps plugin identifiers to map files:
  - `"jamstix" -> "jamstix.json"`
  - `"sd3" -> "superior_drummer3.json"`
  - `"ssd5" -> "ssd5.json"`
- Returns an `ArticulationMapper` instance.

#### 4.2.2 `render_articulated_notes_to_midi(payload)`

- Expected payload:
  ```python
  {
    "plugin": "jamstix" | "sd3" | "ssd5",
    "ppq": 480,
    "notes": [
      {"t0": int, "t1": int, "pitch": int, "vel": int, "chan": int, "articulationId": str | None},
      ...
    ],
  }
  ```

- Steps:
  1. Load plugin map.
  2. Create a `MidiFile(type=1)` with `ticks_per_beat = ppq` and one `MidiTrack`.
  3. Insert a constant tempo meta event (120 BPM) for now.
  4. For each note:
     - Get `art = mapper.get_articulation(art_id)` if available.
     - Compute `note_num = art["note"]` if present else fallback to `pitch`.
     - Get CC specs from `art["cc"]` if any.
     - Add two logical events:
       - `note_on` at `t0` with associated CC list.
       - `note_off` at `t1`.
  5. Sort events by `tick`.
  6. Walk events in order, translating absolute tick times to delta ticks (`time` field in mido messages):
     - Emit all CC messages first at a given tick (first CC carries the delta, subsequent CCs at time 0).
     - Emit the note_on/off message after CCs (time 0 if CCs were emitted, or the delta if not).
  7. Append `end_of_track` meta event.
  8. Save MIDI to `BytesIO`, base64‑encode, return `{ plugin, midi_base64, ticks_per_beat }`.

This allows consistent plugin behavior from semantic articulations across different drum instruments.

### 4.3 Export endpoint

Endpoint: `async def dcsm_export_midi(request)` in `drumtrackai_api_server_clean.py`.

- Request JSON is passed directly to `render_articulated_notes_to_midi`.
- Wraps the result into:
  ```python
  {
    "plugin": result["plugin"],
    "midi_base64": result["midi_base64"],
    "ticks_per_beat": result["ticks_per_beat"],
    "filename": f"dcsm_export_{timestamp}.mid",
  }
  ```
- On error, logs with `LOG.error` and returns `{ "error": str(e) }` with 500.

---

## 5. Frontend Architecture

### 5.1 MIDI data model

File: `web-frontend/src/midi/types.ts`

Key types:

- `export type Tick = number;`
- `export type MidiNote = { id: string; t0: Tick; t1: Tick; pitch: number; vel: number; chan: number; articulationId?: string }`.
- `export type MidiClip = { id: string; name: string; startTick: Tick; endTick: Tick; notes: MidiNote[] }`.
- `export type MidiTrackKind = 'drums' | 'keys' | 'bass' | 'other';`
- `export type MidiTrack = { id: string; name: string; kind: MidiTrackKind; chan: number; clips: MidiClip[]; muted: boolean; solo: boolean }`.
- `export type MidiSong = { ppq: number; tempoMap: TempoPt[]; timeSig: [number, number]; sections: ArrangementSection[]; tracks: MidiTrack[] }`.

`articulationId` is optional so legacy flows and other instruments do not break.

### 5.2 MIDI store (Zustand)

File: `web-frontend/src/midi/midiStore.ts`

- Maintains a singleton `MidiSong` instance in React context via Zustand.
- Provides mutation functions (`addTrack`, `addClip`, `updateNotes`, etc.) that update the immutable tree.
- Additional selectors/hooks:
  - `useMidiTracks`, `useMidiTrack`, `useMidiTempoMap`, `useMidiSections`.

### 5.3 DCSM DAW app shell

File: `web-frontend/src/daw/AppDAW.tsx`

- Imports `useMidi` and ensures a drums track/clip exists:
  - On mount, if no `kind === 'drums'` track is present, it creates one with `chan: 10` and a `Main Groove` clip.
- Renders:
  - `TransportBar`, `BarsBeatsRuler`, `Timeline` at the top.
  - Left column: `Mixer`, `DrumEditorPanel`, `ImpactDrumsPanel`.
  - Right column: `GrooveCoachPanel`, `ReviewPanel`.
- Uses Tone.js for transport and `useDawStore` for shared DAW state (cursor position, project, kitMap).

### 5.4 Drum Editor

File: `web-frontend/src/daw/ui/DrumEditorPanel.tsx`

- Props: `{ trackId: string; clipId: string }`.
- Internals:
  - Reads `track` and `clip` from `useMidi`.
  - Reads `song` and `updateNotes` from `useMidi`.
  - Maintains `selectedNoteIds` for inspector.
  - Provides `handleGenerate` method:
    - Determines `bpm` from `song.tempoMap[0]`.
    - Calls `dcsmGenerate(bpm, section)` where `section` is currently a simple range.
    - Converts returned notes (`time`, `lane`, `vel`, `articulationId`) to `MidiNote` ticks using `ppq` and `bpm`.
    - Maps lanes to GM‑style pitches (`kick->36`, `snare->38`, `hihat->42`, etc.).
    - Calls `updateNotes(trackId, clipId, notes)`.

Renders:

- Header row with track/clip label and **Generate Groove** button.
- Two-column grid:
  - 8 columns: `DrumGrid` (note editor), with `onSelectionChange`.
  - 4 columns: `DrumArticulationInspector` (articulation editor).

### 5.5 DrumGrid

File: `web-frontend/src/midi/ui/DrumGrid.tsx`

- Core responsibilities:
  - Render notes in a per‑lane grid.
  - Manage note selection, drag/move/resize interactions.
  - Paint velocity overlay if enabled.
- Articulation visualization:
  - For each rendered note, reads `note.articulationId`.
  - Derives a one-letter label: `H`, `R`, `S`, `T`, `C` based on prefix.
  - Draws it at the corner of the rectangle.
- Selection reporting:
  - New prop: `onSelectionChange?: (noteIds: string[]) => void`.
  - Internally keeps a `selectedNotes: Set<string>` and, via `useEffect`, notifies parent when it changes.

### 5.6 DrumArticulationInspector

File: `web-frontend/src/daw/ui/DrumArticulationInspector.tsx`

- Props: `{ trackId: string; clipId: string; selectedNoteIds: string[] }`.
- Locates the clip from `useMidi` and determines a focus note (first in selection).
- Instrument family detection:
  - Based on `pitch` (GM numbers) map to `kick`, `snare`, `hihat`, `ride`, `tom`, `crash`.
- Articulation options per family (as in the user manual).
- On dropdown change:
  - Calls `updateNote(trackId, clipId, noteId, { articulationId })` for each selected note.

### 5.7 Export dialog

File: `web-frontend/src/daw/ui/ExportDialog.tsx`

- Uses `useDawStore` for job/kit info and `useMidi` for the song.
- Export modes:
  - `stereo` – uses legacy `/api/exports` queue for a stereo render.
  - `stems` – uses `/api/exports` with `mode='stems'`.
  - `midi_plugin` – plugin‑specific drums MIDI export.
- MIDI plugin mode:
  - Finds `drumsTrack = song.tracks.find(t => t.kind === 'drums')` and `clip = drumsTrack?.clips[0]`.
  - Builds `notesPayload` from `clip.notes` projecting the fields required by backend.
  - Calls `dcsmExportMidi({ plugin, ppq: song.ppq, notes: notesPayload })`.
  - Decodes `midi_base64` to a Blob and triggers a browser download.

Frontend and backend are therefore tightly aligned on the note and articulation schema.

---

## 6. API Client Layer

File: `web-frontend/src/services/api.ts`

Relevant functions:

- `dcsmGenerate(bpm, section)`
  - POSTs `{ bpm, section }` to `/dcsm/generate`.
  - Response type: `{ notes: Array<{ time, lane, vel, articulationId? }>; midi_b64: string }`.

- `generateDrumPattern(payload)`
  - Compatibility wrapper using the same `/dcsm/generate` endpoint with a different payload shape.

- `dcsmExportMidi(payload)`
  - POSTs `{ plugin, ppq, notes: [{ t0,t1,pitch,vel,chan,articulationId? }] }` to `/dcsm/export_midi`.
  - Response type: `{ plugin, midi_base64, ticks_per_beat, filename, error? }`.

The API client isolates HTTP details from DAW UI code.

---

## 7. Error Handling & Edge Cases

### 7.1 Backend

- JSON decode errors in endpoints return `{"error":"invalid JSON body"}` with 400.
- Rust integration failures are caught and logged; some endpoints may fall back to Python or respond with an error.
- `dcsm_export_midi` wraps all exceptions and logs them with `LOG.error`.

### 7.2 Frontend

- Drum Editor’s generate button tracks a `busy` state and logs errors to console.
- Export dialog uses alerts to surface failures (e.g. empty MIDI or network/HTTP issues).
- If there is no drums clip, the MIDI export option warns the user.

### 7.3 Type safety

- TypeScript types for API results include optional `articulationId` so older backends (without articulations) still compile.
- `MidiNote.articulationId` is optional for similar reasons.

---

## 8. Extension Points

### 8.1 Additional articulations

- Add new `articulationId` values to `articulation_selector.py` and ensure they are represented in articulation maps.
- Update `DrumArticulationInspector` to expose them in the UI.
- Optionally adjust DrumGrid label logic to show different letters or icons.

### 8.2 New plugins

- Add a new map file to `config/articulation_maps/`, e.g. `ezdrummer2.json`.
- Extend `_load_mapper` in `render_to_plugin_midi.py` to recognize the new plugin ID and load the file.
- Add a new option in `ExportDialog`’s plugin dropdown.

### 8.3 LLM orchestration

- Integrate a richer LLM pipeline that feeds `performance_spec` into `/dcsm/generate`.
- Add frontend controls for the user to select drummer style, groove complexity, etc., mapped into `performance_spec`.

---

## 9. Summary

DrumTracKAI’s technical design separates concerns cleanly:

- Rust handles heavy audio analysis and initial drum generation.
- Python orchestrates workflows, assigns human‑meaningful articulations, and handles plugin‑specific exports.
- React/TypeScript provide a modern DAW UI with a dedicated drum editor and articulation inspector.
- Articulation IDs form the semantic bridge between LLM instructions, symbolic note editing, and concrete plugin MIDI protocols.

This architecture is designed to be:

- **Extensible** – Add new plugins, articulations, or stylistic rules without changing the Rust core.
- **Robust** – Optional fields and fallbacks keep older flows working.
- **LLM‑friendly** – Notes and articulations are represented as clear JSON objects suitable for training and inference.
