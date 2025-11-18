# DrumTracKAI v1.1.16 - Next Development Workflows
**Current Status:** Audio upload working  
**Next Phase:** Connect analysis and generation features

---

## 🎯 **PHASE 1: CONNECT REAL AUDIO ANALYSIS**

### **Objective:** 
Replace stub endpoints with actual Rust audio-core analysis

### **Tasks:**

#### **1.1 Tempo Detection**
**Status:** Rust CLI has `analyze` command, backend not using it yet

**Implementation:**
```python
# In dcsm_backend.py - replace stub /api/analyze
async def analyze_audio_real(request: web.Request):
    data = await request.json()
    file_id = data.get('file_id')
    file_path = UPLOAD_DIR / file_id
    
    # Call Rust audio-core CLI
    result = subprocess.run([
        AUDIO_CORE_BIN, 'analyze', str(file_path)
    ], capture_output=True, text=True, timeout=30)
    
    analysis = json.loads(result.stdout)
    return web.json_response({
        "success": True,
        "job_id": file_id,
        "tempo": analysis['tempo'],
        "beats": analysis['beats'],
        "onsets": analysis['onsets']
    })
```

**Files to Modify:**
- `dcsm_backend.py` - Replace lambda with real function
- Test with: `docker exec backend /usr/local/bin/audio-core analyze /app/uploads/test.wav`

---

#### **1.2 Waveform Peaks (Already Working)**
**Status:** ✅ Already implemented in `/files/waveform` endpoint

**Usage:**
```javascript
// Frontend can call
const peaks = await fetch(`/files/waveform?key=${fileKey}&width=1000`);
```

---

#### **1.3 Onset Detection**
**Status:** Endpoint exists (`/analyze/onsets`), needs connection to Rust

**Implementation:**
```python
async def analyze_onsets(request: web.Request):
    key = request.query.get("key")
    file_path = UPLOAD_DIR / key
    
    # Rust CLI already returns onsets in 'analyze' command
    result = run_audio_core(['analyze', str(file_path)])
    data = json.loads(result)
    
    return web.json_response({
        "sr": data['sample_rate'],
        "onsets": data['onsets']
    })
```

---

## 🎼 **PHASE 2: DRUM PATTERN GENERATION**

### **Objective:**
Connect DCSM pattern generation to frontend controls

### **Current State:**
- Rust has pattern generation code in `audio-core/src/patterns.rs`
- Backend has `/dcsm/generate` endpoint
- Frontend has mixer UI but not connected

### **Tasks:**

#### **2.1 Pattern Generation API**
**Endpoint:** POST `/dcsm/generate`

**Input:**
```json
{
  "bpm": 120,
  "style": "rock",
  "swing": "off",
  "humanize": 0.1,
  "seed": 42,
  "sections": [
    {"start": 0, "end": 4, "fill_in": false, "fill_out": true, "density": 0.7}
  ]
}
```

**Expected Output:**
```json
{
  "notes": [
    {"time": 0.0, "lane": "kick", "vel": 100},
    {"time": 0.5, "lane": "snare", "vel": 90}
  ],
  "midi_base64": "TVRoZAAA..."
}
```

**Implementation Status:**
- Backend endpoint exists but may need testing
- Rust CLI can generate patterns: `audio-core generate --bpm 120 --style rock`

---

#### **2.2 Smart Sectionization**
**Endpoint:** GET `/dcsm/sectionize`

**Purpose:** Detect song structure (intro/verse/chorus/bridge/outro)

**Usage:**
```javascript
const sections = await fetch(`/dcsm/sectionize?key=${fileKey}&bpm=120&mode=smart`);
// Returns: [{start: 0, end: 8, label: "intro"}, ...]
```

**Status:** 
- Endpoint exists in backend
- Rust has sectionization logic
- Needs integration testing

---

## 🎹 **PHASE 3: MIDI EXPORT**

### **Objective:**
Export generated drum patterns as MIDI files

### **Tasks:**

#### **3.1 MIDI File Generation**
**Current:** Backend returns base64 encoded MIDI

**Implementation:**
```python
# In dcsm_generate endpoint
midi_data = generate_midi(notes, bpm)
midi_b64 = base64.b64encode(midi_data).decode()

return web.json_response({
    "notes": notes,
    "midi_base64": midi_b64
})
```

**Frontend Download:**
```javascript
function downloadMIDI(base64Data, filename) {
  const blob = b64toBlob(base64Data, 'audio/midi');
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
}
```

---

## 🎨 **PHASE 4: FRONTEND INTEGRATION**

### **Objective:**
Connect UI controls to backend functionality

### **Tasks:**

#### **4.1 Upload → Analysis Flow**
**Current:** Basic flow working (upload → waveform)

**Next Steps:**
1. Display tempo analysis results in UI
2. Show detected beats/onsets on waveform
3. Add "Analyze" button to trigger deeper analysis

**Files:**
- `frontend/src/components/DCSMStudio.tsx` or similar
- `frontend/src/services/api.ts` - already has functions

---

#### **4.2 Pattern Generator Controls**
**UI Elements Needed:**
- BPM input (with auto-detect from analysis)
- Style selector (rock/jazz/funk/latin)
- Swing preset (off/light/heavy)
- Density slider (0-1)
- Humanize slider (0-1)

**Integration:**
```javascript
async function generatePattern(params) {
  const response = await fetch('/dcsm/generate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(params)
  });
  const {notes, midi_base64} = await response.json();
  displayNotesInPianoRoll(notes);
}
```

---

#### **4.3 Piano Roll / Drum Editor**
**Purpose:** Visualize and edit generated drum patterns

**Features:**
- 8 lanes (kick, snare, hihat, ohat, ride, tom, crash, clap)
- Time grid aligned to beats
- Click to add/remove notes
- Velocity editing

**Status:**
- UI components may exist in frontend
- Need to wire up to note data from backend

---

## 🔄 **PHASE 5: SESSION PERSISTENCE**

### **Objective:**
Save and load user projects

### **Current Endpoints:**
- POST `/session/{sid}` - Save session
- GET `/session/{sid}` - Load session

### **Implementation:**
```javascript
// Save current state
await fetch('/session/my-project-123', {
  method: 'POST',
  body: JSON.stringify({
    audioKey: 'uploads/myfile.wav',
    bpm: 120,
    sections: [...],
    patterns: [...]
  })
});

// Load later
const session = await fetch('/session/my-project-123').then(r => r.json());
```

---

## 📊 **PHASE 6: BENCHMARKING (OPTIONAL)**

### **Objective:**
Compare Rust vs Python performance

### **Available Endpoints:**
- GET `/bench/peaks?key={file}&impl=both`
- GET `/bench/analysis?key={file}&impl=both`
- GET `/bench/generate?bpm=120&impl=both`

### **Frontend Page:**
Create benchmark UI at http://localhost:3000/bench

**Display:**
- Python time vs Rust time
- Speedup ratio
- Memory usage

---

## 🛠️ **DEVELOPMENT WORKFLOW**

### **Testing New Features:**

#### **1. Test Rust CLI Directly:**
```bash
docker exec backend /usr/local/bin/audio-core analyze /app/uploads/test.wav
docker exec backend /usr/local/bin/audio-core generate --bpm 120 --style rock
```

#### **2. Update Backend Code:**
```bash
# Edit dcsm_backend.py locally
# Copy to container
docker cp dcsm_backend.py backend:/app/dcsm_backend.py
# Restart
docker restart backend
```

#### **3. Update Frontend:**
```bash
cd frontend
npm run build
docker cp build/. frontend:/usr/share/nginx/html/
# OR rebuild container
docker-compose build frontend
docker restart frontend
```

#### **4. Check Logs:**
```bash
docker logs backend --tail 50 -f
docker logs frontend --tail 20
```

---

## 🧪 **TESTING STRATEGY**

### **Unit Tests:**
- Rust: `cd audio-core && cargo test`
- Python: `pytest tests/` (if tests exist)

### **Integration Tests:**
```bash
# Test full upload → analyze → generate flow
curl -X POST -F "file=@test.wav" http://localhost:3000/api/upload
# Get file key from response
curl -X POST http://localhost:3000/api/analyze -d '{"file_id":"uploads/test.wav"}'
# Check results
curl http://localhost:3000/api/results/complete
```

### **E2E Tests:**
- Selenium/Playwright to test UI flows
- Upload file → Generate pattern → Download MIDI

---

## 📅 **RECOMMENDED DEVELOPMENT ORDER**

### **Week 1: Core Analysis**
1. ✅ Upload working (DONE)
2. Connect real tempo detection
3. Display BPM in UI
4. Show beats/onsets on waveform

### **Week 2: Pattern Generation**
1. Wire up `/dcsm/generate` endpoint
2. Add pattern controls to UI
3. Display generated notes in piano roll
4. Test different styles (rock/jazz/funk)

### **Week 3: MIDI Export**
1. Implement MIDI file generation
2. Add download button
3. Test in DAWs (Ableton, FL Studio, etc.)
4. Fix any MIDI compatibility issues

### **Week 4: Polish & Sessions**
1. Session save/load
2. Error handling & validation
3. Performance optimization
4. Documentation

---

## 🎯 **SUCCESS CRITERIA**

### **Phase 1 Complete:**
- [ ] Upload audio → Real BPM detected
- [ ] Onsets visualized on waveform
- [ ] Tempo displayed in UI

### **Phase 2 Complete:**
- [ ] Generate button creates drum pattern
- [ ] Notes displayed in piano roll
- [ ] Different styles produce different patterns

### **Phase 3 Complete:**
- [ ] Download MIDI button works
- [ ] MIDI files play correctly in DAWs
- [ ] Type-1 MIDI with 8 separate tracks

### **Phase 4 Complete:**
- [ ] Full UI flow: Upload → Analyze → Generate → Download
- [ ] All controls functional
- [ ] Pattern editing works

### **Phase 5 Complete:**
- [ ] Save/load sessions
- [ ] Projects persist across browser sessions

---

## 📚 **REFERENCE DOCUMENTATION**

### **Rust Audio-Core CLI:**
```bash
# View help
docker exec backend /usr/local/bin/audio-core --help

# Commands available:
audio-core peaks <file> --width 1000
audio-core analyze <file>
audio-core generate --bpm 120 --bars 8 --style rock
```

### **Backend API Reference:**
See `dcsm_backend.py` lines 496-518 for all routes

### **Frontend API Client:**
See `frontend/src/services/api.ts` for all available functions

---

## 💡 **QUICK WINS**

Start with these easy implementations:

1. **Display Real Tempo:** Just call Rust analyze and show BPM
2. **Generate Simple Pattern:** Use existing `/dcsm/generate` with default params
3. **Download MIDI:** Decode base64 and trigger browser download

Each builds on existing infrastructure - no new components needed!

---

**Ready to start with Phase 1: Connect Real Audio Analysis?**
