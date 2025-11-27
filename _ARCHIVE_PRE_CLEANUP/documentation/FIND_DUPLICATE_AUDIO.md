# Finding Duplicate Audio Sources

## Method 1: Use Debug Page

1. **Open:** http://localhost:3000/debug_audio.html
2. **Click:** "Install Play Hook"
3. **Switch to main app:** http://localhost:3000
4. **Play audio**
5. **Switch back to debug page**
6. **Click:** "List All Audio Elements"

**Look for:**
- More than 1 audio element
- Duplicate src URLs
- Multiple [MEDIA PLAY] messages

---

## Method 2: Browser Console (FASTEST)

Open the main app (http://localhost:3000), then paste this into the browser console:

```javascript
// 1. Check how many audio elements exist
console.log("Audio elements:", document.querySelectorAll("audio").length);

// 2. List all audio elements
document.querySelectorAll("audio").forEach((a, i) => {
  console.log(`#${i}:`, a.src, {paused: a.paused, volume: a.volume});
});

// 3. Install play hook to see when audio plays
if (!window.__playHook) {
  window.__playHook = true;
  const orig = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function() {
    console.log("▶️ PLAY:", this.src);
    return orig.apply(this, arguments);
  };
  console.log("✅ Play hook installed");
}
```

**Then click Play in the app**

**Expected if FIXED:** 
- `Audio elements: 1`
- Only ONE `▶️ PLAY:` message

**If BROKEN (duplicates exist):**
- `Audio elements: 2` or more
- Multiple `▶️ PLAY:` messages with same URL

---

## Method 3: Mute Test

If you see duplicates, test if they're causing distortion:

```javascript
// Mute all audio except the first one
const audios = document.querySelectorAll("audio");
audios.forEach((a, i) => {
  if (i === 0) {
    a.muted = false;
    a.volume = 0.5;
  } else {
    a.muted = true;
    a.volume = 0;
  }
});
console.log("All but first muted. If distortion is gone, duplicates were the cause.");
```

---

## Known Duplicate Sources

Based on code search, these components MAY create audio:

1. **frontend/src/audio/engine.ts** ← Main engine (FIXED)
2. **frontend/src/pages/WebDAW.tsx** ← Uses `AudioEngine` class
3. **frontend/src/components/AudioEngine.js** ← JavaScript version (?)
4. **frontend/src/audio/AudioEngine.ts** ← Scaffold version
5. **frontend/src/audio/engine/AudioEngine.ts** ← Worklet version
6. **frontend/src/components/EnhancedPianoRoll.tsx** ← Has `DrumAudioEngine` class
7. **frontend/src/midi/players.ts** ← Has Tone.Player for MIDI

**CRITICAL:** Check if you're on the `/webdaw` route. That uses a DIFFERENT AudioEngine!

---

## Quick Fix If Duplicates Found

**Option 1:** Navigate to correct page
- Make sure you're on http://localhost:3000 (WebDAWApp)
- NOT http://localhost:3000/webdaw (WebDAW scaffold)

**Option 2:** Disable unused audio components
Find the duplicate in code and comment it out/disable it

---

## Next Steps

1. Run Method 2 (console script) RIGHT NOW
2. Report how many audio elements exist
3. If > 1, we'll identify and disable the duplicate
