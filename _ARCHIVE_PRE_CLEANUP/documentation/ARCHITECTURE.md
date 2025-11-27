# 🏗️ DrumTracKAI System Architecture

**Technical Deep Dive into System Design**

---

## 📐 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER APPLICATION                           │
├──────────────────────────────────────────────────────────────────┤
│  Frontend (React TypeScript)                                     │
│  ├─ Audio Upload & Waveform Visualization                        │
│  ├─ Tempo & Section Detection UI                                 │
│  ├─ Drummer Selector Component (10 fictional drummers)           │
│  ├─ Piano Roll Editor (8 drum lanes)                             │
│  ├─ Professional Mixer & Transport                               │
│  └─ Session Management                                           │
├──────────────────────────────────────────────────────────────────┤
│  Backend (Python aiohttp)                                        │
│  ├─ Audio Analysis Endpoints                                     │
│  ├─ Drummer Mapping Service ⭐ (Bridge Layer)                    │
│  ├─ Pattern Generation API                                       │
│  ├─ File Upload & Management                                     │
│  └─ Rust Audio-Core Integration                                  │
├──────────────────────────────────────────────────────────────────┤
│  Audio Engine (Rust)                                             │
│  ├─ Symphonia Decoder (MP3/WAV/FLAC/AAC)                         │
│  ├─ DSP Algorithms (Tempo, Onset, Spectral)                      │
│  ├─ Smart Sectionization Engine                                  │
│  ├─ Pattern Generator (6 styles, presets)                        │
│  └─ MIDI Export (Type-1 multi-track)                             │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│                   DRUMMER MAPPING LAYER ⭐                        │
│  drummer_mapping_service.py                                      │
│  ├─ DRUMTRACKAI_DRUMMERS (10 fictional profiles)                 │
│  ├─ Source Drummer Mapping (fictional → real)                    │
│  ├─ Characteristic Loading from Admin DB                         │
│  ├─ Blending Engine (multiple sources)                           │
│  └─ Parameter Translation (DB → Rust)                            │
└──────────────────────────────────────────────────────────────────┘
                              ↕
┌──────────────────────────────────────────────────────────────────┐
│                      ADMIN APPLICATION                            │
├──────────────────────────────────────────────────────────────────┤
│  Drummer Analysis Engine                                         │
│  ├─ Drum Stem Separation (MVSEP API)                             │
│  ├─ Advanced Nuance Extraction                                   │
│  ├─ Style Vector Quantification                                  │
│  ├─ Pattern Complexity Analysis                                  │
│  └─ Comparative Analysis Tools                                   │
├──────────────────────────────────────────────────────────────────┤
│  Database (SQLite - drumtrackai.db)                              │
│  ├─ drummer_style_vectors (50+ characteristics)                  │
│  ├─ drum_characteristics (per-component)                         │
│  ├─ pattern_complexity_definitions                               │
│  ├─ style_comparisons                                            │
│  └─ metadata                                                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### **Complete Workflow: Upload → Analysis → Generation**

```
1. USER UPLOADS AUDIO FILE
   ↓
2. FRONTEND: POST /api/upload
   └─> Backend receives file
       └─> Saves to uploads/ directory
       └─> Generates waveform peaks
       └─> Returns file_key + waveform data

3. FRONTEND: POST /api/analyze
   └─> Backend analyzes audio
       └─> Rust audio-core: ac_analyze
           ├─> Decode audio (Symphonia)
           ├─> Detect tempo (autocorrelation + onset strength)
           ├─> Find beats (dynamic programming)
           └─> Detect onsets (spectral flux)
       └─> Returns: tempo, beats[], onsets[]

4. FRONTEND: GET /dcsm/sectionize
   └─> Backend sectionizes audio
       └─> Rust audio-core: ac_sectionize_smart
           ├─> Compute chroma features
           ├─> Build recurrence matrix
           ├─> Find repetition boundaries
           ├─> Label sections (intro/verse/chorus/bridge/outro)
           └─> Snap to beats
       └─> Returns: sections[] with labels

5. USER SELECTS DRUMMER
   ↓
6. FRONTEND: GET /api/drummers
   └─> Backend: drummer_mapping_service.list_drummers()
       └─> Returns: 10 fictional drummers with display info

7. FRONTEND: GET /api/drummers/{drummer_id}
   └─> Backend: drummer_mapping_service.get_drummer_characteristics()
       └─> Loads from admin/drumtrackai.db
       └─> Fallback to default if not found
       └─> Returns: full characteristics + display info

8. USER CLICKS "GENERATE"
   ↓
9. FRONTEND: POST /api/generate_with_drummer
   └─> Backend receives:
       {
         "drummer_id": "studio_groove_master",
         "bpm": 161,
         "sections": [{"start": 0, "end": 10, ...}],
         "song_analysis": {}
       }
   └─> drummer_mapping_service.get_generation_parameters()
       ├─> Load drummer characteristics
       ├─> Map to Rust style enum
       ├─> Select swing/vel/fill presets
       ├─> Calculate density & humanize
       └─> Combine with song_analysis if provided
   └─> For each section:
       └─> Rust audio-core: generate
           ├─> Select style function (gen_rock, gen_jazz, etc.)
           ├─> Generate base pattern
           ├─> Apply swing preset
           ├─> Apply velocity profile
           ├─> Apply label-specific fills
           ├─> Apply humanization
           └─> Return notes[]
   └─> Returns: {notes[], drummer_id, params_used}

10. FRONTEND DISPLAYS NOTES
    └─> Piano roll visualization
    └─> Audio playback via Web Audio API
```

---

## 🎵 Drummer Mapping System (NEW!)

### **Three-Layer Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: User-Facing (Fictional Names)                     │
│  ├─ "Studio Groove Master" 🎩                               │
│  ├─ "Metal Atomic Clock" ⚡                                 │
│  ├─ "Funk Machine" 🕺                                        │
│  └─ ... 7 more fictional drummers                           │
│  Purpose: Legal protection, branding, user-friendly         │
└─────────────────────────────────────────────────────────────┘
                          ↓ Maps to ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Mapping Layer (drummer_mapping_service.py)        │
│  ├─ DRUMTRACKAI_DRUMMERS dict                               │
│  ├─ source_drummers: ["jeff_porcaro"]                       │
│  ├─ blend_weights: [1.0]                                    │
│  ├─ get_drummer_characteristics()                           │
│  ├─ map_to_rust_style()                                     │
│  ├─ get_generation_parameters()                             │
│  └─ _blend_characteristics() for multi-source               │
│  Purpose: Translation, blending, parameter generation        │
└─────────────────────────────────────────────────────────────┘
                          ↓ Loads from ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Admin Database (Real Names & Analysis)            │
│  ├─ drummer_style_vectors table                             │
│  │   ├─ drummer_id: "jeff_porcaro"                          │
│  │   ├─ characteristics_blob: pickle(dict)                  │
│  │   └─ 50+ quantified characteristics                      │
│  ├─ Analyzed from real drum tracks                          │
│  └─ Never exposed to end users                              │
│  Purpose: Real analysis, legal names, research              │
└─────────────────────────────────────────────────────────────┘
```

### **Characteristic Flow**

```python
# Example: "Studio Groove Master" generation

# 1. User selects drummer
selected = "studio_groove_master"

# 2. Load definition
definition = DRUMTRACKAI_DRUMMERS["studio_groove_master"]
# source_drummers = ["jeff_porcaro"]
# blend_weights = [1.0]

# 3. Load from admin DB
conn = sqlite3.connect("admin/drumtrackai.db")
cursor = conn.execute(
    "SELECT characteristics_blob FROM drummer_style_vectors WHERE drummer_id = ?",
    ("jeff_porcaro",)
)
blob = cursor.fetchone()[0]
characteristics = pickle.loads(blob)
# {
#   "ghost_note_density": 0.75,
#   "ride_preference": 0.70,
#   "swing_comfort": 0.85,
#   "technical_precision": 0.86,
#   ... 46 more characteristics
# }

# 4. Map to Rust parameters
genre_tags = ["Jazz Fusion", "Pop", "Rock"]
if "Jazz" in genre_tags:
    style = "jazz"
elif "Funk" in genre_tags:
    style = "funk"
# ... etc

swing_comfort = characteristics.get("swing_comfort", 0.5)
if swing_comfort > 0.75:
    swing_preset = "heavy"
elif swing_comfort > 0.50:
    swing_preset = "light"
else:
    swing_preset = "off"

params = {
    "style": "jazz",
    "swing_preset": "heavy",
    "vel_preset": "accent24",
    "fill_preset": "tomrun",
    "density": 0.75,  # from ghost_note_density
    "humanize": 0.14   # 1.0 - technical_precision
}

# 5. Send to Rust generator
rust_args = [
    "generate",
    "--bpm", "161",
    "--start", "0", "--end", "10",
    "--style", "jazz",
    "--swing-preset", "heavy",
    "--vel-preset", "accent24",
    "--fill-preset", "tomrun",
    "--density", "0.75",
    "--humanize", "0.14"
]

# 6. Rust generates with these parameters
# Result: Jazz-style drums with Jeff Porcaro characteristics!
```

---

## 🦀 Rust Audio-Core Architecture

### **Module Structure**

```rust
audio-core/
├── src/
│   ├── lib.rs              // Module exports & CLI entry point
│   ├── decoder.rs          // Symphonia audio decoding
│   ├── dsp.rs              // DSP algorithms
│   ├── generator.rs        // Pattern generation
│   ├── midi.rs             // MIDI export
│   └── sectionize_smart.rs // Smart sectionization
```

### **DSP Pipeline**

```rust
// dsp.rs - Audio Analysis

pub fn analyze_audio(path: &str) -> AnalysisResult {
    // 1. Decode audio
    let (samples, sr) = decode_audio(path)?;
    
    // 2. Compute onset strength envelope
    let onset_env = onset_strength(&samples, sr);
    
    // 3. Detect tempo via autocorrelation
    let tempo_candidates = detect_tempo_autocorr(&onset_env, sr);
    
    // 4. Refine tempo with dynamic programming
    let tempo = refine_tempo(tempo_candidates, &onset_env);
    
    // 5. Track beats using tempo
    let beats = track_beats(&onset_env, tempo, sr);
    
    // 6. Detect individual onsets
    let onsets = detect_onsets(&onset_env, sr);
    
    AnalysisResult { tempo, beats, onsets, sr, duration }
}
```

### **Pattern Generator**

```rust
// generator.rs - Drum Pattern Generation

pub struct GenParams {
    pub bpm: f32,
    pub density: f32,        // 0.0-1.0 note density
    pub swing: f32,          // 0.0-0.35 swing amount
    pub humanize: f32,       // 0.0-1.0 timing variation
    pub grid_sec: f32,       // Time per grid unit
    pub seed: u64,           // Deterministic generation
    pub style: Style,        // Rock, Funk, EDM, HipHop, Jazz, Pop
    pub label: SectionLabel, // Intro, Verse, Chorus, Bridge, Outro
    pub swing_preset: SwingPreset,   // Off, Light, Heavy
    pub vel_preset: VelPreset,       // Flat, Accent24, Funk16
    pub fill_preset: FillPreset,     // TomRun, SnareBuzz, etc.
}

pub fn generate_section(
    start: f32,
    end: f32,
    fill_in: bool,
    fill_out: bool,
    p: GenParams
) -> Vec<Note> {
    // 1. Calculate swing amount
    let swing_amt = (p.swing + p.swing_preset.amount()).clamp(0.0, 0.35);
    
    // 2. Generate base pattern for style
    let mut notes = match p.style {
        Style::Rock => gen_rock(start, end, fill_in, fill_out, p, swing_amt),
        Style::Funk => gen_funk(start, end, fill_in, fill_out, p, swing_amt),
        Style::Jazz => gen_jazz(start, end, fill_in, fill_out, p, swing_amt),
        // ... other styles
    };
    
    // 3. Apply section label fills
    apply_label_fills(start, end, p, &mut notes);
    
    // 4. Apply fill preset
    apply_fill_preset(start, end, p, &mut notes);
    
    // 5. Apply velocity profile
    apply_velocity_profile(&mut notes, p.vel_preset);
    
    // 6. Apply humanization
    humanize_notes(&mut notes, p.humanize, p.seed);
    
    notes
}
```

### **Style-Specific Generators**

```rust
// Example: Jazz style generator

fn gen_jazz(
    start: f32,
    end: f32,
    fill_in: bool,
    fill_out: bool,
    p: GenParams,
    swing: f32
) -> Vec<Note> {
    let mut notes = Vec::new();
    let beat_sec = 60.0 / p.bpm;
    let mut t = start;
    
    while t < end {
        // Kick on 1 and 3 (walking feel)
        if (t - start) % (beat_sec * 2.0) < p.grid_sec {
            notes.push(Note {
                time: t,
                lane: Lane::Kick,
                vel: 0.8 + rand_f32(&mut seed) * 0.15
            });
        }
        
        // Ride cymbal pattern (jazz ride)
        let ride_pattern = [1.0, 0.7, 0.9, 0.6]; // Ding-ding-da-ding
        let eighth = (t - start) / (beat_sec * 0.5);
        let ride_vel = ride_pattern[(eighth as usize) % 4];
        if ride_vel > 0.5 {
            notes.push(Note {
                time: apply_swing(t, swing, beat_sec),
                lane: Lane::Ride,
                vel: ride_vel * (0.5 + p.density * 0.3)
            });
        }
        
        // Snare backbeats (2 and 4)
        if ((t - start) / beat_sec) % 2.0 > 0.9 {
            notes.push(Note {
                time: t,
                lane: Lane::Snare,
                vel: 0.9
            });
        }
        
        // Ghost notes on snare (high density)
        if p.density > 0.6 && rand_f32(&mut seed) < p.density * 0.4 {
            notes.push(Note {
                time: t + rand_f32(&mut seed) * p.grid_sec,
                lane: Lane::Snare,
                vel: 0.2 + rand_f32(&mut seed) * 0.2 // Quiet ghost notes
            });
        }
        
        t += p.grid_sec;
    }
    
    notes
}
```

---

## 🎨 Frontend Architecture

### **Component Hierarchy**

```
App
├── WebDAWApp (Main container)
│   ├── Mixer (Track volume/pan controls)
│   ├── Transport Bar (Play/Pause/Stop/BPM)
│   ├── Timeline (Waveform + Sections)
│   ├── PianoRoll (MIDI editor)
│   └── Sidebar
│       ├── DrummerSelector ⭐ NEW
│       │   ├── Drummer Cards
│       │   └── Selected Badge
│       └── SectionControls
│           ├── Section List
│           ├── Tempo Controls
│           └── Generate Buttons
```

### **State Management**

```typescript
// WebDAWApp.tsx - Main state

const [tracks, setTracks] = useState<UploadedTrack[]>([]);
const [sections, setSections] = useState<Section[]>([]);
const [notes, setNotes] = useState<MidiNote[]>([]);
const [bpm, setBpm] = useState(120);
const [playhead, setPlayhead] = useState(0);
const [playing, setPlaying] = useState(false);
const [loop, setLoop] = useState({ enabled: false, start: 0, end: 4 });
const [selectedDrummer, setSelectedDrummer] = useState<Drummer | null>(null); // ⭐ NEW
```

### **API Integration**

```typescript
// services/api.ts

// Generic generation (no drummer)
export async function generateDrumPattern(payload: {
  bpm: number;
  density: number;
  sections: Section[];
}) {
  return await fetchJSON('/dcsm/generate', { method: 'POST', body: JSON.stringify(payload) });
}

// ⭐ NEW: Drummer-specific generation
export async function generateWithDrummer(payload: {
  drummer_id: string;
  bpm: number;
  sections: Section[];
  song_analysis?: object;
}) {
  return await fetchJSON('/api/generate_with_drummer', { method: 'POST', body: JSON.stringify(payload) });
}
```

---

## 🔌 Backend API Server

### **Server Setup (aiohttp)**

```python
# dcsm_backend.py

async def _amain():
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    LOG.info(f"Server running on {HOST}:{PORT}")
    await asyncio.Event().wait()

def make_app() -> web.Application:
    app = web.Application()
    
    # Add routes
    app.add_routes([
        # File operations
        web.post("/api/upload", upload),
        web.get("/files/waveform", waveform),
        web.get("/files/audio", audio_file),
        
        # Analysis
        web.post("/api/analyze", analyze_audio_real),
        web.get("/analyze/tempo", analyze_tempo),
        web.get("/analyze/onsets", analyze_onsets),
        web.post("/analyze/tempo_sections", analyze_tempo_sections),
        
        # ⭐ NEW: Drummer endpoints
        web.get("/api/drummers", list_drummers),
        web.get("/api/drummers/{drummer_id}", get_drummer_details),
        web.post("/api/generate_with_drummer", generate_with_drummer),
        
        # Generation
        web.post("/dcsm/generate", dcsm_generate),
        web.get("/dcsm/sectionize", dcsm_sectionize),
        
        # Session
        web.post("/session/{sid}", save_session),
        web.get("/session/{sid}", load_session),
    ])
    
    # CORS for development
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(allow_headers="*", allow_methods="*")
    })
    for route in app.router.routes():
        cors.add(route)
    
    return app
```

---

## 🗄️ Database Schema (Admin)

### **SQLite Schema**

```sql
-- drummer_style_vectors
CREATE TABLE drummer_style_vectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drummer_id TEXT UNIQUE NOT NULL,
    characteristics_blob BLOB NOT NULL,  -- Pickled dict with 50+ characteristics
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Example characteristics in blob:
-- {
--   "timing_precision_mean": 0.86,
--   "micro_timing_tendency": 0.02,
--   "tempo_stability": 0.63,
--   "groove_score": 0.82,
--   "ghost_note_density": 0.75,
--   "ride_preference": 0.70,
--   "kick_syncopation": 0.65,
--   ... 43 more characteristics
-- }

-- drum_characteristics
CREATE TABLE drum_characteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    drummer_id TEXT NOT NULL,
    component TEXT NOT NULL,  -- "kick", "snare", "hihat", etc.
    average_velocity REAL,
    velocity_std REAL,
    hit_rate REAL,
    pattern_complexity REAL,
    FOREIGN KEY (drummer_id) REFERENCES drummer_style_vectors(drummer_id)
);

-- metadata
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

---

## 🎯 Design Patterns

### **1. Bridge Pattern** (Drummer Mapping)
- **Problem**: Admin DB has real names; User app needs legal protection
- **Solution**: Mapping layer translates fictional → real, loads characteristics
- **Benefits**: Decoupling, flexibility, legal safety

### **2. Strategy Pattern** (Style Generators)
- **Problem**: Different drum styles need different generation algorithms
- **Solution**: `Style` enum with style-specific `gen_*()` functions
- **Benefits**: Extensible, maintainable, clear separation

### **3. Builder Pattern** (GenParams)
- **Problem**: Many parameters for pattern generation
- **Solution**: `GenParams` struct with logical grouping
- **Benefits**: Type safety, clear API, validation

### **4. Facade Pattern** (DrummerMappingService)
- **Problem**: Complex DB access + characteristic blending
- **Solution**: Service with simple methods like `get_generation_parameters()`
- **Benefits**: Simplified API, encapsulation, testability

---

## 📊 Performance Considerations

### **Rust Optimization**
- **Release builds**: `--release` flag for -C opt-level=3
- **SIMD**: Manual vectorization for DSP loops
- **Memory**: Pre-allocate vectors, avoid clones
- **Parallelism**: Rayon for multi-threaded analysis (future)

### **Python Optimization**
- **NumPy**: Vectorized operations where possible
- **Caching**: Analysis results cached in memory
- **Async I/O**: aiohttp for non-blocking file operations
- **Lazy loading**: DB connections only when needed

### **Frontend Optimization**
- **Virtual scrolling**: For long MIDI note lists
- **Canvas rendering**: Waveform/piano roll use canvas, not DOM
- **Debouncing**: User input debounced to reduce re-renders
- **Web Workers**: Audio decoding off main thread (future)

---

## 🔐 Security Considerations

### **File Upload**
- Size limits (500MB)
- Type validation (audio/* only)
- Sanitized filenames
- Isolated upload directory

### **Database**
- SQLite with WAL mode
- Prepared statements (no SQL injection)
- Read-only access from user app

### **API**
- CORS configured for development
- Rate limiting planned for production
- No authentication yet (future feature)

---

## 🧪 Testing Strategy

### **Unit Tests**
- Rust: `cargo test` for generator/DSP functions
- Python: pytest for drummer service
- Frontend: Jest for components (future)

### **Integration Tests**
- `test_drummer_connection.py` - End-to-end service test
- API tests with curl/Postman
- Manual UI testing workflow

### **Performance Tests**
- Benchmark endpoints `/bench/*`
- Compare Rust vs Python implementations
- Memory profiling with valgrind/heaptrack

---

**See Also:**
- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API reference
- [DRUMMER_INTEGRATION.md](DRUMMER_INTEGRATION.md) - Drummer system details
- [NEXT_STEPS.md](NEXT_STEPS.md) - Future architecture improvements
