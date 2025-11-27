# 🥁 Complete Drum Builder Architecture

**Three-Layer System with LLM Integration**

Version: 2.0.0  
Date: November 21, 2025  
Status: 🟢 **SPECIFICATION COMPLETE - READY FOR IMPLEMENTATION**

---

## 📋 **Executive Summary**

Complete redesign of the drumtrack building module around three distinct layers:

1. **Pattern Layer** - What notes happen (grid-based, musical)
2. **Performance Layer** - How notes are played (micro-timing, velocities, articulations)
3. **Rendering Layer** - MIDI output for DCSM piano roll (high-resolution, metadata-rich)

**Key Innovation:** Performance layer driven by LLM + analytics, not hardcoded humanization.

---

## 🏗️ **Three-Layer Architecture**

### **Layer 1: Pattern Layer ("What")**

**Responsibility:** Determine which drum hits occur at which grid positions.

**Input:**
- SongMap (sections, bars, energy, tempo)
- Style models (GrooVAE, clip database, templates)
- LLM pattern suggestions
- User controls (style, drummer, intensity, variation)

**Output:**
```python
GridEvent = {
    "bar_index": int,
    "subdivision_index": int,
    "subdivisions_per_bar": int,
    "instrument_id": str,  # "kick", "snare_center", "hihat_closed", etc.
    "is_ghost": bool,
    "is_accent": bool
}
```

**Clean grid - NO micro-timing at this layer.**

---

### **Layer 2: Performance Layer ("How")**

**Responsibility:** Define HOW each note is performed - the human feel.

**Input:**
- Pattern layer grid events
- Drummer profile (timing characteristics, ghost note preferences)
- SongMap analytics (section energy, genre)
- **LLM-generated DrumPerformanceSpec**
- User controls (humanize amount, ghost density, swing)

**Output:**
```json
{
  "styleId": "rock_tight",
  "globalFeel": "laid_back",
  "quantizationBase": "16th",
  "phrases": [
    {
      "phraseId": "verse_1",
      "barStart": 0,
      "barEnd": 7,
      "profiles": [
        {
          "instrumentId": "snare_center",
          "microTiming": {
            "subdivisionOffsetsMs": [-5, 2, -3, 4],
            "swingAmount": 0.2,
            "laidBackAmount": 0.4
          },
          "velocityProfile": {
            "base": 95,
            "accentBoost": 15,
            "ghostReduction": 0.4,
            "randomRange": 7,
            "phraseShape": "swell"
          },
          "ghostDensity": 0.7,
          "flamProbability": 0.2,
          "dragProbability": 0.1
        }
      ]
    }
  ]
}
```

---

### **Layer 3: Rendering Layer ("MIDI")**

**Responsibility:** Convert pattern + performance into high-resolution MIDI for piano roll.

**Input:**
- Grid events from Pattern Layer
- DrumPerformanceSpec from Performance Layer
- SongMap for tempo/timing calculations

**Output:**
```typescript
interface DrumNoteEvent {
  id: string;
  barIndex: number;
  tickInBar: number;
  tickLength: number;
  channel: number;
  midiPitch: number;
  velocity: number;
  instrumentId: DrumInstrumentId;
  isGhost?: boolean;
  isAccent?: boolean;
  isFlam?: boolean;
  isDrag?: boolean;
  performanceGroupId?: string;
  microTimingMs?: number;
}

interface DrumTrackForDCSM {
  track_id: string;
  style_id: string;
  resolution_ppq: number;  // 960 or 1920
  notes: DrumNoteEvent[];
  performance_spec: DrumPerformanceSpec;
}
```

---

## 🎛️ **Complete User Controls**

### **Existing Controls (All Integrated)**

| Control | Type | Range | Purpose |
|---------|------|-------|---------|
| **Style** | Dropdown | Rock, Funk, Jazz, etc. | Musical genre |
| **Drummer** | Dropdown | Jeff Porcaro, John Bonham, etc. | Drummer profile |
| **Intensity** | Slider | 0.0 - 1.0 | Loudness/energy |
| **Variation** | Slider | 0.0 - 1.0 | Pattern changes |
| **Generation Mode** | Dropdown | Template / AI Variation / Full AI | Pattern source |
| **Humanize** | Toggle | On/Off | Enable performance layer |
| **Fill Type** | Dropdown | Auto, Tom Run, Crash Buildup, etc. | Fill style |
| **Fill Locations** | Array | Measure indices | Where fills occur |
| **Measure Range** | Range | Start-End bars | Section to generate |

### **New Controls (Performance Layer)**

| Control | Type | Range | Purpose |
|---------|------|-------|---------|
| **Humanize Amount** | Slider | 0.0 (tight) - 1.0 (loose) | Micro-timing variance |
| **Ghost Note Amount** | Slider | 0.0 (none) - 1.0 (dense) | Ghost note density |
| **Swing Amount** | Slider | 0.0 (straight) - 1.0 (swing) | Swing/shuffle feel |
| **Build Scope** | Radio | Full Song / Selected Section | Generation scope |

### **Guide Track Controls (Optional)**

| Control | Type | Options | Purpose |
|---------|------|---------|---------|
| **Guide Enabled** | Toggle | On/Off | Use guide track |
| **Guide Instrument** | Dropdown | Mix, Bass, Guitar, Keys, Vocal | Which instrument to follow |

---

## 🤖 **LLM Integration**

### **LLM Prompt Structure**

**Input to LLM:**
```python
{
  "section": {
    "label": "Verse 1",
    "measures": "4-11",
    "tempo": "98.5 BPM",
    "time_signature": "4/4"
  },
  "style": "rock",
  "drummer": "jeff_porcaro",
  "controls": {
    "intensity": 0.7,
    "variation": 0.5,
    "humanize_amount": 0.7,
    "ghost_note_amount": 0.7,
    "swing_amount": 0.2
  },
  "songmap_summary": {...},
  "drummer_profile": {...}
}
```

**Output from LLM:**
```json
DrumPerformanceSpec (as shown in Layer 2)
```

### **LLM Responsibility**

**LLM designs:**
- Per-instrument micro-timing profiles
- Velocity curves and dynamics
- Ghost note placement strategy
- Flam/drag probabilities
- Phrase-specific feel changes

**LLM does NOT:**
- Generate raw MIDI notes (Pattern Layer does this)
- Replace analytical data (uses it as context)
- Ignore user controls (respects all sliders)

---

## 🎯 **User Workflow**

### **Workflow 1: Full Song Generation**

```
1. User clicks "Full Song" scope
2. Sets style, drummer, intensity, variation
3. Enables humanize, sets feel controls
4. Clicks "Generate"
   ↓
5. Backend:
   - Pattern Layer: Generate grid for entire song
   - LLM: Create DrumPerformanceSpec for all sections
   - Performance Layer: Apply spec to grid
   - Rendering Layer: Convert to high-res MIDI
   ↓
6. Frontend: Display in piano roll with all metadata
```

### **Workflow 2: Section-by-Section Refinement**

```
1. User generates full song first
2. Locks sections they like (Intro, Chorus 1)
3. Selects "Verse 1" section
4. Changes to "Selected Section" scope
5. Tweaks feel controls for just this verse
6. Clicks "Generate"
   ↓
7. Backend: Only regenerates Verse 1
8. Frontend: Merges new Verse 1, keeps locked sections intact
```

### **Workflow 3: Live Re-Humanization**

```
1. User has generated drum track
2. Adjusts "Humanize Amount" slider
3. Frontend: Applies local re-humanization
   - Scales microTimingMs values
   - Adjusts velocities
   - No backend call needed
4. User sees changes instantly in piano roll
```

---

## 📊 **Data Flow Diagram**

```
┌─────────────────────────────────────────────────────────────┐
│                      USER CONTROLS                           │
│  Style, Drummer, Intensity, Variation, Humanize, etc.       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND PIPELINE                           │
└─────────────────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ↓            ↓             ↓
  ┌─────────┐  ┌─────────┐  ┌──────────┐
  │ SongMap │  │ Drummer │  │  User    │
  │Analysis │  │ Profile │  │ Controls │
  └────┬────┘  └────┬────┘  └────┬─────┘
       │            │             │
       └────────────┼─────────────┘
                    ↓
         ┌──────────────────────┐
         │   PATTERN LAYER      │
         │ (Grid generation)    │
         └──────────┬───────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │   LLM CALL           │
         │ (Performance Spec)   │
         └──────────┬───────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │  PERFORMANCE LAYER   │
         │ (Apply micro-timing) │
         └──────────┬───────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │  RENDERING LAYER     │
         │ (High-res MIDI)      │
         └──────────┬───────────┘
                    │
                    ↓
         ┌──────────────────────┐
         │  DrumTrackForDCSM    │
         │  + SMF Base64        │
         └──────────┬───────────┘
                    │
                    ↓
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND (DCSM Piano Roll)                      │
│  - High-resolution display                                   │
│  - Per-instrument lanes                                      │
│  - Ghost/accent/flam visual indicators                       │
│  - Section locking                                           │
│  - Local re-humanization                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎨 **Frontend Components**

### **Component 1: SectionTimelineStrip**

**Purpose:** Visual section navigation with locking

**Features:**
- Shows all sections (Intro, Verse 1, Chorus 1, etc.)
- Click to select section
- Lock icon to protect sections from regeneration
- Color-coded by section type

### **Component 2: DrumGenerationToolbar**

**Purpose:** Generation controls and scope selection

**Features:**
- Build Scope selector (Full Song / Selected Section)
- Section lock toggle
- Human feel snapshot display
- Generate button
- Re-Humanize button

### **Component 3: DrumBuilderPanel**

**Purpose:** Detailed control panel

**Features:**
- All existing controls (style, drummer, etc.)
- New feel controls (humanize amount, ghosts, swing)
- Guide track controls
- Fill configuration

### **Component 4: Enhanced Piano Roll**

**Purpose:** High-resolution drum note display and editing

**Features:**
- Per-instrument lanes
- Ghost note visualization (lighter color)
- Accent note visualization (brighter color)
- Flam/drag indicators
- Micro-timing display (optional)
- Manual note editing
- Locked section highlighting

---

## 📁 **File Structure**

### **Backend**

```
backend/
├── drum_generation/
│   ├── drum_generation_config.py          # Config dataclass
│   ├── drum_generation_api.py             # Main orchestrator
│   ├── pattern_layer.py                   # Grid generation
│   ├── performance_layer.py               # LLM integration
│   ├── rendering_layer.py                 # MIDI conversion
│   └── llm_performance_spec.py            # LLM prompts
│
├── dcsmpiano/
│   ├── drumtrack_schema.py                # DrumTrackForDCSM types
│   └── drumtrack_builder_dcsmpiano.py     # Main builder
│
└── api/
    └── generate_drums.py                  # FastAPI endpoint
```

### **Frontend**

```
frontend/src/
├── types/
│   ├── drumGenerationConfig.ts            # Config types
│   └── drumTrack.ts                       # DrumTrackForDCSM types
│
├── components/drums/
│   ├── DrumBuilderPanel.tsx               # Control panel
│   ├── DrumGenerationToolbar.tsx          # Toolbar
│   ├── SectionTimelineStrip.tsx           # Section nav
│   └── DrumTrackPane.tsx                  # Main container
│
├── utils/
│   ├── reHumanize.ts                      # Client-side re-humanization
│   └── mergeDrumTrack.ts                  # Section merging
│
└── api/
    └── drums.ts                           # API calls
```

---

## ✅ **Implementation Checklist**

### **Phase 1: Backend Foundation**

- [ ] Create `drum_generation_config.py` with all controls
- [ ] Update `pattern_layer.py` to output `GridEvent[]`
- [ ] Create `DrumPerformanceSpec` schema
- [ ] Implement LLM prompt builder
- [ ] Implement LLM call wrapper
- [ ] Create `performance_layer.py` (apply spec to grid)
- [ ] Update `rendering_layer.py` for high-res MIDI
- [ ] Create `DrumTrackForDCSM` output format
- [ ] Update `/api/generate-drums` endpoint
- [ ] Add section scope handling (full/selected)

### **Phase 2: Frontend Foundation**

- [ ] Create TypeScript types (`drumGenerationConfig.ts`, `drumTrack.ts`)
- [ ] Update `DrumBuilderPanel` with new controls
- [ ] Add "Build Scope" radio buttons
- [ ] Add humanize/ghost/swing sliders
- [ ] Create section lock state management
- [ ] Implement `mergeDrumTrack()` utility
- [ ] Update piano roll to consume `DrumTrackForDCSM`

### **Phase 3: UI Components**

- [ ] Create `SectionTimelineStrip.tsx`
- [ ] Create `DrumGenerationToolbar.tsx`
- [ ] Create `DrumTrackPane.tsx` (integrates all components)
- [ ] Add visual indicators for ghosts/accents/flams
- [ ] Add locked section highlighting
- [ ] Wire up section selection

### **Phase 4: Client-Side Re-Humanization**

- [ ] Implement `reHumanizeTrackLocally()`
- [ ] Implement `reHumanizeTrackByInstrument()`
- [ ] Add re-humanize controls to UI
- [ ] Add real-time preview

### **Phase 5: Testing & Polish**

- [ ] Test full song generation
- [ ] Test section-by-section generation
- [ ] Test section locking
- [ ] Test LLM integration
- [ ] Test re-humanization
- [ ] Add loading states
- [ ] Add error handling
- [ ] Add user documentation

---

## 🎯 **Success Criteria**

1. ✅ **Separation of Concerns:** Pattern, Performance, and Rendering layers are distinct
2. ✅ **LLM Integration:** LLM controls performance, not patterns
3. ✅ **User Control:** All existing + new controls work seamlessly
4. ✅ **Scope Control:** Users can generate full song or sections independently
5. ✅ **Section Locking:** Protected sections don't get overwritten
6. ✅ **High Resolution:** MIDI output is 960+ PPQ with micro-timing
7. ✅ **User Friendly:** Complex system, simple interface
8. ✅ **Real-Time Tweaks:** Client-side re-humanization without backend calls

---

## 📚 **API Contracts**

### **Backend Endpoint**

```
POST /api/generate-drums

Request:
{
  "sectionId": "verse_1",
  "startMeasure": 4,
  "endMeasure": 11,
  "style": "rock",
  "drummer": "jeff_porcaro",
  "intensity": 0.7,
  "variation": 0.5,
  "generationMode": "full_ai",
  "humanize": true,
  "humanizeAmount": 0.7,
  "ghostNoteAmount": 0.7,
  "swingAmount": 0.2,
  "buildScope": "selected_section",
  ...
}

Response:
{
  "ok": true,
  "midi_smf_base64": "...",
  "drum_track": {
    "track_id": "uuid",
    "style_id": "rock",
    "resolution_ppq": 960,
    "notes": [ DrumNoteEvent[] ],
    "performance_spec": { DrumPerformanceSpec }
  }
}
```

---

## 🎓 **Summary**

This architecture provides:

- **Clean Separation:** Pattern (what) vs Performance (how) vs Rendering (MIDI)
- **LLM Power:** Deep performance control without overwhelming users
- **User Flexibility:** Full song OR section-by-section workflow
- **Real-Time Tweaks:** Client-side re-humanization for instant feedback
- **Professional Output:** High-resolution MIDI with rich metadata
- **Future-Proof:** Easy to extend with new performance profiles, styles, etc.

**Next Steps:** Begin implementation with Phase 1 (Backend Foundation)

---

**🥁 Complete Drum Builder Architecture v2.0.0**  
**Built:** November 21, 2025  
**For:** DrumTracKAI v1.1.16.3  
**Status:** 🟢 **SPECIFICATION COMPLETE**
