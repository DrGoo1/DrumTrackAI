# 🎵 Per-Section Tempo Detection - Design Document

## 🎯 Overview

Enable DrumTracKAI to detect and use different tempos for each musical section, handling:
- Songs with tempo changes (accelerando, ritardando)
- Tempo variations between sections (verse slower, chorus faster)
- Live recordings with natural drift
- More accurate drum pattern generation

---

## 🏗️ Architecture

### **Data Flow:**
```
Audio Upload
    ↓
Global Tempo Detection (baseline: e.g., 161.5 BPM)
    ↓
Energy-based Sectionization (using baseline tempo)
    ↓
Per-Section Tempo Analysis ← NEW FEATURE
    ↓
Section Manager (view/edit tempos per section)
    ↓
Drum Generation (using section-specific tempo)
```

---

## 📊 **Section Data Model Update**

### **Current Section Type:**
```typescript
type Section = {
  id: string;
  start: number;    // seconds
  end: number;      // seconds
  density: number;  // 0.0-1.0
  fillIn: boolean;
  fillOut: boolean;
  label: string;
  confidence?: number;
}
```

### **Enhanced Section Type:**
```typescript
type Section = {
  id: string;
  start: number;
  end: number;
  density: number;
  fillIn: boolean;
  fillOut: boolean;
  label: string;
  confidence?: number;
  
  // NEW TEMPO FIELDS
  tempo?: number;           // Detected tempo for this section (e.g., 162.3)
  tempoConfidence?: number; // 0.0-1.0 confidence in detection
  tempoLocked?: boolean;    // User has manually set tempo
  globalTempo?: number;     // Fallback to global if not detected
}
```

---

## 🔌 **Backend API**

### **New Endpoint: `/analyze/tempo_sections`**

**Request:**
```json
POST /analyze/tempo_sections
{
  "key": "1763316300213-Peg_No_Drums.mp3",
  "sections": [
    { "start": 0.0, "end": 5.95 },
    { "start": 5.95, "end": 17.85 },
    { "start": 17.85, "end": 29.75 }
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "start": 0.0,
      "end": 5.95,
      "tempo": 161.2,
      "confidence": 0.87,
      "candidates": [161.2, 80.6, 322.4]
    },
    {
      "start": 5.95,
      "end": 17.85,
      "tempo": 161.8,
      "confidence": 0.92,
      "candidates": [161.8, 80.9, 323.6]
    },
    {
      "start": 17.85,
      "end": 29.75,
      "tempo": 162.5,
      "confidence": 0.89,
      "candidates": [162.5, 81.25, 325.0]
    }
  ],
  "global_tempo": 161.5
}
```

**Implementation (Rust audio-core):**
```rust
// audio-core/src/dsp.rs
pub fn analyze_segment(
    pcm: &[f32], 
    sr: u32, 
    start_sec: f32, 
    end_sec: f32, 
    config: AnalysisConfig
) -> (f32, Vec<f32>, Vec<f32>) {
    let start_frame = (start_sec * sr as f32) as usize;
    let end_frame = (end_sec * sr as f32) as usize;
    let segment = &pcm[start_frame.min(pcm.len())..end_frame.min(pcm.len())];
    
    analyze(segment, sr, config)
}
```

---

## 🎨 **Frontend UI Changes**

### **Section Manager Enhancement:**

```
┌─────────────────────────────────────────┐
│ Section Manager                [+ Add]  │
├─────────────────────────────────────────┤
│ 1. INTRO                           ✏️🗑️ │
│    Start: 0:00 | End: 0:06             │
│    Duration: 4 bars                     │
│    Density: 50%                         │
│                                         │
│    🎵 Tempo: 161.2 BPM                  │ ← NEW
│    Confidence: 87% [🔄 Re-analyze]     │ ← NEW
│    [🔒 Lock Tempo] [✏️ Edit Manually]  │ ← NEW
│                                         │
│    [Density Slider]                     │
│    ☑ Fill In  ☐ Fill Out               │
│    [✂️ Split] [🔗 Merge]                │
└─────────────────────────────────────────┘
```

### **Tempo Indicators:**
- **Green badge**: High confidence (>0.85)
- **Yellow badge**: Medium confidence (0.6-0.85)
- **Red badge**: Low confidence (<0.6) - manual adjustment recommended
- **Lock icon**: User has overridden detection

---

## 🔄 **Workflow**

### **Automatic Mode (Default):**
1. Upload audio
2. Detect global tempo: 161.5 BPM
3. Create sections using global tempo
4. **Auto-analyze each section's tempo**
5. Update section cards with individual tempos
6. User can review and lock/edit as needed

### **Manual Adjustment:**
1. User splits/merges sections
2. System automatically re-analyzes affected sections
3. Or user clicks "🔄 Re-analyze" button
4. Or user clicks "✏️ Edit Manually" to override

### **Drum Generation:**
```javascript
generateDrumPattern({
  bpm: section.tempo || globalBpm,  // Use section tempo if available
  section: {
    start: section.start,
    end: section.end,
    density: section.density,
    // ...
  }
})
```

---

## 🎯 **Use Cases**

### **Use Case 1: Song with Tempo Change**
```
Intro:   160 BPM  (slow build)
Verse:   162 BPM  (main tempo)
Chorus:  165 BPM  (energy boost!)
Bridge:  158 BPM  (slow down)
Outro:   160 BPM  (return to intro feel)
```

**Result:** Each section gets drums that match its actual tempo.

### **Use Case 2: Live Recording with Drift**
```
Section 1: 161.2 BPM (band starts tight)
Section 2: 161.8 BPM (speeds up slightly)
Section 3: 162.5 BPM (natural acceleration)
Section 4: 161.0 BPM (settles back down)
```

**Result:** Drums stay in sync throughout the song.

### **Use Case 3: Rubato or Free Time**
```
Intro: No tempo detected (confidence: 0.2)
→ User manually sets: 120 BPM and locks it
→ Or chooses "No Drums" for this section
```

---

## ⚡ **Performance Optimization**

### **Smart Re-analysis:**
Only re-analyze when needed:
- Section boundaries change by > 1 second
- User explicitly requests re-analysis
- Section merged/split

### **Caching:**
```javascript
// Cache tempo analysis results
const tempoCache = new Map<string, TempoResult>();
const cacheKey = `${key}-${start.toFixed(2)}-${end.toFixed(2)}`;

if (tempoCache.has(cacheKey)) {
  return tempoCache.get(cacheKey);
}
```

### **Parallel Analysis:**
Analyze all sections in parallel:
```javascript
const tempoResults = await Promise.all(
  sections.map(s => analyzeTempo(key, s.start, s.end))
);
```

---

## 🧪 **Testing Strategy**

### **Test Files Needed:**
1. **Constant Tempo:** Standard rock song (should show ~same tempo all sections)
2. **Accelerando:** Song that speeds up (e.g., 140 → 160 BPM)
3. **Section Variations:** Verse 120, Chorus 130
4. **Live Recording:** Natural drift (±5 BPM variation)
5. **Rubato/Free Time:** Classical or jazz (low confidence expected)

### **Validation:**
- Compare section tempos to DAW analysis (Ableton, Pro Tools)
- Verify drum patterns stay in sync
- Check confidence scores match subjective difficulty

---

## 📝 **Implementation Checklist**

### **Phase 1: Backend (2-3 hours)**
- [ ] Add `/analyze/tempo_sections` endpoint to `dcsm_backend.py`
- [ ] Implement segment analysis in Rust `audio-core`
- [ ] Add parallel processing for multiple sections
- [ ] Test with various audio files

### **Phase 2: Frontend Data Model (1 hour)**
- [ ] Update `Section` type with tempo fields
- [ ] Add tempo to section state management
- [ ] Create `analyzeSectionTempos()` API function

### **Phase 3: UI Enhancement (2 hours)**
- [ ] Add tempo display to Section Manager cards
- [ ] Add confidence badges (color-coded)
- [ ] Add "Re-analyze" button per section
- [ ] Add "Lock Tempo" checkbox
- [ ] Add manual tempo input field

### **Phase 4: Auto-Analysis Integration (1 hour)**
- [ ] Call tempo analysis after sectionization
- [ ] Update sections with detected tempos
- [ ] Handle re-analysis on section edits
- [ ] Add loading states

### **Phase 5: Drum Generation (1 hour)**
- [ ] Update `generateDrumPattern()` to use section tempo
- [ ] Fallback to global tempo if not available
- [ ] Test with varying tempos

### **Phase 6: Polish (1 hour)**
- [ ] Add tooltips explaining confidence
- [ ] Add visual indicators for tempo changes
- [ ] Add "Analyze All" button
- [ ] Performance optimization

**Total Estimated Time: 8-9 hours**

---

## 🎵 **Alternative: Tempo Map Visualization**

For advanced users, show a tempo curve:

```
Tempo (BPM)
165 │         ╭────╮
160 │────╭────╯    ╰────╮
155 │                    ╰────
    └─────────────────────────── Time
      Intro Verse Chorus Bridge
```

This would require:
- Beat-by-beat tempo analysis
- Canvas-based visualization
- More complex UI

**Recommendation:** Implement basic per-section first, add visualization later if needed.

---

## 🚀 **Immediate Next Steps**

**Do you want me to implement this? If yes, I'll:**

1. **Start with backend** - Add tempo analysis endpoint
2. **Update Section type** - Add tempo fields
3. **Enhance Section Manager** - Show tempo per section
4. **Add auto-analysis** - Call after sectionization
5. **Test with your audio** - Verify it works

**Which approach do you prefer?**

A. **Automatic** - Analyze all sections immediately after detection
B. **Manual** - User clicks "Analyze Tempos" button when ready
C. **Hybrid** - Auto-analyze with option to re-analyze

**I recommend Hybrid (C) - automatic but with manual override capability.**
