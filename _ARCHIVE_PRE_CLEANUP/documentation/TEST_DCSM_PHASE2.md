# Testing Phase 2 Bar Layer in DCSM Interface

**Date:** November 20, 2025  
**Feature:** Bar-level analysis with meter detection in WebDAW

---

## 🎯 **What We're Testing**

The new **Phase 2 bar layer** features integrated into the DCSM web interface:

1. ✅ Bar detection with per-bar tempo
2. ✅ Meter detection (4/4 vs 3/4)
3. ✅ Enhanced sections with bar indices
4. ✅ Energy and spectral data per section
5. ✅ Intelligent section labeling

---

## 🚀 **Step-by-Step Testing Guide**

### **Prerequisites**
- ✅ Backend running on port 8000 (already started)
- ✅ Frontend running on port 3000 (already started)
- ✅ Rust audio-core built (`target\release\audio-core.exe`)
- ✅ Test audio files in `uploads/` folder

---

### **Test 1: Upload & Auto-Analysis**

1. **Open DCSM in browser:**
   - Navigate to: http://localhost:3000
   - Or use the browser preview window

2. **Open Browser Console (F12):**
   - This is where Phase 2 data will be logged
   - Look for console.log messages

3. **Upload Audio File:**
   - Click "Upload" or drag-drop an audio file
   - Or use existing file from uploads folder
   - Recommended: `1763570509314-Peg_No_Drums.mp3` (already tested)

4. **Watch for Auto-Analysis:**
   - After upload completes, auto-sectionize should trigger
   - Watch console for logs

---

### **Expected Console Output:**

```javascript
🎯 SongMap loaded!
  Global BPM: 161.5
  Meter: 4/4              // ← NEW! Phase 2
  Bars: 161               // ← NEW! Phase 2
  Sections: 36
  Section labels: (36) ["intro", "verse", "verse", ...]

  Per-bar tempo: min=215.3, max=215.3, avg=215.3  // ← NEW! Phase 2
```

---

### **Test 2: Verify Section Data**

**In Console, inspect sections:**

```javascript
// Type this in console to see section data:
console.table(sections.map(s => ({
  label: s.label,
  start: s.start.toFixed(1),
  end: s.end.toFixed(1),
  energy: s.energy?.toFixed(2),
  startBar: s.startBarIndex,    // ← NEW! Phase 2
  endBar: s.endBarIndex,        // ← NEW! Phase 2
  barCount: s.barCount          // ← NEW! Phase 2
})))
```

**Expected Output:**
| label | start | end | energy | startBar | endBar | barCount |
|-------|-------|-----|--------|----------|--------|----------|
| intro | 0.0   | 6.3 | 0.07   | 0        | 4      | 5        |
| verse | 6.3   | 13.0| 0.07   | 4        | 8      | 5        |
| ...   | ...   | ... | ...    | ...      | ...    | ...      |

---

### **Test 3: Verify SongMap State**

**In Console, check songMap:**

```javascript
// Type this to see the full SongMap:
songMap
```

**Expected Structure:**
```javascript
{
  duration: 240.4,
  globalBpmEstimate: 161.5,
  meter: [4, 4],           // ← NEW! Phase 2
  bars: [                  // ← NEW! Phase 2
    {
      index: 0,
      start_time: 0.371,
      end_time: 1.486,
      meter: [4, 4],
      tempo_bpm: 215.3,    // ← Per-bar tempo!
      beat_times: [0.371, 0.743, 1.114, 1.486],
      confidence: 0.517
    },
    // ... 160 more bars
  ],
  sections: [...],
  beatTimes: [...]
}
```

---

### **Test 4: Check Network Requests**

1. **Open Network tab** in DevTools (F12)
2. **Filter by "analyze_full"**
3. **Upload a file** or trigger analysis
4. **Verify the request:**
   - URL: `/dcsm/analyze_full?key=<filename>`
   - Status: 200 OK
   - Response should contain: `bars`, `meter`, `sections`

5. **Inspect Response:**
   - Click on the request
   - Go to "Response" tab
   - Verify JSON structure matches expected format

---

### **Test 5: UI Behavior**

**Check these UI elements:**

- [ ] **BPM Display** - Should update to detected BPM (161.5)
- [ ] **Waveform** - Should render correctly
- [ ] **Sections** - Should appear as colored regions
- [ ] **Timeline** - Should show section boundaries
- [ ] **Section Labels** - Should show intro/verse/chorus/outro

**Note:** Bar visualization may not be implemented yet - that's Phase 3

---

### **Test 6: Test with Different Audio**

Try these test scenarios:

#### **Scenario A: Known 4/4 Song**
- Upload a rock/pop song
- Expected meter: [4, 4]
- Should have consistent bars

#### **Scenario B: Known 3/4 Song (if available)**
- Upload a waltz or 3/4 song
- Expected meter: [3, 4]
- Bars should group by 3 beats

#### **Scenario C: Tempo Change Song**
- Upload song with tempo changes
- Check if per-bar tempo varies
- Look for different tempo_bpm values in bars

---

## 🐛 **Troubleshooting**

### **Issue: No console output**

**Solution:**
```javascript
// Manually trigger analysis in console:
handleAnalyzeFull('1763570509314-Peg_No_Drums.mp3')
```

### **Issue: 404 error on analyze_full**

**Check:**
1. Backend is running latest code
2. `/dcsm/analyze_full` endpoint exists
3. Restart backend if needed

### **Issue: No bars in response**

**Check:**
1. Audio file has clear beats
2. Minimum 8 beats required
3. Check Rust CLI output directly

### **Issue: Meter always [4,4]**

**Expected:** Algorithm prefers 4/4 by default
- Need very clear 3/4 pattern to detect
- Check with known 3/4 songs

---

## 📊 **Success Criteria**

### **Phase 2 Features Working:**
- ✅ `songMap` state populated in React
- ✅ `bars` array present with >0 bars
- ✅ Each bar has `tempo_bpm` field
- ✅ `meter` detected (not [0,0])
- ✅ Sections have `startBarIndex`, `endBarIndex`, `barCount`
- ✅ Console logs show bar/meter data
- ✅ Network request returns full SongMap

### **Integration Working:**
- ✅ Upload triggers auto-analysis
- ✅ No errors in console
- ✅ UI updates with detected data
- ✅ BPM changes to detected value
- ✅ Sections render on timeline

---

## 🧪 **Advanced Testing**

### **Test Drum Planning (Console)**

```javascript
// Import the function (if available in scope):
// import { buildDrumPlanFromSongMap } from './types/songMap';

// Or test the logic manually:
const drumPlan = songMap.bars.map((bar, idx) => {
  const section = songMap.sections.find(s => 
    s.startBarIndex <= idx && idx <= s.endBarIndex
  );
  
  return {
    barIndex: idx,
    sectionLabel: section?.label || 'unknown',
    tempo: bar.tempo_bpm,
    energy: section?.energy || 0.5
  };
});

console.table(drumPlan.slice(0, 20));
```

This shows how bar data maps to drum generation strategy.

---

## 📝 **Test Results Template**

```
=== DCSM Phase 2 Test Results ===
Date: Nov 20, 2025
Tester: [Your Name]

File Tested: _________________
Duration: ______ seconds

Results:
[ ] SongMap loaded successfully
[ ] Bars detected: _____ bars
[ ] Meter detected: [__, __]
[ ] Sections detected: _____ sections
[ ] Per-bar tempo varies: Yes / No
[ ] Console logs appear correctly
[ ] UI updates with data
[ ] No errors in console

Notes:
_________________________________
_________________________________
_________________________________

Status: PASS / FAIL
```

---

## 🎯 **Next Steps After Testing**

If all tests pass:
1. ✅ Mark Phase 2 as validated
2. 📊 Document accuracy metrics
3. 🎨 Design bar visualization for UI
4. 🥁 Integrate drum planning with generation
5. 🚀 Move to Phase 3 (self-similarity, ML labeling)

If tests fail:
1. 🐛 Document specific failures
2. 🔍 Debug with Rust CLI directly
3. 🔧 Fix issues in backend/frontend
4. 🔄 Re-test until passing

---

## 📚 **Reference Files**

- `test_phase2.py` - Python API test script
- `songmap_test.json` - Example SongMap output
- `PHASE2_BAR_LAYER_COMPLETE.md` - Implementation details
- `COMPLETE_INTEGRATION_GUIDE.md` - Full documentation

---

## ✅ **Quick Checklist**

Before testing:
- [ ] Backend running (port 8000)
- [ ] Frontend running (port 3000)
- [ ] Rust binary built
- [ ] Test audio available
- [ ] Browser console open (F12)

During testing:
- [ ] Upload audio file
- [ ] Check console for SongMap logs
- [ ] Verify bars array populated
- [ ] Check meter detection
- [ ] Inspect section bar indices
- [ ] Test network request

After testing:
- [ ] Document results
- [ ] Save test data
- [ ] Report any issues
- [ ] Celebrate success! 🎉

---

**Ready to test! Open http://localhost:3000 and follow the steps above.** 🚀
