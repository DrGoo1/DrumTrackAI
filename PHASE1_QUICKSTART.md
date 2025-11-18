# 🚀 Phase 1 Quick Start Guide

**Complete Song Analysis + MIDI Creation Workflow**

---

## 📋 Pre-Flight Checklist

### 1. **Backend Requirements**

```bash
# Verify Python version
python --version  # Must be 3.11.x

# Activate virtual environment
.\drumtrackai_env\Scripts\activate

# Verify dependencies
pip list | grep -E "aiohttp|librosa|numpy"
```

### 2. **Rust Audio Core (Optional but Recommended)**

```bash
# Build Rust audio-core (5-7x faster than Python)
cd audio-core
cargo build --release
cd ..

# Set environment variables
set USE_RUST=1
set AUDIO_CORE_BIN=%CD%\audio-core\target\release\audio-core.exe
```

### 3. **Frontend Requirements**

```bash
# Navigate to frontend
cd frontend

# Install dependencies (if not already done)
npm install

# Start frontend dev server
npm start
```

---

## 🎯 Running Phase 1 Tests

### **Basic Test (No Audio File)**

Tests backend, drummer system, and Rust availability:

```bash
python test_phase1_complete_workflow.py
```

**Expected Output:**
```
✓ Backend is healthy
✓ Found 10 drummers
✓ Loaded drummer characteristics
✓ Rust audio-core available
⚠ No test audio file provided (skipping upload tests)

TEST SUMMARY:
  Passed:   4 / 4
  Warnings: 1
```

### **Full Workflow Test (With Audio)**

Complete end-to-end test with actual audio file:

```bash
python test_phase1_complete_workflow.py "path/to/your/song.mp3"
```

**Example:**
```bash
python test_phase1_complete_workflow.py "C:/Music/Peg_No_Drums.mp3"
```

**Expected Output:**
```
✓ Backend is healthy
✓ Found 10 drummers  
✓ Loaded: Studio Groove Master
✓ Rust audio-core available
✓ File uploaded: uploads/xxx.mp3
✓ Tempo detected: 161.0 BPM
✓ Detected 7 sections
✓ Generated 487 MIDI notes
✓ MIDI notes in correct format

TEST SUMMARY:
  Passed:   8 / 8
  Warnings: 0

Phase 1 is READY FOR PRODUCTION! 🎉
```

---

## 🎹 Manual Workflow Test (In Browser)

### **Step 1: Start Services**

**Terminal 1 - Backend:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean
.\drumtrackai_env\Scripts\activate
python dcsm_backend.py
```

**Terminal 2 - Frontend:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean\frontend
npm start
```

### **Step 2: Access DCSM Studio**

Open browser to: **http://localhost:3000**

### **Step 3: Complete Workflow**

#### **3.1 Upload Audio**
1. Click **"Upload Audio"** button
2. Select MP3/WAV file (e.g., Peg_No_Drums.mp3)
3. Wait for waveform to appear
4. Verify tempo detected (should show in BPM field)

**✅ Checkpoint:** Waveform visible, tempo detected

#### **3.2 Verify Sectionization**
1. Sections should auto-detect after upload
2. Look for colored section blocks on timeline
3. Check section labels (intro, verse, chorus, etc.)
4. Each section should have fill toggles and density slider

**✅ Checkpoint:** Multiple sections visible with labels

#### **3.3 Select Drummer**
1. Click **"Select Drummer Style"** in right sidebar
2. Browse 10 DrumTrackAI drummers
3. Click on **"Studio Groove Master"** (Jeff Porcaro)
4. Verify drummer badge appears at top
5. Console should log: "Selected drummer: Studio Groove Master"

**✅ Checkpoint:** Drummer selected, badge visible

#### **3.4 Generate Drums**
1. Click **"Generate"** on first section
2. Wait for processing (should be quick)
3. Check piano roll below timeline
4. Should see MIDI notes appear (8 lanes: kick, snare, etc.)
5. Console should log generation parameters

**✅ Checkpoint:** MIDI notes visible in piano roll

#### **3.5 Play Back**
1. Click **"Play"** button in transport
2. Playhead should move across timeline
3. Drums should play back (if audio engine working)
4. VU meters should respond

**✅ Checkpoint:** Playback works

#### **3.6 Edit MIDI (Optional)**
1. Click on piano roll to add/remove notes
2. Drag notes to adjust timing
3. Changes should reflect immediately

**✅ Checkpoint:** MIDI editing works

#### **3.7 Generate All Sections**
1. Click generate on each section
2. Or use "Generate All" (if implemented)
3. Verify all sections have notes

**✅ Checkpoint:** Complete drum track

---

## 🐛 Troubleshooting

### **Backend Won't Start**

```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Kill existing process if needed
taskkill /PID <pid> /F

# Restart backend
python dcsm_backend.py
```

### **Frontend Won't Start**

```bash
# Clean install
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### **No Drummers Appearing**

```bash
# Test drummer endpoint directly
curl http://localhost:8000/api/drummers

# Should return JSON with 10 drummers
# If not, check drummer_mapping_service.py is imported
```

### **Generation Fails**

```bash
# Check Rust is built
ls audio-core/target/release/audio-core.exe

# If missing:
cd audio-core
cargo build --release

# Check environment variables
echo %USE_RUST%
echo %AUDIO_CORE_BIN%

# Test Rust directly
.\audio-core\target\release\audio-core.exe generate --bpm 120 --start 0 --end 8 --style rock
```

### **No MIDI Notes Appear**

**Check Console (F12):**
- Look for errors in Network tab
- Check Console for JavaScript errors
- Verify API call succeeded

**Check Backend Logs:**
- Look for errors in terminal where backend is running
- Check Rust subprocess output

**Verify Data:**
```bash
# Test generation endpoint directly
curl -X POST http://localhost:8000/api/generate_with_drummer \
  -H "Content-Type: application/json" \
  -d '{
    "drummer_id": "studio_groove_master",
    "bpm": 120,
    "sections": [{"start": 0, "end": 8, "fill_in": false, "fill_out": true, "label": "test", "density": 0.7}]
  }'
```

---

## 📊 Expected Performance

### **With Rust (Recommended):**
- Tempo detection: **< 500ms**
- Sectionization: **< 1s**
- Drum generation: **< 200ms per section**
- MIDI export: **< 100ms**

### **Without Rust (Python Only):**
- Tempo detection: **2-3s**
- Sectionization: **5-7s**
- Drum generation: **1-2s per section**
- MIDI export: **< 100ms**

---

## ✅ Phase 1 Completion Criteria

Before moving to Phase 2, ensure:

- [x] Backend starts without errors
- [x] Frontend connects to backend
- [x] 10 drummers load successfully
- [x] Drummer characteristics load from DB (or fallback)
- [x] Audio upload works (MP3/WAV)
- [x] Tempo detection works
- [x] Sectionization detects multiple sections
- [x] Drummer selection updates UI
- [x] Drum generation produces MIDI notes
- [x] Piano roll displays notes correctly
- [x] Playback works (even if basic)
- [x] All sections can be generated
- [x] MIDI data format is correct
- [x] No console errors during workflow
- [x] Performance is acceptable

---

## 🚀 Next Steps After Phase 1

Once all checks pass:

1. **Document any issues** found during testing
2. **Create baseline MIDI exports** from test songs
3. **Prepare for Phase 2** (Humanization)
4. **Optional:** Create video walkthrough of workflow

---

## 📝 Test Report Template

```
PHASE 1 TEST REPORT
==================

Date: _______________
Tester: _______________
Environment: _______________

Backend Version: v1.1.16
Frontend Version: v1.1.16
Rust Version: _______________

Test Audio Files:
- [ ] Peg_No_Drums.mp3
- [ ] _________________
- [ ] _________________

Results:
- Backend Health: [ PASS / FAIL ]
- Drummer List: [ PASS / FAIL ]
- Drummer Details: [ PASS / FAIL ]
- Audio Upload: [ PASS / FAIL ]
- Tempo Detection: [ PASS / FAIL ]
- Sectionization: [ PASS / FAIL ]
- Drum Generation: [ PASS / FAIL ]
- MIDI Display: [ PASS / FAIL ]
- Playback: [ PASS / FAIL ]
- MIDI Export: [ PASS / FAIL ]

Notes:
_________________________________
_________________________________
_________________________________

Ready for Phase 2? [ YES / NO ]
```

---

**Let's test Phase 1!** 🎯
