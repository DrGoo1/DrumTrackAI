# 🥁 Jamstix-Style DCSM Piano Roll Integration Plan

**Comprehensive Upgrade: Drum Builder v2.0 → Professional Drum Editor**

Date: November 21, 2025, 4:10 PM  
Source: ChatGPT comprehensive package  
Status: 🔵 **READY TO INTEGRATE**

---

## 📊 **What This Adds**

### **Core Enhancements**

1. **64th-Note Resolution** - Ultra-high precision grid
2. **Jamstix-Style Per-Note Attributes** - Priority, timing offset, hit style, limb assignment
3. **Aspect Views** - Groove / Accent / Fill filtering
4. **Groove Weight Overlay** - Heavy / Neutral / Syncopated tick weights
5. **Part Type System** - Jamstix-inspired song part presets
6. **Power Modeling** - Guide track analysis → dynamic intensity
7. **Enhanced Note Inspector** - Complete per-note control panel
8. **Limb-Centric Model** - Optional limb view (LH/RH/LF/RF)

### **Why This Matters**

- **Professional Quality**: Matches or exceeds Jamstix capabilities
- **Modern UX**: Clean React UI vs Jamstix legacy interface
- **LLM Integration**: Performance specs drive the limb/priority/timing model
- **Complete Control**: Per-note editing + global groove shaping
- **64th Resolution**: Handles fastest humanization/polyrhythms

---

## 🏗️ **Architecture Overview**

```
┌────────────────────────────────────────────────────────────┐
│                      BACKEND (Python)                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │ drum_generation_config.py                        │   │
│  │ - DrumGenerationConfig with new controls        │   │
│  │ - humanizeAmount, ghostNoteAmount, swingAmount  │   │
│  │ - guideEnabled, guideInstrument                 │   │
│  │ - buildScope (full_song | selected_section)     │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ part_types_config.py (Jamstix-inspired)         │   │
│  │ - Intro, Verse, Pre-Chorus, Chorus, Bridge...   │   │
│  │ - Default intensity, variation, fills, hand     │   │
│  │ - Groove profiles per part type                 │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ power_model.py                                   │   │
│  │ - Compute per-bar power from guide RMS          │   │
│  │ - Combine with user intensity                   │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ llm_performance_spec.py (Enhanced)               │   │
│  │ - Build comprehensive prompt with:               │   │
│  │   • SongMap, part types, power curve            │   │
│  │   • Drummer profile, guide info                 │   │
│  │ - Returns DrumPerformanceSpec with:             │   │
│  │   • Per-instrument micro-timing profiles        │   │
│  │   • Velocity profiles, ghost/flam/drag probs    │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ dcsm_drumtrack_schema.py                         │   │
│  │ - DrumNoteEvent with Jamstix attributes:        │   │
│  │   • limbId (LH/RH/LF/RF)                        │   │
│  │   • priority (0..1)                             │   │
│  │   • timingOffsetMs (±50ms)                      │   │
│  │   • hatOpenLevel (0..1)                         │   │
│  │   • hitStyle (single/double/bounce)             │   │
│  │   • locked (bool)                               │   │
│  │ - DrumTrackForDCSM with 960+ PPQ resolution     │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ dcsm_drumtrack_builder.py                        │   │
│  │ - Convert internal events → DrumTrackForDCSM    │   │
│  │ - Apply performance spec micro-timing           │   │
│  │ - Assign phrase/performance group IDs           │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ dcsm_generate_drums_api.py                       │   │
│  │ - POST /dcsm/generate_drums                      │   │
│  │ - Returns: midi_smf_base64 + drum_track dict    │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
                           ↓
┌────────────────────────────────────────────────────────────┐
│                     FRONTEND (React/TS)                    │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────────────────────────────────────────┐   │
│  │ types/drumTrack.ts (Enhanced)                    │   │
│  │ - DrumNoteEvent with all Jamstix attributes     │   │
│  │ - NoteAspect: "groove" | "accent" | "fill"      │   │
│  │ - LimbId: "LH" | "RH" | "LF" | "RF" | ...       │   │
│  │ - HitStyle: "single" | "double" | "bounce"      │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ types/grooveWeight.ts                            │   │
│  │ - GrooveWeight: "heavy" | "neutral" | "syncopated" │
│  │ - GrooveWeightMap per bar/subdivision           │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ utils/pianoRollGrid.ts                           │   │
│  │ - GridResolution: "16th" | "32nd" | "64th"      │   │
│  │ - getSubdivisionsPerBar(), getTicksPerSubdivision() │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ components/drums/DrumPianoRoll.tsx               │   │
│  │ - 64th-note resolution support                   │   │
│  │ - Instrument lanes (16 drum voices)             │   │
│  │ - Aspect filtering (All/Groove/Accent/Fill)     │   │
│  │ - Groove weight overlay                          │   │
│  │ - Note selection & multi-select                  │   │
│  │ - Color-coded by aspect + flags                  │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ components/drums/NoteInspector.tsx               │   │
│  │ - Velocity slider (1-127)                        │   │
│  │ - Priority slider (0-1)                          │   │
│  │ - Timing offset slider (±50ms)                   │   │
│  │ - Hat open slider (0-1, for hi-hats)            │   │
│  │ - Hit style radio (single/double/bounce)        │   │
│  │ - Flags: Ghost, Accent, Flam, Drag, Lock        │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │ components/drums/DrumEditorPane.tsx              │   │
│  │ - Layout: PianoRoll + NoteInspector             │   │
│  │ - Grid resolution selector                       │   │
│  │ - Aspect view selector                           │   │
│  │ - Note selection management                      │   │
│  └──────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

---

## 📋 **Integration Checklist**

### **Phase 1: Backend Foundation** (2-3 hours)

- [ ] **A1. Update drum_generation_config.py**
  - Add `humanizeAmount`, `ghostNoteAmount`, `swingAmount` fields
  - Add `guideEnabled`, `guideInstrument` fields
  - Add `buildScope` field
  - Keep backward compatible with existing v2.0

- [ ] **A2. Add part_types_config.py**
  - Create PART_TYPES dict with presets
  - Implement `get_part_type_preset()`
  - Document part type IDs

- [ ] **A3. Add power_model.py**
  - Implement `compute_power_curve_from_guide()`
  - Integrate with guide track RMS analysis
  - Return per-bar power values

- [ ] **A4. Enhance llm_performance_spec.py**
  - Update LLM prompt with new fields
  - Include part types, power curve in prompt
  - Update response parsing

- [ ] **A5. Add dcsm_drumtrack_schema.py**
  - Define enhanced `DrumNoteEvent` with Jamstix attributes
  - Define `DrumTrackForDCSM` structure
  - Add helper functions

- [ ] **A6. Add dcsm_drumtrack_builder.py**
  - Implement `build_drumtrack_for_dcsm()`
  - Apply micro-timing from performance spec
  - Assign limb IDs, priorities

- [ ] **A7. Add/Update dcsm_generate_drums_api.py**
  - Create new endpoint or merge into existing
  - Wire up all new modules
  - Test end-to-end

### **Phase 2: Frontend Types & Utilities** (1-2 hours)

- [ ] **B1. Update types/drumTrack.ts**
  - Add `LimbId`, `HitStyle`, `NoteAspect` types
  - Extend `DrumNoteEvent` with Jamstix attributes
  - Add `DrumPerformanceSpec` types
  - Update `DrumTrackForDCSM`

- [ ] **B2. Add types/grooveWeight.ts**
  - Define `GrooveWeight` type
  - Define `GrooveWeightMap` structure
  - Export interfaces

- [ ] **B3. Add utils/pianoRollGrid.ts**
  - Implement grid resolution helpers
  - Support 16th, 32nd, 64th subdivisions
  - Calculate ticks per subdivision

- [ ] **B4. Update utils/drumTrackUtils.ts**
  - Add helpers for new note attributes
  - Update time conversion for high-res
  - Add limb-related utilities

### **Phase 3: Piano Roll Components** (3-4 hours)

- [ ] **C1. Create components/drums/DrumPianoRoll.tsx**
  - Implement 64th-note grid rendering
  - Add instrument lane layout
  - Implement aspect filtering
  - Add groove weight overlay
  - Handle note selection
  - Color-code by aspect + flags

- [ ] **C2. Create components/drums/NoteInspector.tsx**
  - Velocity slider
  - Priority slider
  - Timing offset slider
  - Hat open slider (conditional)
  - Hit style radio buttons
  - Flag checkboxes
  - Lock toggle

- [ ] **C3. Create components/drums/DrumEditorPane.tsx**
  - Layout PianoRoll + NoteInspector
  - Add grid resolution selector
  - Add aspect view selector
  - Wire up note selection
  - Handle note updates

### **Phase 4: Integration & Testing** (2-3 hours)

- [ ] **D1. Wire Backend to Frontend**
  - Update API client
  - Handle new response format
  - Map drum_track to UI

- [ ] **D2. Update Existing Components**
  - Integrate DrumEditorPane into WebDAWApp
  - Replace or extend existing piano roll
  - Update DrumBuilderPanelV2 if needed

- [ ] **D3. Test End-to-End**
  - Generate with new controls
  - Verify 64th-note precision
  - Test note inspector
  - Test aspect filtering
  - Test groove weights

---

## 🎯 **Implementation Strategy**

### **Option A: Clean Integration** (Recommended)

Keep existing v2.0 intact, add Jamstix features as enhancement layer:

1. **Backend:**
   - Create new modules alongside existing
   - Keep `drum_generation_api.py` as is
   - Add `dcsm_generate_drums_api.py` as alternative endpoint
   - Both endpoints can coexist

2. **Frontend:**
   - Keep existing components
   - Add new drum editor components
   - Allow user to toggle between "simple" and "pro" modes
   - Pro mode shows DrumEditorPane with full Jamstix features

**Pros:**
- No risk to existing v2.0 work
- Can A/B test both approaches
- Gradual migration path
- Easier rollback

**Cons:**
- More files initially
- Eventually need to merge

### **Option B: Direct Replacement**

Replace existing with enhanced versions:

1. **Backend:**
   - Update `drum_generation_api.py` in place
   - Merge schema files
   - Single endpoint

2. **Frontend:**
   - Replace existing piano roll
   - Replace existing types
   - Single code path

**Pros:**
- Cleaner final structure
- Single source of truth
- Less maintenance

**Cons:**
- Higher risk
- Harder to test
- Must get it right first time

**Recommendation:** Start with Option A, merge to Option B after validation.

---

## 📁 **File Structure**

### **Backend (Python)**

```
backend/
├── drum_generation/
│   ├── __init__.py
│   ├── drum_generation_config.py      ← UPDATE (add new fields)
│   ├── part_types_config.py           ← NEW
│   ├── power_model.py                 ← NEW
│   ├── llm_performance_spec.py        ← UPDATE (enhance prompt)
│   └── pattern_layer.py               ← EXISTING
├── dcsmpiano/
│   ├── __init__.py
│   ├── drumtrack_schema.py            ← REPLACE with dcsm_drumtrack_schema.py
│   └── drumtrack_builder_dcsmpiano.py ← REPLACE with dcsm_drumtrack_builder.py
├── examples/
│   └── integration_example.py
└── tests/
    └── test_drum_builder_v2.py

# Root level:
drum_generation_api.py                  ← EXISTING
dcsm_generate_drums_api.py             ← NEW (or merge into above)
```

### **Frontend (TypeScript/React)**

```
frontend/src/
├── types/
│   ├── drumTrack.ts                   ← UPDATE (add Jamstix attributes)
│   ├── drumGenerationConfig.ts        ← UPDATE (add new fields)
│   └── grooveWeight.ts                ← NEW
├── utils/
│   ├── drumTrackUtils.ts              ← UPDATE (add limb helpers)
│   ├── pianoRollGrid.ts               ← NEW
│   └── rehumanize.ts                  ← EXISTING
└── components/
    ├── drums/                          ← NEW DIRECTORY
    │   ├── DrumPianoRoll.tsx          ← NEW (64th-note capable)
    │   ├── NoteInspector.tsx          ← NEW (Jamstix-style)
    │   ├── DrumEditorPane.tsx         ← NEW (layout)
    │   └── SectionTimelineStrip.tsx   ← EXISTING (already created)
    ├── DrumBuilderPanelV2.tsx         ← EXISTING
    └── RehumanizePanel.tsx            ← EXISTING
```

---

## 🔧 **Technical Details**

### **Resolution Support**

**Current:** 480 PPQ (standard MIDI)
**v2.0:** 960 PPQ (double resolution)
**Jamstix:** 960-1920 PPQ (flexible)

**Implementation:**
- Set `resolution_ppq` to 960 or 1920
- At 960 PPQ in 4/4:
  - Quarter note: 960 ticks
  - 16th note: 60 ticks
  - 32nd note: 30 ticks
  - **64th note: 15 ticks**
  
**Grid Calculation:**
```typescript
const subdivisionsPerBar = 64;  // For 64th grid
const ticksPerSubdivision = (960 * 4) / 64 = 60 ticks
```

### **Aspect System**

**Definition:**
- **Groove:** Core pattern notes (backbeat, hi-hat pattern)
- **Accent:** Emphasized hits (crashes, accented snares)
- **Fill:** Transitional fills (tom runs, crashes)

**Implementation:**
```typescript
export type NoteAspect = "groove" | "accent" | "fill";

// In DrumNoteEvent:
aspect?: NoteAspect;

// Filter in UI:
const visibleNotes = notes.filter(n => 
  currentAspect === "all" || n.aspect === currentAspect
);
```

### **Groove Weights**

**Jamstix Concept:**
- **Heavy:** Strong anchor points (downbeats, backbeats)
- **Neutral:** Normal grid subdivisions
- **Syncopated:** Off-beat emphasis

**Storage:**
```typescript
grooveWeights: {
  [barIndex]: {
    [subdivisionIndex]: {
      weight: "heavy" | "neutral" | "syncopated",
      forceHit?: boolean,
      forceSilent?: boolean
    }
  }
}
```

**Visual:**
- Heavy: Thicker grid line, bright color
- Neutral: Normal grid line
- Syncopated: Dashed or alternate color

---

## 🎨 **UI/UX Considerations**

### **Layout Options**

**Option 1: Side-by-Side**
```
┌─────────────────────────┬──────────┐
│                         │          │
│   Piano Roll            │   Note   │
│   (64th grid)           │ Inspector│
│                         │          │
└─────────────────────────┴──────────┘
```

**Option 2: Floating Panel**
```
┌─────────────────────────────────────┐
│                                     │
│   Piano Roll (64th grid)            │
│                                     │
│        ┌──────────┐                │
│        │  Note    │                │
│        │Inspector │                │
│        └──────────┘                │
└─────────────────────────────────────┘
```

**Recommendation:** Side-by-side, with inspector collapsible.

### **Color Scheme**

**Aspect Colors:**
- Groove: Slate/neutral (#64748B)
- Accent: Amber/bright (#F59E0B)
- Fill: Purple (#A855F7)

**Note Flags:**
- Ghost: Semi-transparent overlay
- Accent: Brighter fill
- Flam/Drag: Small icon overlay
- Locked: Ring/outline (emerald #10B981)

**Groove Weights:**
- Heavy: Bright line (#94A3B8)
- Neutral: Normal line (#475569)
- Syncopated: Amber line (#F59E0B)

---

## ⚠️ **Compatibility Considerations**

### **Backward Compatibility**

**Must Maintain:**
- Existing v2.0 API endpoint works
- Existing components still functional
- Existing types still valid
- Legacy MIDI format still exported

**Strategy:**
- New fields are **optional** with defaults
- Response includes both formats:
  ```json
  {
    "drum_track": { ... },    // NEW format
    "midi_notes": [ ... ],    // LEGACY format
    "midi_base64": "..."
  }
  ```

### **Migration Path**

1. **Phase 1:** Add new modules, keep old
2. **Phase 2:** New UI alongside old
3. **Phase 3:** Test both in parallel
4. **Phase 4:** Gradually deprecate old
5. **Phase 5:** Remove old after validation

---

## 🧪 **Testing Strategy**

### **Unit Tests**

**Backend:**
- [ ] Test part type presets
- [ ] Test power curve calculation
- [ ] Test performance spec generation
- [ ] Test drumtrack builder
- [ ] Test limb assignment logic

**Frontend:**
- [ ] Test grid calculations (16th/32nd/64th)
- [ ] Test aspect filtering
- [ ] Test note selection
- [ ] Test inspector updates
- [ ] Test groove weight rendering

### **Integration Tests**

- [ ] Generate drums with new config
- [ ] Verify 960/1920 PPQ output
- [ ] Verify Jamstix attributes present
- [ ] Test note editing through inspector
- [ ] Test aspect view switching
- [ ] Test 64th-note precision

### **E2E Tests**

- [ ] Full generation workflow
- [ ] Edit notes in inspector
- [ ] Apply groove weights
- [ ] Filter by aspect
- [ ] Export MIDI
- [ ] Verify in DAW

---

## 📈 **Success Criteria**

### **Minimum Viable (MVP)**

- [ ] Backend generates tracks with all new attributes
- [ ] 960 PPQ resolution working
- [ ] Piano roll displays 64th grid
- [ ] Note inspector shows all controls
- [ ] Can edit velocity, timing, priority
- [ ] Aspect filtering works
- [ ] Backward compatible

### **Full Feature Complete**

- [ ] All Jamstix attributes working
- [ ] Groove weight overlay functional
- [ ] Limb view toggle (optional)
- [ ] Part type system integrated
- [ ] Power model drives intensity
- [ ] LLM generates comprehensive specs
- [ ] Professional-grade output

### **Production Ready**

- [ ] All tests passing
- [ ] Performance acceptable (< 16ms renders)
- [ ] No regressions in existing features
- [ ] Documentation complete
- [ ] User guide written

---

## 📚 **Documentation Needs**

### **Developer Docs**

- [ ] Architecture overview
- [ ] API reference (new endpoints)
- [ ] Type definitions guide
- [ ] Component usage examples
- [ ] Integration guide

### **User Docs**

- [ ] New features overview
- [ ] Note inspector guide
- [ ] Aspect view explanation
- [ ] Groove weights tutorial
- [ ] Part types reference

---

## ⏱️ **Time Estimates**

**Conservative:**
- Backend: 6-8 hours
- Frontend Types: 2-3 hours
- Piano Roll: 6-8 hours
- Integration: 4-6 hours
- Testing: 4-6 hours
- **Total: 22-31 hours (3-4 days)**

**Optimistic:**
- Backend: 4-5 hours
- Frontend Types: 1-2 hours
- Piano Roll: 4-5 hours
- Integration: 2-3 hours
- Testing: 2-3 hours
- **Total: 13-18 hours (2-3 days)**

**Realistic:** 3 days of focused work

---

## 🚀 **Next Actions**

### **Immediate (Today)**

1. **Review Package** - Read through all code
2. **Plan Integration** - Choose Option A or B
3. **Create Branch** - `feature/jamstix-integration`
4. **Start Backend** - Begin with Phase 1

### **This Week**

1. Complete backend modules
2. Complete frontend types
3. Build piano roll component
4. Wire everything together
5. Basic testing

### **Next Week**

1. Polish UI/UX
2. Comprehensive testing
3. Documentation
4. Production deployment

---

## 💡 **Key Decisions Needed**

1. **Integration Approach:** Option A (clean) or Option B (replace)?
2. **Resolution:** 960 PPQ or 1920 PPQ default?
3. **Endpoint:** New `/dcsm/generate_drums` or merge into existing?
4. **UI Mode:** Toggle between "simple" and "pro"?
5. **Limb View:** Include in v1 or defer to v2?

---

## ✨ **What This Achieves**

**Before (v2.0):**
- High-res output (960 PPQ)
- Micro-timing support
- LLM-driven performance
- Client-side re-humanization

**After (Jamstix Integration):**
- ✅ All of the above
- ✅ **64th-note resolution** (even finer)
- ✅ **Per-note control** (priority, timing, style, limb)
- ✅ **Aspect views** (groove/accent/fill)
- ✅ **Groove weights** (Jamstix-style)
- ✅ **Part types** (Jamstix-inspired)
- ✅ **Power modeling** (guide-driven)
- ✅ **Professional editor** (matches Jamstix but modern)

**Result:** DrumTracKAI becomes **the most advanced drum programming system** with:
- LLM intelligence (Jamstix lacks)
- Modern UI (Jamstix is dated)
- 64th resolution (Jamstix doesn't need)
- Complete control (matches Jamstix)
- Open architecture (Jamstix is closed)

---

## 🎯 **Status**

**Current:** Paused at 80% (v2.0 core complete)

**After Integration:** 95% complete (professional-grade system)

**Timeline:** 3-4 days to integrate + test

**Risk:** Low (can run in parallel with v2.0)

**Reward:** High (transforms into pro tool)

---

**Ready to begin integration!** 🚀

Recommend starting with backend modules (Phase 1) to establish foundation, then moving to frontend components (Phases 2-3).

---

**Created:** November 21, 2025, 4:10 PM  
**Source:** ChatGPT comprehensive Jamstix integration package  
**Status:** 🔵 **READY TO IMPLEMENT**
