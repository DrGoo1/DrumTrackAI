# 🧪 Manual Testing Guide - Drum Builder v2.0

**Step-by-Step Testing Instructions**

Date: November 21, 2025

---

## 🎯 **Testing Overview**

This guide will walk you through testing all major features of Drum Builder v2.0.

**Estimated Time:** 30-45 minutes  
**Prerequisites:** Backend and frontend running

---

## 📝 **Pre-Test Checklist**

Before starting, ensure:

- [ ] Python environment activated
- [ ] Backend server running (port 8000)
- [ ] Frontend dev server running (port 3000)
- [ ] Browser opened to http://localhost:3000
- [ ] Browser console open (F12) for debugging

---

## 🚀 **Quick Start**

### **Option 1: Automated Backend Test**

```bash
# Run automated backend tests
TEST_BACKEND.bat
```

This will:
- Check if backend is running
- Test health endpoint
- Test generation endpoint
- Test v2.0 controls
- Save results to JSON files

### **Option 2: Automated Frontend Test**

```bash
# Run automated frontend tests
TEST_FRONTEND.bat
```

This will:
- Check TypeScript compilation
- Verify all v2.0 files exist
- Check file sizes
- Report any issues

---

## 🧪 **Manual Test Suite**

### **Test 1: Backend API - Basic Generation** ⭐ CRITICAL

**Purpose:** Verify the backend API works with v2.0 parameters

**Steps:**

1. Open a command prompt
2. Run this curl command:

```bash
curl -X POST http://localhost:8000/api/generate-drums ^
  -H "Content-Type: application/json" ^
  -d "{\"style\":\"rock\",\"drummer\":\"jeff_porcaro\",\"intensity\":0.7,\"variation\":0.8,\"humanize\":true,\"humanizeAmount\":0.7,\"ghostNoteAmount\":0.6,\"swingAmount\":0.2,\"generationMode\":\"template\",\"sectionId\":\"test\",\"startMeasure\":0,\"endMeasure\":4,\"tempos\":[120,120,120,120],\"timeSignature\":[4,4],\"fillLocations\":[3],\"fillType\":\"auto\",\"buildScope\":\"selected_section\"}"
```

**Expected Result:**

```json
{
  "ok": true,
  "drum_track": {
    "track_id": "...",
    "resolution_ppq": 960,
    "notes": [
      {
        "id": "...",
        "barIndex": 0,
        "tickInBar": 0,
        "velocity": 100,
        "midiPitch": 36,
        "instrumentId": "kick",
        "microTimingMs": -2.3,  // ← v2.0 feature
        ...
      }
    ],
    "performance_spec": { ... }  // ← LLM output
  },
  "midi_notes": [ ... ],  // ← Legacy format
  "metadata": {
    "builder_version": "v2.0"  // ← Version indicator
  }
}
```

**Validation:**
- [ ] Response has `ok: true`
- [ ] `drum_track` exists
- [ ] `resolution_ppq` is 960
- [ ] Notes have `microTimingMs` field
- [ ] Notes have `instrumentId` field
- [ ] `performance_spec` exists
- [ ] `metadata.builder_version` is "v2.0"

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 2: Frontend TypeScript - Compilation** ⭐ CRITICAL

**Purpose:** Verify TypeScript code compiles without errors

**Steps:**

1. Open command prompt
2. Navigate to `web-frontend/`
3. Run: `npm run build`

**Expected Result:**

```
Creating an optimized production build...
Compiled successfully!
```

**Validation:**
- [ ] No TypeScript errors
- [ ] No missing import errors
- [ ] Build folder created
- [ ] All types resolve

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 3: UI Component - DrumBuilderPanelV2** ⭐ CRITICAL

**Purpose:** Verify enhanced drum builder panel renders and functions

**Steps:**

1. Open http://localhost:3000 in browser
2. Navigate to drum builder section
3. Look for DrumBuilderPanelV2 component

**Expected Result:**

Visual elements visible:
- Style selector (6 buttons: Rock, Funk, Jazz, Latin, Metal, Pop)
- Drummer dropdown
- Intensity slider (0-100%)
- Variation slider (0-100%)
- **NEW:** Humanize section with:
  - Humanize checkbox
  - Humanize Amount slider (0-100%)
  - Ghost Notes slider (0-100%)
  - Swing Amount slider (0-100%)
- Advanced options collapse button
- Generate button

**Validation:**
- [ ] Component renders without errors
- [ ] All controls visible
- [ ] Sliders move smoothly
- [ ] Dropdowns work
- [ ] Generate button clickable
- [ ] v2.0 badge visible

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 4: UI Component - SectionTimelineStrip**

**Purpose:** Verify section timeline displays and lock controls work

**Steps:**

1. Open drum builder interface
2. Look for section timeline component
3. Click on different sections
4. Click lock/unlock buttons

**Expected Result:**

- Sections displayed horizontally
- Color-coded by type (intro, verse, chorus, etc.)
- Click to select section
- Lock button toggles
- Status indicators show (✓ has drums, 🔒 locked)

**Validation:**
- [ ] Timeline renders
- [ ] Sections clickable
- [ ] Lock buttons work
- [ ] Selection highlights
- [ ] Colors correct

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 5: UI Component - RehumanizePanel**

**Purpose:** Verify re-humanization controls work

**Steps:**

1. Generate a drum track first
2. Find RehumanizePanel component
3. Try preset buttons
4. Adjust sliders
5. Click Apply button

**Expected Result:**

- 6 preset buttons visible (tight, natural, loose, etc.)
- 5 adjustment sliders:
  - Micro-timing (0-100%)
  - Feel (-100 to +100%)
  - Velocity variation (0-100%)
  - Swing (0-100%)
  - Ghost note density (0-100%)
- Apply button
- Reset button
- Groove controls (collapsible)

**Validation:**
- [ ] Component renders
- [ ] Presets clickable
- [ ] Sliders adjust values
- [ ] Apply button works
- [ ] Reset button works

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 6: End-to-End - Generate Drums with v2.0 Controls** ⭐ CRITICAL

**Purpose:** Full flow from UI to backend to display

**Steps:**

1. Select a section in timeline
2. Choose style: "Rock"
3. Choose drummer: "Jeff Porcaro"
4. Set intensity: 70%
5. Set variation: 80%
6. Enable humanize
7. Set humanize amount: 70%
8. Set ghost notes: 60%
9. Set swing: 20%
10. Click "Generate Drums"

**Expected Result:**

- Loading indicator shows
- Request sent to backend
- Response received
- Drum track displays in piano roll
- Notes show micro-timing offsets
- Console shows no errors

**Validation:**
- [ ] Generate button triggers request
- [ ] Backend responds within 2 seconds
- [ ] Track displays correctly
- [ ] Micro-timing visible (if piano roll supports it)
- [ ] No console errors
- [ ] Track has 960 PPQ resolution

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 7: Re-humanization - Apply Preset** ⭐ CRITICAL

**Purpose:** Verify client-side re-humanization works

**Steps:**

1. Generate a drum track
2. Open RehumanizePanel
3. Click "natural" preset
4. Click "Apply"
5. Observe changes

**Expected Result:**

- Track updates immediately (< 10ms)
- No backend call made (check Network tab)
- Micro-timing values change
- Velocity values adjust
- Piano roll updates
- Original preserved for reset

**Validation:**
- [ ] Preset applies instantly
- [ ] No network request
- [ ] Track modified
- [ ] Reset works
- [ ] Performance < 10ms

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 8: Section Locking**

**Purpose:** Verify section locks prevent regeneration

**Steps:**

1. Generate drums for "Verse 1"
2. Click "Lock" button on Verse 1
3. Change generation settings
4. Generate drums again (with full song scope)

**Expected Result:**

- Verse 1 shows locked indicator (🔒)
- Verse 1 track preserved
- Other sections regenerated
- Generate button disabled when locked section selected

**Validation:**
- [ ] Lock button toggles state
- [ ] Locked indicator shows
- [ ] Locked section preserved
- [ ] Other sections regenerate
- [ ] UI updates correctly

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 9: Utility Functions**

**Purpose:** Verify utility functions work correctly

**Steps:**

1. Open browser console
2. Import utilities
3. Test functions

**Test Commands:**

```javascript
// Import (adjust path as needed)
import {
  ticksToSeconds,
  secondsToTicks,
  analyzeTrack
} from './utils/drumTrackUtils';

// Test time conversion
console.log(ticksToSeconds(1920, 120, 960));  // Should be 2.0
console.log(secondsToTicks(2.0, 120, 960));  // Should be 1920

// Test track analysis (after generating a track)
const stats = analyzeTrack(yourTrack);
console.log('Stats:', stats);
```

**Expected Result:**

- No errors in console
- Correct values returned
- Functions execute quickly

**Validation:**
- [ ] Time conversion accurate
- [ ] Statistics correct
- [ ] No runtime errors
- [ ] Performance acceptable

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 10: Error Handling**

**Purpose:** Verify graceful error handling

**Test Cases:**

**10a. Backend Down**

Steps:
1. Stop backend server
2. Try to generate drums
3. Observe error message

Expected:
- [ ] User-friendly error message
- [ ] No crash
- [ ] Can retry after backend starts

**10b. Invalid Configuration**

Steps:
1. Send invalid config (e.g., intensity: 200)
2. Observe handling

Expected:
- [ ] Validation catches error
- [ ] Clear error message
- [ ] UI remains stable

**10c. Network Timeout**

Steps:
1. Simulate slow network
2. Generate drums
3. Wait for timeout

Expected:
- [ ] Timeout handled gracefully
- [ ] Error message shown
- [ ] Can retry

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

## 📊 **Performance Testing**

### **Test 11: Response Times**

**Measure generation times for different modes:**

| Mode | Target | Your Result |
|------|--------|-------------|
| Template | < 100ms | ___ ms |
| AI Variation | < 1s | ___ ms |
| Full AI | < 3s | ___ ms |
| Re-humanization | < 10ms | ___ ms |

**How to Measure:**

```javascript
// In browser console
console.time('generation');
// ... click generate ...
console.timeEnd('generation');
```

**Validation:**
- [ ] All times within acceptable range
- [ ] No significant lag
- [ ] UI remains responsive

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

### **Test 12: Memory Usage**

**Monitor memory during operation:**

1. Open Chrome DevTools → Performance → Memory
2. Take heap snapshot before generation
3. Generate multiple tracks
4. Take heap snapshot after
5. Check for leaks

**Validation:**
- [ ] No memory leaks detected
- [ ] Memory usage reasonable (< 200MB frontend)
- [ ] Garbage collection working

**Status:** ⚪ Not Tested | ✅ Passed | ❌ Failed

---

## 🐛 **Bug Tracking**

### **Issues Found**

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | | | |
| 2 | | | |
| 3 | | | |

**Severity Levels:**
- 🔴 Critical: Blocks usage
- 🟡 High: Major functionality broken
- 🔵 Medium: Feature partially works
- 🟢 Low: Minor cosmetic issue

---

## ✅ **Test Summary**

### **Overall Results**

| Category | Passed | Failed | Not Tested |
|----------|--------|--------|------------|
| Backend API | 0 | 0 | 2 |
| Frontend TypeScript | 0 | 0 | 1 |
| UI Components | 0 | 0 | 3 |
| End-to-End | 0 | 0 | 1 |
| Re-humanization | 0 | 0 | 1 |
| Section Locks | 0 | 0 | 1 |
| Utilities | 0 | 0 | 1 |
| Error Handling | 0 | 0 | 3 |
| Performance | 0 | 0 | 2 |
| **TOTAL** | **0** | **0** | **16** |

### **Sign-Off**

- [ ] All critical tests passed
- [ ] All high-priority tests passed
- [ ] Known issues documented
- [ ] Performance acceptable
- [ ] Ready for production

**Tester:** _________________  
**Date:** _________________  
**Signature:** _________________

---

## 📝 **Notes**

Use this space for observations, suggestions, and feedback:

```
[Your notes here]
```

---

**Next Steps:**
1. Complete all tests
2. Document any issues
3. Fix critical bugs
4. Retest
5. Move to production deployment

Good luck! 🚀
