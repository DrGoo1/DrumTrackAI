# Section Selection & Arrangement Improvements

**Date:** November 20, 2025  
**Status:** ✅ Selection Implemented | ⚠️ Tempo/Labeling Needs Fix

---

## ✅ **What's Implemented:**

### **1. Timeline Section Selection**
- **Click** on any section in the timeline header to select it
- **Ctrl+Click** (or **Cmd+Click** on Mac) to multi-select sections
- **Selected sections** are highlighted with white overlay and thick white border
- Click empty space in header to **clear selection**

### **2. Collapsible Section List**
- **Musical Arrangement Manager** (right panel) now shows:
  - **All sections** when none selected
  - **Only selected sections** when one or more selected
- **Selection indicator** shows "X sections selected" with clear button
- Keeps section list focused on what matters

### **3. Generation Integration Ready**
- Selected sections are tracked in `selectedSectionIds` state
- Ready to link to drum generation (generate for selected sections only)
- Next step: Update generate button to use selected sections

---

## ⚠️ **Issues to Fix:**

### **Problem 1: Tempo Detection Way Too High**

**Test Song:** "Torn" by Natalie Imbruglia  
**Expected Tempo:** ~92-94 BPM (medium tempo ballad)  
**Detected Tempo:** 255 BPM (2.7x too fast!)

**Root Cause:**
The algorithm is likely detecting 16th notes or 8th notes as quarter notes.

**Fix Needed in `audio-core/src/dsp.rs`:**
```rust
// Current: Spectral flux autocorrelation may be picking up subdivisions
// Need: Better tempo octave correction and beat hierarchy analysis

// Possible fixes:
1. Add tempo octave correction (if detected > 180, try tempo/2)
2. Implement beat hierarchy (strong vs weak beats)
3. Use median filtering on inter-beat intervals
4. Add musical context (most pop songs are 80-160 BPM)
```

**Tempo Correction Strategy:**
```rust
fn correct_tempo_octave(tempo: f32) -> f32 {
    let mut corrected = tempo;
    
    // If tempo unreasonably high, divide by 2 until in reasonable range
    while corrected > 180.0 {
        corrected /= 2.0;
    }
    
    // If tempo unreasonably low, multiply by 2
    while corrected < 60.0 {
        corrected *= 2.0;
    }
    
    corrected
}
```

---

### **Problem 2: Section Labeling Too Generic**

**Current:** Most sections labeled as "verse"  
**Expected:** Intro, Verse, Pre-Chorus, Chorus, Bridge, Outro

**Root Cause:**
The section labeling in `audio-core/src/sectionize_smart.rs` is too simplistic. It only looks at:
- Energy levels
- Spectral centroid (brightness)
- Basic position heuristics

**What's Missing:**
- **Repetition analysis** - Choruses repeat musically
- **Harmonic similarity** - Similar chord progressions
- **Self-similarity matrix** - Compare sections to each other
- **Energy contours** - Choruses typically have higher, sustained energy
- **Spectral flux patterns** - Rhythmic density changes

**Improved Labeling Algorithm Needed:**

```rust
// audio-core/src/sectionize_smart.rs

1. Build self-similarity matrix using chroma features
2. Find repeated patterns (likely choruses)
3. Analyze energy trajectory:
   - Rising intro
   - High, sustained = chorus
   - Dynamic variation = verse
   - Energy drop = bridge
   - Fade out = outro
4. Use position heuristics as tiebreaker:
   - First section usually intro
   - Last section usually outro
   - Middle sections with repetition = chorus
```

---

## 📋 **Reference: "Torn" Structure**

**Actual Song Structure:**
```
0:00 - 0:15  | Intro         | Build-up, guitar
0:15 - 0:44  | Verse 1       | "I thought I saw a man..."
0:44 - 1:00  | Pre-Chorus    | "Don't you come around here..."
1:00 - 1:28  | Chorus        | "I'm all out of faith..."
1:28 - 1:57  | Verse 2       | "You're a little late..."
1:57 - 2:13  | Pre-Chorus    | Energy build
2:13 - 2:42  | Chorus        | (Repeat)
2:42 - 3:10  | Bridge        | "There's nothing where..."
3:10 - 3:39  | Final Chorus  | Extended, with variations
3:39 - 4:04  | Outro         | Fade with "I'm all out of faith"
```

**Key Characteristics:**
- **Chorus:** Highest energy, repeats 3 times, melodically similar
- **Verse:** Medium energy, different lyrics each time
- **Pre-Chorus:** Energy ramp before chorus
- **Bridge:** Different chord progression, contrasting section

---

## 🔧 **How to Use Section Selection:**

### **Workflow:**
1. **Upload audio** and click "🎯 Analyze Song Structure"
2. **Review sections** on timeline
3. **Click sections** to select (Ctrl+Click for multiple)
4. **Musical Arrangement Manager** shows only selected sections
5. **Adjust parameters** for selected sections
6. **Generate drums** (will use selected sections)

### **Selection Tips:**
- **Single section:** Click once to focus on it
- **Multiple sections:** Ctrl+Click each section
- **Chorus only:** Select all chorus sections for consistent drum pattern
- **Verse variety:** Select verses separately for varied patterns
- **Clear selection:** Click empty space in header or use "Clear selection" button

---

## 🚀 **Next Steps:**

### **Immediate (Frontend):**
- [x] Section selection on timeline
- [x] Visual highlighting
- [x] Collapsible section list
- [ ] Link generate button to selected sections
- [ ] Add "Generate for All Selected" button
- [ ] Show total duration of selected sections

### **Short-term (Backend/Rust):**
- [ ] Fix tempo octave detection (divide by 2 if > 180 BPM)
- [ ] Add tempo validation and correction
- [ ] Implement basic repetition detection for choruses
- [ ] Improve energy-based labeling

### **Medium-term (Analysis Quality):**
- [ ] Implement self-similarity matrix
- [ ] Add chroma feature extraction
- [ ] Harmonic structure analysis
- [ ] Better pre-chorus detection
- [ ] Bridge identification algorithm

---

## 🧪 **Testing Recommendations:**

### **Test with Known Songs:**
1. **"Torn" - Natalie Imbruglia** (92 BPM, clear structure)
2. **"Don't Stop Believin'" - Journey** (118 BPM, verse-chorus-bridge)
3. **"Billie Jean" - Michael Jackson** (117 BPM, repetitive structure)
4. **"Bohemian Rhapsody" - Queen** (Multiple tempos, complex structure)
5. **"Seven Nation Army" - White Stripes** (124 BPM, simple structure)

### **Validation Checklist:**
- [ ] Detected tempo within ±5 BPM of actual
- [ ] At least 60% of sections labeled correctly
- [ ] Chorus sections identified as repeating
- [ ] Intro/outro detected at boundaries
- [ ] Bridge detected in middle (if present)

---

## 📝 **Implementation Notes:**

### **Tempo Fix (Priority 1):**
Location: `audio-core/src/dsp.rs` line ~150-200 (tempo estimation)

```rust
// After autocorrelation tempo detection:
let tempo = estimate_tempo_from_onsets(&beat_times);
let corrected_tempo = correct_tempo_octave(tempo);
```

### **Labeling Fix (Priority 2):**
Location: `audio-core/src/sectionize_smart.rs` line ~200-300 (labeling logic)

```rust
// Add repetition analysis:
let repetition_groups = find_repeated_sections(&sections);
for group in repetition_groups {
    if group.len() >= 2 {
        // Label repeated sections as chorus
        for section_idx in group {
            sections[section_idx].label = "chorus";
        }
    }
}
```

---

## ✅ **Current Status:**

**Working:**
- ✅ Section display on timeline with tempo
- ✅ Click to select sections
- ✅ Multi-select with Ctrl/Cmd
- ✅ Visual highlighting of selected sections
- ✅ Filtered section list shows only selected
- ✅ Selection state management

**Needs Work:**
- ⚠️ Tempo detection accuracy (255 BPM should be 92 BPM)
- ⚠️ Section labeling variety (too many "verse")
- ⚠️ Chorus detection (repetition analysis)
- ⚠️ Pre-chorus identification
- ⚠️ Bridge detection

---

**Ready to test section selection in the browser!** The tempo and labeling improvements will require Rust code changes and recompilation.
