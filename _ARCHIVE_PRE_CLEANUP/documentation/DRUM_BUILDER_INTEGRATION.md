# Drum Builder - System Integration Map

**Complete integration of all existing tools**

---

## 🔗 **System Flow**

```
AUDIO → ANALYSIS → UI → GENERATION → OUTPUT
  ↓         ↓        ↓        ↓          ↓
Rust     Sections  Select  Drummer    MIDI
FFI      + Tempo   Range   Database   Piano
                                      Roll
```

---

## **1. Rust Audio-Core (Analysis)**

**Files:** `audio-core/src/*.rs`

**Functions We Use:**
```rust
ac_analyze_full()      → Tempo per measure, beats, bars
ac_sectionize_smart()  → Sections with energy/spectral data
ac_generate_json()     → Drum pattern generation
ac_generate_midi64()   → MIDI export
```

---

## **2. Drummer Database**

**File:** `drummer_mapping_service.py`

```python
get_drummer_by_name("jeff_porcaro")
get_drummers_by_style("rock")
get_signature_patterns("bonham")
```

**Connected to:** `database/drummer_profiles.json`

---

## **3. AI Generator (GrooVAE)**

**File:** `ai_pattern_generator.py`

```python
generate_pattern(bars=8, style_embedding)
vary_pattern(base_pattern, variation=0.8)
```

**Model:** Magenta GrooVAE checkpoint (CUDA)

---

## **4. Rudiments & Fills**

**Create new:** `rudiments_library.py`

```python
FILL_PATTERNS = {
  "tom_run": ...,
  "snare_buzz": ...,
  "crash_buildup": ...
}
```

---

## **5. Drum Samples**

**Path:** `database/processed_stems/`

- Extract patterns from real recordings
- Jeff Porcaro, Bonham, etc. analyzed
- Convert stems to MIDI patterns

---

## **6. Frontend Components**

**Existing:**
- `Timeline.tsx` → Shows sections
- `PianoRoll.tsx` → Displays MIDI
- `DrumOptions.tsx` → Style controls

**New:**
- `MeasureSelector.tsx` → Click to select
- `DrumBuilderPanel.tsx` → Generate controls
- `HumanizeControls.tsx` → Timing/velocity

---

## **7. Backend API**

**File:** `dcsm_backend.py`

**New Endpoint:**
```python
@routes.post('/api/generate-drums')
async def generate_drums(request):
    # 1. Get drummer profile
    # 2. Generate/vary pattern
    # 3. Adapt to tempo changes
    # 4. Add fills
    # 5. Humanize
    # 6. Return MIDI
```

---

## 🚀 **User Workflow**

1. Upload audio → **Rust analysis**
2. View sections → **Timeline UI**
3. Select measures → **Click range**
4. Choose style → **Drummer DB**
5. Generate → **AI + Templates**
6. Edit → **Piano Roll**
7. Export → **MIDI file**

---

## 📋 **Implementation Tasks**

**Week 1:**
- [ ] `MeasureSelector` component
- [ ] `/api/generate-drums` endpoint
- [ ] Connect to drummer database
- [ ] Basic generation (templates)

**Week 2:**
- [ ] AI variation mode
- [ ] Humanization engine
- [ ] Fill library
- [ ] Piano roll measure markers

**Week 3:**
- [ ] Per-measure editing
- [ ] Copy/paste measures
- [ ] Export enhancements
- [ ] Polish & testing

---

**Result:** Measure-by-measure drum building using ALL existing tools!
