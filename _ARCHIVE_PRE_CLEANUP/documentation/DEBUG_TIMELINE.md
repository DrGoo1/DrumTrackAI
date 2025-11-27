# Timeline Display Debugging Guide

## Problem: Sections Not Showing on Timeline

### Quick Checks:

1. **Open Browser Console (F12)**
   - Look for console logs after clicking "Analyze Song Structure"
   - Should see:
     ```
     🎯 SongMap loaded!
       Global BPM: 161.5
       Meter: 4/4
       Bars: 161
       Sections: 36
       Section labels: ["intro", "verse", ...]
     ✅ Created 36 UI sections with tempo data
     ```

2. **Check Sections Array in Console**
   Type this in console:
   ```javascript
   sections
   ```
   Should show array of section objects with:
   - `start`, `end`, `label`, `tempo`

3. **Check Timeline Canvas**
   - Timeline should have sections in header area
   - If canvas is blank, sections might not be rendering

### Common Issues:

#### Issue 1: Sections Array Empty
**Symptom:** `sections.length = 0` in console  
**Fix:** Analysis didn't complete successfully
- Check network tab for `/dcsm/analyze_full` request
- Check for errors in console

#### Issue 2: Sections Have No Data
**Symptom:** Sections exist but have `start: 0, end: 0`  
**Fix:** Backend didn't return proper section data
- Test backend directly: `test_phase2.py`

#### Issue 3: Timeline Not Re-rendering
**Symptom:** Sections exist in state but don't appear visually  
**Fix:** Force re-render
- Try changing BPM value to trigger redraw
- Check if `tracks.length > 0` (timeline needs audio loaded)

### Manual Test:

```javascript
// In browser console after uploading audio:

// 1. Check if tracks loaded
tracks

// 2. Trigger analysis manually
handleAutoSectionize(tracks[0].key)

// 3. Wait a few seconds, then check sections
sections

// 4. Check timeline dimensions
const canvas = document.querySelector('canvas');
console.log(`Canvas: ${canvas.width}x${canvas.height}`);

// 5. Force redraw by changing BPM
setBpm(162)
```

### Expected Timeline Rendering:

The Timeline component should:
1. Draw header area (50px tall)
2. Draw sections as colored rectangles in header
3. Draw section labels with 3 lines:
   - Line 1 (y=15): Section name (white)
   - Line 2 (y=28): Tempo (yellow, `♩=161`)
   - Line 3 (y=42): Bar count (gray)

### Debug Output:

Add this to console after analysis:
```javascript
// Check first section details
const s = sections[0];
console.log({
  label: s.label,
  start: s.start,
  end: s.end,
  tempo: s.tempo,
  duration: s.end - s.start
});

// Calculate where it should appear
const maxDuration = Math.max(...tracks.map(t => t.seconds));
const canvasWidth = 800; // typical width
const startX = (s.start / maxDuration) * canvasWidth;
const endX = (s.end / maxDuration) * canvasWidth;
console.log(`Section should appear at X: ${startX} to ${endX} (width: ${endX-startX}px)`);
```

### If Still Not Working:

1. **Check Canvas Exists:**
   ```javascript
   document.querySelector('canvas')?.getContext('2d')
   ```

2. **Check Timeline Rendering Loop:**
   - Open Timeline.tsx
   - Add console.log in useEffect
   - Verify it's being called after sections change

3. **Check Section Minimum Width:**
   - Timeline only shows labels if `(endX - startX) > 60`
   - Very short sections won't show labels

4. **Try Simplest Test:**
   ```javascript
   // Manually set one test section
   setSections([{
     id: 'test-1',
     start: 0,
     end: 10,
     label: 'TEST',
     tempo: 120,
     density: 0.5,
     fillIn: false,
     fillOut: false
   }]);
   ```

### Success Criteria:

✅ Sections array populated (length > 0)  
✅ Each section has start, end, label, tempo  
✅ Timeline canvas exists and has width/height  
✅ Audio track loaded (tracks.length > 0)  
✅ No errors in console  
✅ Colored rectangles visible in timeline header  
✅ Section names visible as white text  
✅ Tempo values visible as yellow text  

---

## Quick Fix Test

Reload the page and:
1. Upload audio file
2. Wait for waveform to appear
3. Open console (F12)
4. Click "🎯 Analyze Song Structure"
5. Watch console for logs
6. Sections should appear immediately

If sections still don't show, paste the console output here for debugging.
