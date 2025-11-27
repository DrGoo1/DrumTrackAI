# Quick Test: Section Display on Timeline

## Steps to Test

1. **Refresh browser** at localhost:3000
2. **Open Console (F12)** - Keep it open!
3. **Upload audio file** - Use "Upload Audio" button
4. **Click "🎯 Analyze Song Structure"** button (right panel)
5. **Watch console logs carefully**

---

## What You Should See in Console:

### Step 1: After clicking Analyze
```
🎯 SongMap loaded!
  Global BPM: 161.5
  Meter: 4/4
  Bars: 161
  Sections: 36
  Section labels: (36) ["intro", "verse", "verse", ...]
  Per-bar tempo: min=215.3, max=215.3, avg=215.3
✅ Created 36 UI sections with tempo data
```

### Step 2: Timeline Re-render
```
🎨 Timeline rendering 36 sections
📐 Canvas dimensions: 1200x400, maxDuration: 240.4s
🎯 First section: "intro" at 0.0px to 31.4px (width: 31.4px), tempo: 215.33205
```

---

## Diagnosis Based on Logs:

### ✅ If you see ALL three log groups:
**Status:** Everything is working!  
**Expected:** Sections should be visible on timeline  
**If not visible:** Canvas rendering issue - check browser zoom/DevTools positioning

### ⚠️ If you only see Step 1 logs:
**Problem:** Sections created but Timeline not re-rendering  
**Possible causes:**
- Timeline component not receiving updated sections prop
- useEffect dependencies not triggering
**Try:** Change BPM value manually to force re-render

### ❌ If you don't see "✅ Created X UI sections":
**Problem:** Section conversion failed  
**Check:** 
```javascript
// In console, type:
sections
// Should show array with objects containing start, end, label, tempo
```

### ❌ If you don't see any logs:
**Problem:** Analysis not completing  
**Check:**
- Network tab for `/dcsm/analyze_full` request status
- Backend is running on port 8000
- No errors in console

---

## Manual Debug Commands

Type these in browser console:

```javascript
// 1. Check if sections exist
console.log('Sections:', sections.length, sections);

// 2. Check if tracks exist
console.log('Tracks:', tracks.length, tracks);

// 3. Check first section details
if (sections[0]) {
  const s = sections[0];
  console.log({
    label: s.label,
    start: s.start,
    end: s.end,
    tempo: s.tempo,
    hasLabel: !!s.label,
    hasTempo: !!s.tempo
  });
}

// 4. Force Timeline to re-render by changing BPM
setBpm(bpm + 1);
```

---

## Common Issues & Fixes

### Issue: "Canvas dimensions: 0x0"
**Cause:** Canvas not properly sized  
**Fix:** Check CSS, ensure Timeline container has height/width

### Issue: "First section width: 0.0px"
**Cause:** Section start/end times are identical  
**Fix:** Backend not returning proper time ranges

### Issue: Timeline shows but sections don't
**Cause:** Section width < 60px (minimum for label display)  
**Note:** Very short sections won't show labels by design  
**Check:** Look at `width: X.Xpx` in the log - should be > 60

### Issue: Sections appear but no labels/tempo
**Cause:** 
- Label text might be off-screen (check Y positions: 15, 28, 42)
- Font not loading
**Try:** Zoom browser in/out to force canvas redraw

---

## Expected Visual Result

After successful analysis, timeline header should show:

```
┌──────────┬────────────┬───────────┬──────────┐
│  INTRO   │   VERSE    │  CHORUS   │  VERSE   │
│  ♩=161   │   ♩=163    │  ♩=160    │  ♩=162   │
│ 4 bars   │  8 bars    │  6 bars   │  8 bars  │
└──────────┴────────────┴───────────┴──────────┘
```

With color coding:
- Orange = Intro
- Blue = Verse
- Green = Chorus
- Purple = Bridge
- Red = Outro

---

## If Still Not Working

1. **Take screenshot** of browser with console open
2. **Copy console output** (all logs)
3. **Check these values:**
   ```javascript
   {
     sectionsCount: sections.length,
     tracksCount: tracks.length,
     firstSectionStart: sections[0]?.start,
     firstSectionEnd: sections[0]?.end,
     canvasExists: !!document.querySelector('canvas')
   }
   ```

Then we can debug further based on what's shown!
