# DrumTracKAI User Manual

This guide explains how to use DrumTracKAI as a drummer assistant: loading audio, analyzing structure, generating drums, editing articulations, and exporting plugin‑ready MIDI.

---

## 1. Installation & Startup

### 1.1 Prerequisites

- Windows (recommended; other OS may work with manual setup)
- Python 3.10+ with virtualenv
- Node.js + npm (for the WebDAW frontend)
- Rust `audio-core` binary available on PATH (for Rust generation), or the PyO3 module if you’re running in-process.

### 1.2 Backend setup

From the repo root (`DrumTracKAI_v1.1.11`):

```bash
# (Optional) create and activate virtualenv
python -m venv drumtrackai_env
# Windows PowerShell
./drumtrackai_env/Scripts/Activate.ps1

pip install -r requirements.txt
```

Environment variables (optional but recommended):

- `USE_RUST=1` – enable Rust generator.
- `AUDIO_CORE_BIN=audio-core` – name or path to Rust CLI (if using CLI mode).
- `AUDIO_CORE_MODE=auto|cli|pyo3` – how to talk to Rust.

Run the backend API server:

```bash
python drumtrackai_api_server_clean.py
```

The API listens on `http://127.0.0.1:8000` by default.

### 1.3 Frontend (WebDAW / DCSM) setup

From `web-frontend/`:

```bash
npm install
npm start
```

Then open the printed URL in your browser (usually `http://localhost:3000`). The DCSM DAW shell will load.

---

## 2. Main Concepts

- **Project / Timeline** – Audio and MIDI live on a shared timeline in the DCSM DAW.
- **Sections** – The audio is divided into sections (intro, verse, chorus, etc.) using sectionization tools.
- **Drums Track & Clip** – A dedicated MIDI track of kind `drums` with one or more clips that hold drum notes.
- **DrumGrid** – A dedicated drum editor for the drums clip, running inside the DCSM DAW.
- **Articulations** – Semantic labels per drum note (e.g. `hh_closed_tight`, `ride_bell`, `snare_rimshot`) that are used later to drive plugin‑specific MIDI exports.
- **Plugin Export** – The system can render your articulated drums into Jamstix / Superior Drummer 3 / SSD5‑compatible MIDI.

---

## 3. Typical Workflow

### 3.1 Analyze audio and sectionize

1. Upload an audio file via the main WebDAW UI (Upload / Analyze flow).
2. Run sectionization:
   - Use automatic tools (e.g. `Sectionize` / `Align Sections`) to split the song into sections.
3. Confirm the sections on the timeline (intro, verse, chorus, bridge, etc.).

> The specific UI around upload and sectionize may appear in a separate panel, but the synced sections will be visible on the DCSM timeline.

### 3.2 Open the DCSM DAW and Drum Editor

1. Open the **DCSM DAW** view (the main modern DAW layout).
2. The left side shows:
   - **TransportBar** (Play, Stop, etc.).
   - **Timeline/BarsBeatsRuler**.
   - **Mixer**.
   - Below Mixer, the **Drum Editor** panel appears.
3. The Drum Editor automatically ensures there is a:
   - `drums` MIDI track.
   - `Main Groove` clip on that track.

If you already have a `drums` track with clips, the Drum Editor uses the first existing drums clip.

### 3.3 Generate a drum groove (with articulations)

Inside the **Drum Editor** panel:

1. At the top, you’ll see:
   - Title: `Drum Editor`.
   - Track and Clip name.
   - A button: **Generate Groove**.
2. Click **Generate Groove**.
   - The app calls the DCSM backend generator (`/dcsm/generate`).
   - The backend uses the Rust core to create a pattern and then assigns an `articulationId` to each note.
   - The generated notes are written into the current drums clip in the MIDI store.
3. After a short delay, notes appear in the **DrumGrid**.

The notes already carry `articulationId` values based on the backend performance spec and articulation selector.

### 3.4 Editing drums in DrumGrid

The DrumGrid (left side of the Drum Editor) is a canvas‑style drum piano roll.

- **Rows** – Mapped to drum instruments (kick, snare, various hats, ride, toms, crashes).
- **Horizontal axis** – Time (bars and beats).
- **Notes** – Rectangles representing drum hits.

You can:

- **Select notes** – Click or drag to select; multiple selection is supported.
- **Move notes** – Drag horizontally (time) or vertically (change drum lane/pitch).
- **Change length** – Drag note edges.
- **Velocity** – Use the velocity lane (if enabled) or other controls for dynamics.

Each note has a small letter label drawn in its rectangle based on its articulation:

- `H` – Hihat articulations (`hh_*`).
- `R` – Ride articulations (`ride_*`).
- `S` – Snare articulations (`snare_*`).
- `T` – Tom articulations (`tom_*`).
- `C` – Crash articulations (`crash_*`).

This lets you see at a glance which notes are special (e.g. bell, open hats, rimshots).

### 3.5 Editing articulations

On the right side of the Drum Editor is the **Drum Articulation Inspector**.

1. **Select notes** in the DrumGrid (one or many).
2. The inspector shows:
   - Focus note metadata (pitch, velocity, channel).
   - **Articulation** dropdown.
3. Articulation options depend on the instrument:
   - **Hi‑hat**: `hh_closed_tight`, `hh_closed`, `hh_slightly_open`, `hh_half_open`, `hh_fully_open`, `hh_pedal_chick`, `hh_splash`.
   - **Ride**: `ride_bow_tip`, `ride_bow_shoulder`, `ride_bell`, `ride_edge`.
   - **Snare**: `snare_center`, `snare_rimshot`, `snare_sidestick`, `snare_ghost`.
   - **Tom**: `tom_center` (can be extended later).
   - **Crash**: `crash_normal`, `crash_bell`, `crash_choke`.
4. Choose a new articulation in the dropdown.
   - The inspector updates **all selected notes** while keeping their timing and velocity.

You never see raw MIDI CCs here—only semantic articulation IDs.

### 3.6 Exporting articulated drums to plugins

To export drums MIDI for a plugin (Jamstix, Superior Drummer 3, SSD5):

1. In the DCSM DAW toolbar, click **Export** to open the Export dialog.
2. Choose **Export mode**:
   - `Stereo mixdown` – Queue a stereo audio export via backend worker.
   - `Stems (multi-track)` – Queue stem exports.
   - `Drums MIDI (articulated, plugin-specific)` – New MIDI export.
3. If you pick **Drums MIDI (articulated, plugin-specific)**:
   - Select **Target plugin**: `Jamstix`, `Superior Drummer 3`, or `SSD5`.
   - The dialog uses the current **drums MIDI clip** (the same one shown in Drum Editor).
   - It sends notes plus `articulationId` and `ppq` to `/dcsm/export_midi`.
   - You’ll be prompted to save a `.mid` file.
4. Load the exported MIDI into the chosen plugin in your DAW.
   - The articulation map ensures notes and CCs line up with the plugin’s expected keyswitches / CC ranges.

---

## 4. Tips & Best Practices

- **Keep one main drums clip** for a section when exporting plugin MIDI; it simplifies mapping.
- Use articulations intentionally:
  - Closed vs open hats.
  - Ride bow vs bell.
  - Snare center vs rimshot / sidestick.
- You can regenerate a groove and then **hand‑edit articulations** for key phrases (fills, choruses) before exporting.
- Save your DAW project and exported MIDI files under clear names per song and plugin.

---

## 5. Troubleshooting

- **No notes appear after Generate Groove**:
  - Make sure the backend is running (`python drumtrackai_api_server_clean.py`).
  - Check browser dev tools → Network for errors calling `/dcsm/generate`.
- **Export dialog says "No drums clip found"**:
  - Ensure the Drum Editor is visible and a drums clip exists.
  - Use the Drum Editor once to guarantee the default drums track/clip is created.
- **Plugin MIDI doesn’t sound correct**:
  - Verify you picked the matching plugin in the Export dialog.
  - Check that the plugin is using the stock mapping that matches the JSON maps in `config/articulation_maps/`.
- **Backend errors**:
  - Look at the console where `drumtrackai_api_server_clean.py` is running; errors will be logged with context.

---

## 6. Where to go next

- Experiment with different performance specs and styles once those controls are exposed in the UI.
- Extend articulation maps (JSON) if you customize plugin mappings.
- Use the exported MIDI files as a starting point in your main DAW, layering additional human tweaks.
