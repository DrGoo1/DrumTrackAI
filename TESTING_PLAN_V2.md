# 🧪 Drum Builder v2.0 - Testing Plan

**Phase 6: Testing & Polish**

Date: November 21, 2025  
Status: 🔵 **IN PROGRESS**

---

## 📋 **Testing Checklist**

### **1. Backend API Testing** (Critical)

- [ ] **Backend Server Running**
  - [ ] dcsm_backend.py starts without errors
  - [ ] Port 8000 is accessible
  - [ ] Health check endpoint responds

- [ ] **API Endpoint Testing**
  - [ ] POST /api/generate-drums accepts DrumGenerationConfig
  - [ ] Returns drum_track in response
  - [ ] Returns midi_notes for backward compatibility
  - [ ] Returns midi_base64 string
  - [ ] Metadata includes builder_version: "v2.0"

- [ ] **LLM Integration**
  - [ ] OpenAI API key configured (optional)
  - [ ] LLM call succeeds (if key present)
  - [ ] Analytics fallback works (no key)
  - [ ] Flat spec fallback works (no analytics)

- [ ] **Data Validation**
  - [ ] 960 PPQ resolution in response
  - [ ] microTimingMs values present
  - [ ] instrumentId values correct
  - [ ] Performance spec included

### **2. Frontend Integration Testing**

- [ ] **TypeScript Compilation**
  - [ ] No compilation errors
  - [ ] Types resolve correctly
  - [ ] Imports work properly

- [ ] **Component Rendering**
  - [ ] DrumBuilderPanelV2 renders
  - [ ] SectionTimelineStrip renders
  - [ ] RehumanizePanel renders
  - [ ] No console errors

- [ ] **User Interactions**
  - [ ] Sliders update values
  - [ ] Style selection works
  - [ ] Drummer selection works
  - [ ] Generate button clicks
  - [ ] Section selection works
  - [ ] Lock/unlock toggles

### **3. End-to-End Flow Testing**

- [ ] **Basic Generation**
  - [ ] Select section
  - [ ] Configure settings
  - [ ] Click Generate
  - [ ] Receive drum_track
  - [ ] Display in piano roll

- [ ] **Advanced Features**
  - [ ] Humanize Amount affects output
  - [ ] Ghost Note Amount works
  - [ ] Swing Amount works
  - [ ] Build Scope selector works
  - [ ] Section locks respected

- [ ] **Re-humanization**
  - [ ] Load track into panel
  - [ ] Apply preset
  - [ ] See changes immediately
  - [ ] Reset to original
  - [ ] Selection mode works

### **4. Performance Testing**

- [ ] **Response Times**
  - [ ] Template mode: < 100ms
  - [ ] AI variation: < 2s
  - [ ] Full AI: < 5s
  - [ ] Re-humanization: < 10ms

- [ ] **Memory Usage**
  - [ ] No memory leaks
  - [ ] Large tracks handle well
  - [ ] Multiple generations stable

### **5. Error Handling**

- [ ] **Network Errors**
  - [ ] Backend down: Graceful error
  - [ ] Timeout: Proper message
  - [ ] Invalid response: Caught

- [ ] **Validation Errors**
  - [ ] Invalid config: Rejected
  - [ ] Missing fields: Handled
  - [ ] Out-of-range values: Clamped

---

## 🚀 **Quick Start Testing**

### **Step 1: Verify Backend**

```bash
# Navigate to project
cd f:\DrumTracKAI_v1.1.16_Clean

# Start backend (if not running)
python dcsm_backend.py

# Test health (in another terminal)
curl http://localhost:8000/
```

**Expected:** Server responds with status

### **Step 2: Test API Endpoint**

```bash
# Test drum generation
curl -X POST http://localhost:8000/api/generate-drums \
  -H "Content-Type: application/json" \
  -d "{\"style\":\"rock\",\"drummer\":\"jeff_porcaro\",\"intensity\":0.7,\"variation\":0.8,\"humanize\":true,\"humanizeAmount\":0.7,\"ghostNoteAmount\":0.6,\"swingAmount\":0.2,\"generationMode\":\"template\",\"sectionId\":\"test\",\"startMeasure\":0,\"endMeasure\":4,\"tempos\":[120,120,120,120],\"timeSignature\":[4,4],\"fillLocations\":[3],\"fillType\":\"auto\"}"
```

**Expected:**
```json
{
  "ok": true,
  "drum_track": {
    "track_id": "...",
    "resolution_ppq": 960,
    "notes": [...],
    "performance_spec": {...}
  },
  "midi_notes": [...],
  "metadata": {
    "builder_version": "v2.0"
  }
}
```

### **Step 3: Check Frontend**

```bash
# Navigate to frontend
cd web-frontend

# Install dependencies (if not done)
npm install

# Start dev server
npm start
```

**Expected:** Opens at http://localhost:3000

### **Step 4: Verify TypeScript Types**

```bash
# Check for compilation errors
cd web-frontend
npm run build
```

**Expected:** No TypeScript errors

---

## 🔬 **Detailed Test Cases**

### **Test Case 1: Basic Generation (Template Mode)**

**Steps:**
1. Open DrumBuilderPanelV2
2. Set style: "rock"
3. Set drummer: "jeff_porcaro"
4. Set intensity: 70%
5. Set generation mode: "Fast Template"
6. Click "Generate Drums"

**Expected:**
- Request sent to /api/generate-drums
- Response includes drum_track
- Resolution is 960 PPQ
- Notes have microTimingMs values
- Display in piano roll

**Validation:**
```typescript
const track = response.drum_track;
assert(track.resolution_ppq === 960);
assert(track.notes.length > 0);
assert(track.notes[0].microTimingMs !== undefined);
assert(track.performance_spec !== null);
```

### **Test Case 2: Humanization Controls**

**Steps:**
1. Generate track (as above)
2. Set Humanize Amount: 80%
3. Set Ghost Note Amount: 70%
4. Set Swing Amount: 30%
5. Click "Generate Drums"

**Expected:**
- Config includes humanizeAmount: 0.8
- Config includes ghostNoteAmount: 0.7
- Config includes swingAmount: 0.3
- Backend applies these values
- Track shows increased variation

**Validation:**
```typescript
const stats = analyzeTrack(track);
assert(stats.ghostNoteCount > 0);
assert(stats.microTimingRange[1] > stats.microTimingRange[0]);
```

### **Test Case 3: Section Locking**

**Steps:**
1. Generate drums for "Verse 1"
2. Click "Lock" on Verse 1 section
3. Change settings
4. Click "Generate Drums" with buildScope: "full_song"

**Expected:**
- Verse 1 track preserved
- Other sections regenerated
- Verse 1 locked indicator shows
- Generate button disabled when locked section selected

**Validation:**
```typescript
const verse1Before = getTrackForSection('verse_1');
generateFullSong();
const verse1After = getTrackForSection('verse_1');
assert.deepEqual(verse1Before, verse1After);
```

### **Test Case 4: Client-Side Re-humanization**

**Steps:**
1. Load track with existing drums
2. Open RehumanizePanel
3. Select preset: "natural"
4. Click "Apply"

**Expected:**
- Track updates immediately (< 10ms)
- No backend call made
- Micro-timing values changed
- Velocity values adjusted
- Piano roll updates

**Validation:**
```typescript
const beforeStats = analyzeTrack(track);
const afterTrack = rehumanizeTrack(track, REHUMANIZE_PRESETS.natural);
const afterStats = analyzeTrack(afterTrack);

assert(afterStats.averageMicroTiming !== beforeStats.averageMicroTiming);
assert(afterStats.velocityRange !== beforeStats.velocityRange);
```

### **Test Case 5: Time Conversion Utilities**

**Steps:**
1. Call ticksToSeconds(1920, 120, 960)
2. Call secondsToTicks(2.0, 120, 960)
3. Call ticksToBarsBeatsTicks(3840, [4, 4], 960)

**Expected:**
```typescript
ticksToSeconds(1920, 120, 960) === 2.0  // 2 quarters at 120 BPM
secondsToTicks(2.0, 120, 960) === 1920
ticksToBarsBeatsTicks(3840, [4, 4], 960) === {
  bars: 1,
  beats: 0,
  ticks: 0,
  seconds: 0
}
```

### **Test Case 6: Track Statistics**

**Steps:**
1. Generate track
2. Call analyzeTrack(track)

**Expected:**
```typescript
const stats = analyzeTrack(track);
assert(stats.noteCount > 0);
assert(stats.averageVelocity >= 1 && stats.averageVelocity <= 127);
assert(stats.ghostNoteCount >= 0);
assert(stats.accentCount >= 0);
assert(stats.instrumentCounts.kick > 0);
```

---

## 🐛 **Known Issues to Test**

### **Potential Issues**

1. **LLM API Key**
   - Test with missing key
   - Test with invalid key
   - Verify fallback works

2. **Large Tracks**
   - Generate 100+ bar track
   - Check memory usage
   - Verify performance

3. **Edge Cases**
   - Empty section
   - Single note
   - Extreme tempo (30 BPM, 300 BPM)
   - Complex time signatures (7/8, 5/4)

4. **Browser Compatibility**
   - Chrome/Edge (Chromium)
   - Firefox
   - Safari (if available)

---

## 📊 **Performance Benchmarks**

### **Target Times**

| Operation | Target | Acceptable | Notes |
|-----------|--------|------------|-------|
| Template Generation | < 100ms | < 500ms | Backend only |
| AI Variation | < 1s | < 3s | Includes ML inference |
| Full AI | < 3s | < 10s | Includes LLM call |
| Re-humanization | < 10ms | < 50ms | Client-side |
| Track Analysis | < 5ms | < 20ms | Client-side |
| UI Render | < 16ms | < 32ms | 60 FPS target |

### **Memory Limits**

| Component | Target | Max | Notes |
|-----------|--------|-----|-------|
| Single Track | < 1MB | < 5MB | High-res MIDI |
| Piano Roll | < 50MB | < 200MB | Canvas rendering |
| Total Frontend | < 200MB | < 500MB | Including assets |

---

## ✅ **Testing Progress**

### **Status Legend**
- ⚪ Not Started
- 🔵 In Progress
- ✅ Passed
- ❌ Failed
- ⚠️ Needs Attention

### **Current Status**

| Test Area | Status | Notes |
|-----------|--------|-------|
| Backend Server | ⚪ | Need to verify |
| API Endpoint | ⚪ | Need to test |
| TypeScript Types | ⚪ | Need to compile |
| Component Render | ⚪ | Need to check |
| Basic Generation | ⚪ | Need to test |
| Humanization | ⚪ | Need to test |
| Section Locks | ⚪ | Need to test |
| Re-humanization | ⚪ | Need to test |
| Performance | ⚪ | Need to benchmark |
| Error Handling | ⚪ | Need to test |

---

## 🔧 **Testing Tools**

### **Manual Testing**

```bash
# Backend health check
curl http://localhost:8000/

# Test generation endpoint
curl -X POST http://localhost:8000/api/generate-drums \
  -H "Content-Type: application/json" \
  -d @test_config.json

# Frontend dev server
cd web-frontend && npm start
```

### **Automated Testing (Future)**

```bash
# Backend unit tests
cd backend
pytest tests/test_drum_builder_v2.py

# Frontend component tests
cd web-frontend
npm test

# E2E tests (Playwright)
npm run test:e2e
```

---

## 📝 **Test Report Template**

```
TEST: [Test Name]
DATE: [Date/Time]
TESTER: [Your Name]

SETUP:
- Backend: Running/Not Running
- Frontend: Running/Not Running
- Environment: Dev/Prod

STEPS:
1. [Step 1]
2. [Step 2]
3. [Step 3]

EXPECTED:
- [Expected outcome]

ACTUAL:
- [Actual outcome]

RESULT: ✅ PASS / ❌ FAIL / ⚠️ PARTIAL

NOTES:
- [Any observations]
- [Issues encountered]
- [Suggestions]

SCREENSHOTS:
- [Attach if relevant]
```

---

## 🚀 **Next Steps**

1. **Start Backend** - Verify server runs
2. **Test API** - Curl commands
3. **Check Frontend** - TypeScript compilation
4. **Manual Testing** - Walk through flows
5. **Document Results** - Update this file
6. **Fix Issues** - Address failures
7. **Retest** - Verify fixes
8. **Sign Off** - Mark complete

---

**Let's begin testing!** 🧪

Start with Step 1: Verify Backend
