# DrumTracKAI v1.1.17 - DCSM DAW & Euclidean Integration

## 🎯 Overview

DrumTracKAI v1.1.17 builds on v1.1.16 by introducing a **new AppDAW-based DCSM page** that unifies all drum-creation workflows (classic, AI, Euclidean) in a single React DAW, fully wired to the Drum Builder v2.0 backend.

## Recent Progress (Dec 26, 2025)

- **MicroTempo Meter**: Prominent realtime BPM/deviation meter driven by `songMap.beatTimes` + playhead.
- **Drum Tempo Mode**: Generation can **Lock** to constant tempo (tight by default) or **Follow** the detected tempo map.
- **Full Song Generation**: "Generate Entire Song" now uses a **single song-aware generation call** with `buildScope: "full_song"` and `songSections` (snake_case labels + bar counts).
- **Section Generation Rename**: Per-section generator button is now labeled **"Generate Section Specific Track"**.
- **Mixer/Metering**: Drum engine strip meters tap **post-pan/post-fader** for more accurate visual levels.

## Recent Progress (Jan 10, 2026) — WebDAWApp v3 Drum Grid + Limb Sync

This checkpoint focused on making the **Drum Performance grid** and **4-limb grid** visually and logically consistent in the v3 UI.

### What was fixed / added

- **Performance grid note positioning + horizontal sync**
  - Refactored the performance-grid note DOM so the **absolute positioning is owned by a plain container element**, not by the `Tooltip` wrapper.
  - This removes subtle wrapper/CSS-induced offsets and makes the **performance grid notes line up with the limb grid hits**.
  - File: `frontend/src/components/drums/DrumPianoRoll.tsx`

- **4-limb inference now matches musical sticking**
  - Implemented improved inferred limb assignment:
    - Cymbal/hat timekeeping updates the "last hand" clock.
    - Snare/toms alternate hands when hits are close in time; otherwise default to conventional sticking.
  - Made inferred limb assignment **authoritative for the 4-limb grid** (can override unreliable upstream `limbId`).
  - Result: 4-limb grid is now aligned with performance hits and shows correct sticking for common patterns.
  - File: `frontend/src/components/drums/DrumPianoRoll.tsx`

- **Debug instrumentation for diagnosing grid issues**
  - Added/extended debug readouts (gated behind `localStorage.drpDebug=1`) to measure:
    - computed vs DOM X alignment for a selected note
    - lane heights, scroll metrics, per-instrument counts, and limb assignment counts
  - File: `frontend/src/components/drums/DrumPianoRoll.tsx`

- **Mode + Scope UI: dropdowns replaced with always-visible either/or options**
  - Replaced "Mode" and "Scope" `<select>` dropdowns with **two-option radio-style controls** so both options are visible at all times.
  - Scope controls remain disabled outside scratch mode.
  - File: `frontend/src/components/v3/V3ImportAnalysisHeader.tsx`

### SD3 support + “Advanced Articulation Mode” (backend MIDI render)

- SD3 articulation map is available:
  - File: `config/articulation_maps/superior_drummer3.json`
- Backend MIDI renderer now supports an explicit flag:
  - Payload field: `advancedArticulations: bool`
  - When `false`: emits only the mapped note pitches.
  - When `true`: additionally emits articulation-map events like:
    - `cc` (e.g. CC4 hat openness)
    - `aftertouch` (rendered as MIDI `polytouch`)
  - File: `backend/render_to_plugin_midi.py`

### Quick test checklist (v3)

- Start the app (recommended):
  - Run `STOP_ALL.bat` then `LAUNCH_WORKING.bat` from repo root.
- In v3, load/generate a drum track and verify:
  - Performance grid notes are aligned in their instrument rows.
  - 4-limb grid hits are time-aligned with performance notes.
  - Typical backbeat snare hits appear on LH in the 4-limb grid.
  - Mode/Scope controls show both choices at once.

### Next steps (building out v3)

- Finish limb-lane alignment polish and remove any remaining spacer/offset inconsistencies between label column and grid.
- Add articulation legend/shading in the UI (different shades per instrument articulation) and decide final articulation encoding strategy.
- Wire UI to expose SD3 export settings (plugin selection + `advancedArticulations` flag) and validate SD3 playback.
- Confirm groove selection actually influences generation for v3 (ensure selected groove id is passed and honored).

Key additions in v1.1.17:

- **New DCSM DAW page at `/`** powered by `AppDAW.tsx`
- **Source Song workflow**: upload drumless audio, backend analysis, arrangement sections
- **Integrated Drum Creation panel** under the piano roll with:
  - Style + drummer **categories** (DrumTracKAI-style groupings)
  - Intensity, variation, humanize, ghost notes, swing, build scope
  - Fill controls (Fill In/Out from sections, fill type, **fill density**)
  - Guide track toggle + instrument (mix, bass, guitar, keys, vocal, other)
  - **Jamstix / Articulation profiles** (balanced, ghosty, tight hats, crashy)
  - **Euclidean mode** with per-lane hits/rotate and presets
- **Drum Builder v2.0 integration** via `/api/generate-drums` including:
  - `generationMode` (template, ai_variation, full_ai, euclidean)
  - `euclideanLanes` for Euclidean mode
  - Performance-layer controls (humanizeAmount, ghostNoteAmount, swingAmount)
- **Waveform strip aligned with the ruler** so arrangement sections, fills and drum hits line up visually with the audio
- **Tempo sync** for injected drums using analyzed BPM from `/analyze/tempo`
- **One-click Export Drums MIDI** using `dcsmExportMidi` (Jamstix/DCSM ready)

The legacy WebDAW/DCSM interface is still available under its own route, but the new DCSM DAW at `/` is the primary landing page in v1.1.17.

- **Professional DAW Plugin** (VST3/AU) for seamless DAW integration
- **Guide Track Feature** for instrument-aware drum generation
- **Advanced Groove Engine** with swing presets and per-lane velocity profiles
- **Multi-bar Fill Library** with style-aware pattern generation
- **Smart Sectionization** with downbeat-aware repetition labeling
- **Type-1 Multi-track MIDI Export** with separate lanes per drum
- **Performance Benchmarking Suite** for Rust vs Python comparison
- **Optional PyO3 Integration** for in-process Rust calls

## 🚀 Quick Start

### Prerequisites
- Python 3.11.9 (critical for LLVM compatibility)
- Node.js v20 LTS
- Rust toolchain (optional, for building from source)
- **NEW:** JUCE Framework 7.0.9 (for building DAW plugin)
- **NEW:** Visual Studio 2019/2022 or Xcode 12+ (for plugin compilation)

### Option 1: Build DAW Plugin
```bash
# Setup JUCE framework
cd DrumTracKAIConnector
SETUP_JUCE.bat

# Build VST3/AU plugin
BUILD_PLUGIN.bat

# Plugin installs to:
# Windows: C:\Program Files\Common Files\VST3\
# macOS: ~/Library/Audio/Plug-Ins/VST3/ or Components/
```

### Option 2: Web Interface (Docker)
```bash
# From project root (Windows)
DOCKER_LAUNCH.bat

# This will:
# - Build and start backend (port 8000) and web-frontend (port 3000)
# - Open http://localhost:3000 in your browser

# Main DCSM DAW (v1.1.17):
#   http://localhost:3000/
# Legacy WebDAW/DCSM:
#   http://localhost:3000/webdaw-legacy
```

### Option 3: Web Interface (manual dev mode)

```bash
# Backend (from project root, with audio-core built)
set USE_RUST=1
set AUDIO_CORE_MODE=auto
python dcsm_backend.py

# Frontend
cd web-frontend
npm install
npm run dev

# Visit http://localhost:3000
```

### v1.1.17 DCSM DAW – Drum Creation Flow

1. **Open the new DCSM DAW**
   - Go to `http://localhost:3000/`

2. **Upload a source song (no drums)**
   - Use the **Source Song** panel on the left to upload audio.
   - Backend performs upload + analysis; you’ll see file name + status.

3. **View waveform and sections**
   - A green **waveform strip** appears under the Bars/Beats ruler.
   - Use **Arrangement Sections** to auto-sectionize and tweak:
     - `start` / `end` (seconds)
     - `density` (0–1)
     - `Fill In` / `Fill Out` flags per section

4. **Configure drum creation** (panel under the Drum Editor)
   - **Style**: musical style (e.g., Studio Rock, Funk Pocket)
   - **Drummer Category**: high-level drummer profiles (e.g., studio_rock, funk_pocket)
   - **Intensity / Variation**: groove energy and movement
   - **Humanize / Ghost / Swing**: performance layer controls
   - **Scope**: build full song vs selected section
   - **Drum & Cymbal Density**: additional density controls
   - **Fill Type & Fill Density**:
     - Fill locations come from section `Fill In` / `Fill Out` flags
     - Fill density scales how strong fills are in those bars
   - **Guide Track**: enable + choose instrument to steer power curve
   - **Jamstix / Articulation profile**: balanced, ghosty, tight hats, crashy (affects Jamstix enrichment)
   - **Mode**:
     - `template`, `ai_variation`, `full_ai` use pattern generator
     - `euclidean` enables Euclidean lanes

5. **Euclidean mode inside the DCSM DAW**
   - Set **Mode = Euclidean** in the Drum Creation panel.
   - A **Euclidean Lanes** section appears:
     - Choose a preset (e.g., *In Fives*, *Techno Pulses*) from `EUCLIDEAN_PRESETS`.
     - Adjust per-lane **Hits** and **Rotate** for kick, snare, hats, ride, crash, etc.
   - On generate, the frontend sends:
     - `generationMode: "euclidean"`
     - `euclideanLanes: [...]` (instrumentId, steps, hits, accents, rotate, velocities)
   - The backend’s Drum Builder v2.0 uses these lanes to construct internal events.

6. **Generate drums and inspect in the editor**
   - Click **Generate Drum Track**.
   - The frontend calls `/api/generate-drums` with the full `DrumGenerationConfig`.
   - On success:
     - `midi_notes` are converted from seconds to ticks using the DAW tempo map.
     - Notes are written into the default **Drums** track/clip via `midiStore.updateNotes`.
   - You can zoom/scroll/play in the **DrumEditorPanel** to inspect the pattern.

7. **Tempo sync**
   - After a source song is loaded, the frontend calls `/analyze/tempo` with the file key.
   - The analyzed BPM is written into the MIDI tempo map (`useMidi.setTempoMap`).
   - Seconds→ticks mapping for injected drums uses this BPM, keeping drum MIDI aligned with source audio.

8. **Export to DCSM / Jamstix**
   - Use the top toolbar **Export Drums MIDI** button in the new DCSM DAW.
   - This calls `dcsmExportMidi` with the current drum notes:
     - `plugin: "jamstix"`
     - `ppq: song.ppq`
     - notes `{ t0, t1, pitch, vel, chan, articulationId? }`
   - The response returns a base64-encoded MIDI file and filename.
   - The frontend triggers a download of a `.mid` file ready for Jamstix or any DAW.

## 🥁 Jamstix Limb Editor & Limb Meta (v1.1.17)

v1.1.17 introduces a Jamstix-style **Limb Bar Editor** and a new limb-based drum editing workflow. This becomes the primary editing surface for drums in the DCSM DAW.

### Frontend Components

- **`web-frontend/src/daw/ui/LimbBarEditor.tsx`**
  - Jamstix Bar Editor–style UI with:
    - 4 limb lanes: `LH`, `RH`, `LF`, `RF`
    - Bar grid with `RES` (16/32/64) and `SPAN` (1/1, 1/2, 1/4, 1/8 bar)
    - Mode toggles: `FULL`, `AUTO`, `BAR`, `RECOMPOSE`
    - Stroke modes: `SINGLE`, `DOUBLE`, `BOUNCED`, `LOCKED`
    - Circular knobs for **OPEN / PRIORITY / TIMING / POWER**
  - Stores per-bar defaults and per-slot overrides:
    - `barDefaults`: `{ open, power, timing, priority }` per bar
    - `slotMeta`: keyed by `(limb, step)` within the bar
- **`web-frontend/src/daw/ui/KitLimbsPanel.tsx`**
  - Configures which kit instruments are mapped to each limb (handedness, double-kick awareness).
- **`web-frontend/src/daw/state/limbStore.ts`**
  - Zustand store for limb configuration and mappings.
- **UI helpers**
  - `DrumIcon.tsx` + `drumKinds.ts` + `drumKindFromNote.ts` for simple SVG drum icons.
  - `KnobCircle.tsx` for the Jamstix-style circular knobs.

### DTO Extensions (Frontend → Backend)

`web-frontend/src/types/drumGenerationConfig.ts` now includes limb meta:

- `BarDefaultsDTO`
  - `barIndex: number` (0-based within generated range)
  - `open: number` (0..1, 0.5 ≈ neutral)
  - `power: number` (0..1)
  - `timing: number` (0..1)
  - `priority: number` (0..1)
- `LimbIdDTO`: union of `"LH" | "RH" | "LF" | "RF"`
- `SlotMetaDTO`
  - `barIndex: number`
  - `limb: LimbIdDTO`
  - `step: number` (0..resolution-1 in that bar)
  - Optional `open`, `power`, `timing`, `priority`
- `DrumGenerationConfigDTO`
  - Extended with optional:
    - `bars?: BarDefaultsDTO[]`
    - `slots?: SlotMetaDTO[]`

`DrumCreationPanel.tsx` accepts optional `barMetaDefaults` / `barMetaSlots` props and forwards them into the `DrumGenerationConfigDTO` sent to `/api/generate-drums`.

### Backend Config: DrumGenerationConfig (v2)

`backend/drum_generation/drum_generation_config.py` now defines:

- `BarDefaults`
  - `barIndex: int`
  - `open: float = 0.5`
  - `power: float = 0.5`
  - `timing: float = 0.5`
  - `priority: float = 0.5`
- `SlotMeta`
  - `barIndex: int`
  - `limb: Literal["LH", "RH", "LF", "RF"]`
  - `step: int`
  - Optional `open`, `power`, `timing`, `priority`
- `DrumGenerationConfig`
  - Extended with:
    - `bars: Optional[List[BarDefaults]] = None`
    - `slots: Optional[List[SlotMeta]] = None`
  - `to_dict` / `from_dict` serialize/deserialize these fields for API calls and caching.

### API Bridge: Legacy Config → v2 Config

`drum_generation_api.py` contains a legacy `DrumGenerationConfig` wrapper that converts the frontend JSON into the v2 `NewConfig`:

- Reads limb meta from request JSON:
  - `self.bars = data.get('bars')`
  - `self.slots = data.get('slots')`
- Passes them to v2 config:
  - `NewConfig(..., bars=self.bars, slots=self.slots)`
- These ultimately land in `backend/drum_generation/drum_generation_config.py` as `config.bars` / `config.slots`.

### Jamstix Enrichment: Applying global × bar × slot

`backend/drum_generation/jamstix_attributes.py` now applies limb meta when enriching internal events:

- New helper `_bias(x)` maps 0..1 → ~0.5..1.5 multipliers.
- `enrich_internal_events_with_jamstix_attrs` accepts `drum_config` (v2 `DrumGenerationConfig`).
- Builds:
  - `bars_by_idx[barIndex]` from `config.bars`
  - `slots_by_key[(barIndex, step, limb)]` from `config.slots`
- For each internal event:
  - Computes `bar_pos_frac` from `barStartTime` / `barEndTime` and `time_sec`.
  - Assigns `limbId` (LH/RH/LF/RF) based on `instrument_id`.
  - Approximates a 16-step `step_idx` from `bar_pos_frac`.
  - Looks up bar + slot meta for `(barIndex, step_idx, limbId)`.
  - Computes `open_mul`, `power_mul`, `timing_mul`, `prio_mul` via `_bias` on bar × slot values.
  - Applies multipliers:
    - **POWER** → scales `velocity` (0.5×–1.5× range capped at 1..127).
    - **TIMING** → scales `timingOffsetMs`.
    - **OPEN** → scales `hatOpenLevel` for hihat/ride instruments.
    - **PRIORITY** → scales the computed `priority` of the hit.

This realizes the `final = global × bar × slot` model:
- Global controls in `DrumCreationPanel` set the baseline.
- Limb Bar Editor bar defaults modulate entire bars.
- Per-slot overrides modulate individual limb+step hits.

### Docker Workflow for Backend Edits

Backend Python files live inside the backend container’s `/app` tree. For safe edits without touching images directly, use this workflow:

1. **Open a shell in the backend container (optional)**
   ```bash
docker exec -it drumtrackai-v1116-backend /bin/bash
# Inside container:
cd /app
ls
```

2. **Copy target file(s) out to host for editing**
   ```bash
# Example: drum_generation_config
docker cp drumtrackai-v1116-backend:/app/backend/drum_generation/drum_generation_config.py \
  F:\DrumTracKAI_v1.1.17\drum_generation_config.py
```

3. **Edit locally in IDE**
   - Apply changes to the copied file on Windows.

4. **Copy edited file back into the container**
   ```bash
docker cp F:\DrumTracKAI_v1.1.17\drum_generation_config.py \
  drumtrackai-v1116-backend:/app/backend/drum_generation/drum_generation_config.py
```

5. **Restart backend container**
   ```bash
docker restart drumtrackai-v1116-backend
```

6. **Sync container file back into repo structure (optional)**
   ```bash
docker cp drumtrackai-v1116-backend:/app/backend/drum_generation/drum_generation_config.py \
  F:\DrumTracKAI_v1.1.17\backend\drum_generation\drum_generation_config.py
```

This keeps the Dockerized backend and the Git repository in sync while allowing iterative backend development from your IDE.

## 🎵 Advanced Features (v1.1.16)

### 1. YouTube LLM Learning System (NEW in v1.1.16.3)

**Dual-Track Autonomous Learning from YouTube:**

#### **Track A: Foundation Learning (Do This FIRST)**
- **Autonomous Search**: System knows 50+ techniques to search for automatically
- **No Manual Prompts**: Pre-programmed technique database
- **Progressive Difficulty**: Beginner → Intermediate → Advanced
- **Educational Content**: Lessons, tutorials, demonstrations
- **Result**: Strong general drumming expertise (Track A)

**Foundation Quick Start:**
```python
from admin.services.youtube_foundation_learning import full_foundation_curriculum

# System learns 50+ techniques autonomously (no prompts needed!)
result = full_foundation_curriculum(max_videos_per_technique=2)
# Downloads ~110 videos across all difficulty levels
```

#### **Track B: Drummer Profiles (After Foundation >70%)**
- **Drummer-Specific**: Search for individual drummers (Jeff Porcaro, John Bonham, etc.)
- **Quality Filtering**: Automatic audio quality assessment
- **Signature Capture**: Extract unique timing, velocity, and pattern signatures
- **Result**: Accurate drummer-specific profiles (Track B)

**Profile Quick Start:**
```python
from admin.services.youtube_llm_learning_service import quick_learn_from_youtube

# After foundation is strong, learn specific drummers
result = quick_learn_from_youtube("Jeff Porcaro", "rock", 5)
```

**Key Innovation:**
- ✅ **Foundation FIRST**: Build Track A (general) before Track B (profiles)
- ✅ **Fully Autonomous**: System searches for techniques automatically
- ✅ **Better Profiles**: Drummer signatures more accurate with strong foundation

**Use Cases:**
- **Track A**: General drumming competence across all styles
- **Track B**: Sound exactly like specific legendary drummers
- **Combined**: World-class drum AI with versatility + signature accuracy

See `FOUNDATION_FIRST_LEARNING_STRATEGY.md` and `YOUTUBE_LLM_LEARNING_SYSTEM.md` for complete documentation.

---

### 2. Section Playback System (NEW in v1.1.16.2)

**Individual Section Playback** for musical arrangement analysis:
- **Play/Pause Control**: Each section has its own play button
- **Loop Mode**: Continuous repeat for practice and analysis
- **Section Labels**: Auto-detection of intro/verse/chorus/bridge/outro
- **Progress Tracking**: Real-time progress bars per section
- **Instant Switching**: Jump between sections without stopping
- **Time Display**: Precise timing and duration for each section

**Use Cases:**
- **Musicians**: Practice challenging sections with loop mode
- **Producers**: Analyze song structure and arrangements
- **Drummers**: Study drum patterns section by section
- **Teachers**: Focus on specific musical elements

**Quick Start:**
```bash
# Navigate to Section Player in the web interface
http://localhost:3000?page=section-player

# Or see SECTION_PLAYBACK_QUICKSTART.md
```

See `SECTION_PLAYBACK_SYSTEM.md` for complete documentation.

---

### 2. DAW Plugin Integration (NEW in v1.1.16)

**Professional VST3/AU Plugin** for all major DAWs:
- **Real-time Audio Capture**: 30-second ring buffer for instant analysis
- **MIDI Capture**: Record MIDI patterns for AI enhancement
- **Guide Track Feature**: Specify instrument type for context-aware generation
- **Drag & Drop**: Export generated MIDI directly to DAW timeline
- **Auto-playback**: Drums sync with DAW transport

**Guide Track Instruments:**
- `Song Mix` - Full arrangement analysis
- `Bass` - Lock kicks to bass notes, match groove
- `Guitar` - Accent on chord changes, strum alignment
- `Keys` - Follow harmonic rhythm
- `Vocal` - Complement vocal phrasing
- `Other` - General instrument guide

**Supported DAWs:**
- ✅ Reaper, Ableton Live, FL Studio
- ✅ Cubase, Studio One, Bitwig
- ✅ Logic Pro (macOS), Pro Tools

**Usage:**
```
1. Load "DrumTracKAI Connector" plugin on track
2. Enable "Use this track as guide"
3. Select instrument type (e.g., "Bass")
4. Play audio or record MIDI
5. Click "Analyze Last Audio"
6. Receive AI-generated drums optimized for that instrument
```

**Backend Integration:**
The plugin communicates via HTTP POST with extended JSON:
```json
{
  "mode": "audio",
  "guide_enabled": true,
  "guide_instrument": "bass",
  "bpm": 120.0,
  "audio_wav_base64": "..."
}
```

See `GUIDE_TRACK_IMPLEMENTATION.md` for complete documentation.

### 2. Groove Presets System

**Swing Presets:**
- `off` - No swing (50% timing)
- `light` - Light swing (~55% timing) 
- `heavy` - Heavy swing (~62.5% timing)

**Velocity Profiles:**
- `flat` - Uniform velocity across all lanes
- `accent24` - Emphasizes beats 2 & 4 (snare accents)
- `funk16` - 16th note hi-hat pattern with accents

**Usage:**
```typescript
// Frontend API call
const result = await dcsmGenerate(120, {
  start: 0, end: 16, // 4 bars at 120 BPM
  style: "funk",
  label: "chorus", 
  swing_preset: "light",
  vel_preset: "funk16",
  fill_preset: "snarebuzz"
});
```

### 2. Multi-bar Fill Library

**Fill Types:**
- `none` - No fills
- `random` - Style-appropriate automatic selection
- `tomrun` - Classic tom-tom runs
- `snarebuzz` - Snare buzz rolls
- `edmriser` - EDM-style risers with crash

**Style Awareness:**
- EDM → Prefers risers and crashes
- Funk/Jazz → Prefers snare buzzes
- Rock/Pop → Prefers tom runs

### 3. Smart Sectionization

Analyzes audio using spectral flux and cosine similarity to detect:
- **Repetition patterns** for verse/chorus identification
- **Energy changes** for intro/bridge/outro detection
- **Downbeat alignment** for musically coherent sections

**API:**
```bash
curl "http://localhost:8000/dcsm/sectionize?key=uploads/song.wav&bpm=120&mode=smart&min_bars=4&max_bars=16"
```

### 4. Type-1 Multi-track MIDI

Exports separate MIDI tracks for each drum lane:
- Track 0: Tempo information
- Track 1: Kick drum (MIDI note 36)
- Track 2: Snare drum (MIDI note 38)
- Track 3: Hi-hat closed (MIDI note 42)
- Track 4: Hi-hat open (MIDI note 46)
- Track 5: Tom (MIDI note 45)
- Track 6: Ride cymbal (MIDI note 51)
- Track 7: Crash cymbal (MIDI note 49)

### 5. Performance Benchmarking

**Available Benchmarks:**
- `/bench/peaks` - Waveform peak extraction
- `/bench/analysis` - Tempo/onset detection
- `/bench/generate` - Pattern generation

**Expected Performance:**
- Rust implementation: 5-7x faster than Python
- Memory efficiency: Zero-copy audio processing
- Robustness: Better onset/tempo detection algorithms

## 🔧 Technical Architecture

### Rust Audio-Core
- **Decoder:** Symphonia (MP3, WAV, FLAC, AAC support)
- **DSP:** Spectral flux + autocorrelation for analysis
- **Generator:** Deterministic pattern generation with style presets
- **MIDI:** Type-1 multi-track export with Base64 encoding

### Python Backend
- **Framework:** aiohttp with CORS support
- **Integration:** Rust CLI subprocess calls with PyO3 fallback
- **Analysis:** librosa/soundfile fallback for compatibility
- **Session:** File-based persistence (JSON)

### React Frontend
- **Audio Engine:** Tone.js with professional mixer
- **Components:** Piano Roll (1/64 grid), Mixer with VU meters
- **UI:** Tailwind CSS with dark theme
- **State:** React hooks with session management

## 📊 API Reference

### Core Endpoints
```
GET  /healthz                    - Health check
POST /files/upload               - Upload audio files
GET  /files/waveform             - Get waveform data
GET  /files/audio                - Stream audio files
```

### Analysis Endpoints
```
GET  /analyze/onsets             - Onset detection
GET  /analyze/tempo              - Tempo analysis
POST /align/sections             - Align sections to beats
```

### DCSM Endpoints
```
GET  /dcsm/sectionize            - Smart sectionization
POST /dcsm/generate              - Generate drum patterns
```

### Plugin Endpoints (NEW)
```
POST /api/generate               - Plugin drum generation
  Request body:
  {
    "mode": "audio" | "midi",
    "bpm": 120.0,
    "time_sig": "4/4",
    "style_id": "default",
    "guide_enabled": true,
    "guide_instrument": "bass" | "guitar" | "keys" | "vocal" | "mix" | "other",
    "audio_wav_base64": "..." (if mode == "audio"),
    "midi_smf_base64": "..." (if mode == "midi")
  }
  
  Response:
  {
    "ok": true,
    "status_message": "success",
    "midi_smf_base64": "..."
  }
```

### Session Management
```
POST /session/{sid}              - Save session
GET  /session/{sid}              - Load session
```

### Benchmarking
```
GET  /bench/peaks                - Peak extraction benchmark
GET  /bench/analysis             - Analysis benchmark  
GET  /bench/generate             - Generation benchmark
```

## 🧪 Testing

Run the complete workflow test:
```bash
python test_v1116_workflow.py
```

This tests:
- ✅ Smart sectionization with repetition labeling
- ✅ Groove presets and fill library generation
- ✅ Type-1 MIDI export validation
- ✅ Performance benchmarking suite

## 🔄 Workflow Example

1. **Upload Audio:** Upload drum track via frontend
2. **Smart Sectionize:** Auto-detect verse/chorus sections
3. **Configure Sections:** Set style, swing, velocity per section
4. **Generate Patterns:** Create drum patterns with fills
5. **Export MIDI:** Download Type-1 multi-track MIDI
6. **Benchmark:** Compare Rust vs Python performance

## 🚀 Performance Optimizations

### Rust Optimizations
- **Rayon:** Parallel processing for large files
- **Zero-copy:** Direct memory access for audio data
- **SIMD:** Vectorized operations where possible
- **Memory pools:** Reduced allocation overhead

### PyO3 Integration (Optional)
```bash
# Build Python extension
pip install maturin
cd audio-core && maturin develop --features python

# Enable in-process calls
set AUDIO_CORE_MODE=pyo3
```

## 📈 Benchmarking Results

Typical performance improvements with Rust:
- **Peak extraction:** 5-7x faster
- **Tempo analysis:** 6-8x faster  
- **Pattern generation:** 10-15x faster
- **Memory usage:** 50-70% reduction

## 🔧 Configuration

### Environment Variables
```bash
USE_RUST=1                       # Enable Rust integration
AUDIO_CORE_BIN=path/to/binary    # Rust binary path
AUDIO_CORE_MODE=auto             # auto|cli|pyo3
HOST=0.0.0.0                     # Server host
API_PORT=8000                    # Server port
```

### Frontend Configuration
```bash
REACT_APP_API_BASE=http://localhost:8000
```

## 🎯 Future Enhancements

- **GPU Acceleration:** CUDA/OpenCL for DSP operations
- **WASM Build:** Browser-native Rust execution
- **Advanced Fills:** Machine learning-generated patterns
- **Multi-user Sessions:** Database-backed persistence
- **Real-time Collaboration:** WebSocket-based sync

## 📝 Version History

### v1.1.16.3 (Current) - YouTube LLM Learning System
- ✅ **NEW:** Complete YouTube-to-LLM learning pipeline
- ✅ **NEW:** Intelligent drummer sourcing from YouTube
- ✅ **NEW:** Automatic audio quality filtering
- ✅ **NEW:** Advanced feature extraction for LLM training
- ✅ **NEW:** Automated dataset building from YouTube performances
- ✅ **NEW:** Admin UI integration with progress tracking
- ✅ **NEW:** Batch processing for multiple drummers
- ✅ Integrates existing YouTube downloader and LLM training

### v1.1.16.2 - Section Playback System
- ✅ **NEW:** Individual section playback with play/pause buttons
- ✅ **NEW:** Loop mode for continuous section repeat
- ✅ **NEW:** Real-time progress tracking per section
- ✅ **NEW:** Automatic section labeling (intro/verse/chorus/bridge/outro)
- ✅ **NEW:** Web Audio API integration for precise playback
- ✅ **NEW:** Section switching without stopping
- ✅ Comprehensive documentation and examples
- ✅ Mobile-responsive UI

### v1.1.16.1 - DAW Plugin Integration
- ✅ **NEW:** Complete VST3/AU plugin for all major DAWs
- ✅ **NEW:** Guide Track feature with instrument-aware generation
- ✅ **NEW:** Real-time audio/MIDI capture in plugin
- ✅ **NEW:** Drag & drop MIDI export to DAW timeline
- ✅ **NEW:** Extended backend API for plugin communication
- ✅ Professional UI with guide instrument selector
- ✅ Persistent state management
- ✅ Complete documentation and build scripts

### v1.1.16 - Advanced Composition Features
- Advanced groove presets (swing, velocity profiles)
- Multi-bar fill library with style awareness
- Performance benchmarking suite
- Type-1 multi-track MIDI export

### v1.1.15 - Smart Analysis
- Smart sectionization with repetition detection
- PyO3 integration for in-process Rust calls
- Downbeat-aware section alignment

### v1.1.11 - Enhanced DCSM
- Enhanced mixer with VU meters
- Advanced piano roll (1/64 grid)
- Rust audio-core integration
- Professional web interface

### v1.1.7 - Foundation
- Initial Rust integration
- Basic DCSM features
- Core API endpoints

---

## 🎯 Key Documentation

- **Current State:** `CURRENT_STATE.md` - System overview and quick reference
- **Section Playback:** `SECTION_PLAYBACK_SYSTEM.md` - Complete playback system docs
- **Section Quick Start:** `SECTION_PLAYBACK_QUICKSTART.md` - 5-minute setup guide
- **Plugin Guide:** `DrumTracKAIConnector/README.md`
- **Guide Track Feature:** `GUIDE_TRACK_IMPLEMENTATION.md`
- **Integration Guide:** `COMPLETE_PLUGIN_INTEGRATION_GUIDE.md`
- **Getting Started:** `README_START_HERE.md`
- **Cleanup Report:** `CLEANUP_COMPLETE.md` - Codebase organization details

---

## 📦 **Codebase Status**

**Clean & Production Ready** (Updated: November 20, 2025)
- ✅ **36 active files** in organized structure
- ✅ **280+ legacy files** safely archived in `_ARCHIVE_PRE_CLEANUP/`
- ✅ **2 complete backups** available
- ✅ All components tested and functional

**Archive Categories:**
- `documentation/` - 129 legacy .md files
- `scripts/` - 54 deprecated scripts  
- `test_files/` - 27 test scripts/outputs
- `training/` - 15 training scripts
- `temp_files/` - 31 utility files
- `legacy_backend/` - Old backend components
- `old_frontends/` - Old UI files

All archived files can be restored from `_ARCHIVE_PRE_CLEANUP/` if needed.

---

**DrumTracKAI v1.1.16.1** - The ultimate drum composition and analysis platform with professional-grade DAW integration, AI-powered generation, and industry-leading performance.
