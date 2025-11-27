# 🎵 Section Manager Guide - DrumTracKAI DCSM Studio

## ✅ **NEW FEATURE: Interactive Section Editor**

The Section Manager allows you to **finalize your song arrangement** before generating drum patterns.

---

## 📍 **Where to Find It**

After uploading audio in DCSM Studio, the Section Manager appears as a **right sidebar panel**.

**Location:** http://localhost:3000 → Upload Audio → Right sidebar

---

## 🎯 **Core Features**

### **1. View All Sections**
Each section card shows:
- **Label** (Intro, Verse, Chorus, Bridge, Outro)
- **Start/End Time** (formatted as MM:SS)
- **Duration** (in musical bars)
- **Density** (0-100% - how busy the drums will be)
- **Fill In/Out** checkboxes

### **2. Rename Sections** ✏️
- Click the **✏️ pencil icon**
- Type new name (e.g., "Pre-Chorus", "Solo", "Breakdown")
- Press **Enter** or click outside to save

### **3. Adjust Density** 🎚️
- Select a section to expand its controls
- Use the **Density slider** (0-100%)
- Higher = busier drums, Lower = simpler patterns

**Typical Values:**
- **Intro:** 40-60% (sparse)
- **Verse:** 60-70% (moderate)
- **Chorus:** 80-90% (busy)
- **Bridge:** 50-70% (varies)
- **Outro:** 30-50% (fade out)

### **4. Split Sections** ✂️
**To divide a section into two parts:**
1. Select the section
2. Move playhead to desired split point
3. Click **"✂️ Split Here"**
4. Section splits at nearest beat (beat-aligned)

**Use Case:** Long verse that needs a pattern change halfway through

### **5. Merge Sections** 🔗
**To combine two adjacent sections:**
1. Select a section
2. Click **"🔗 Merge →"**
3. Combines with the next section

**Use Case:** Two short sections that should have the same drum pattern

### **6. Delete Sections** 🗑️
- Click **🗑️ trash icon** on any section
- Confirms before deleting
- Cannot delete last remaining section

### **7. Add Manual Sections** ➕
- Click **"+ Add Section"** button at top
- Creates 4-bar section at current playhead position
- Customize from there

---

## 🎵 **Musical Tips**

### **Fill In / Fill Out Checkboxes**
- **Fill In** = drum fill leading INTO this section (typically 1 bar)
- **Fill Out** = drum fill leading OUT of this section (typically 1 bar)

**Best Practices:**
- ✅ Fill In: Start of chorus (energy boost)
- ✅ Fill Out: End of verse (transition)
- ❌ Don't use: Very first section (Fill In)
- ❌ Don't use: Very last section (Fill Out)

### **Section Naming Strategy**
Use clear, descriptive names:
- ✅ "Intro Drums" 
- ✅ "Verse 1" / "Verse 2"
- ✅ "Pre-Chorus"
- ✅ "Chorus"
- ✅ "Bridge"
- ✅ "Guitar Solo"
- ✅ "Outro Fade"

---

## 🔄 **Workflow: From Upload to Pattern Generation**

### **Step 1: Upload Audio**
```
1. Go to DCSM Studio
2. Click "Upload Audio"
3. Select your backing track (MP3/WAV)
4. Wait for waveform to appear
```

### **Step 2: Auto-Detect Sections**
```
1. Click "Align to [filename]" button
2. System detects sections using:
   - Spectral flux analysis
   - Energy valleys
   - Beat alignment (4-bar minimum)
   - Automatic labeling (intro/verse/chorus/outro)
```

### **Step 3: Review & Edit Sections** ⭐ **THIS IS THE NEW PART**
```
Right sidebar Section Manager appears:

✅ Check section boundaries
   - Do they align with musical phrases?
   - Are transitions on the beat?

✅ Rename sections as needed
   - "section" → "Verse 1"
   - "verse" → "Pre-Chorus"

✅ Split long sections
   - Verse 1a / Verse 1b
   - Different patterns needed

✅ Merge short sections
   - Combine if same pattern wanted

✅ Adjust density per section
   - Intro: Lower (50%)
   - Chorus: Higher (85%)
   - Bridge: Medium (65%)

✅ Set Fill In/Out appropriately
```

### **Step 4: Generate Patterns** (Coming Next!)
```
1. Click "Generate Pattern" for each section
2. System creates drum patterns matching:
   - Section length (exact bars)
   - Density setting
   - Fill In/Out preferences
   - Detected BPM (161.5 in your case)
3. Patterns appear in Piano Roll
4. Edit notes if needed
5. Export to MIDI
```

---

## 🎹 **Keyboard Shortcuts** (Planned)

| Action | Shortcut |
|--------|----------|
| Split at playhead | `S` |
| Delete selected | `Delete` |
| Rename selected | `F2` |
| Next section | `→` |
| Previous section | `←` |

*(Not yet implemented - future enhancement)*

---

## 🐛 **Troubleshooting**

### **"Split Here" button is disabled**
- Playhead must be INSIDE the selected section boundaries
- Move playhead between section start and end time

### **Sections overlap after editing**
- This shouldn't happen (split/merge respects boundaries)
- If it does, use manual time adjustment (future feature)
- For now: Delete and recreate section

### **Changes not saving**
- Changes save immediately to local state
- Click "Save" button to persist to backend session
- Use "Load" to restore previous session

### **Sections not appearing after "Align to [file]"**
- Check browser console for errors
- Verify BPM is detected (shown in top bar)
- Minimum section length is 4 bars - song might be too short

---

## 📊 **Technical Details**

### **Section Alignment**
- All section boundaries snap to **nearest beat**
- Minimum section length: **4 bars** (16 beats)
- Maximum section length: **16 bars** (64 beats)
- Split points snap to beat grid

### **Beat Calculation**
```
secPerBeat = 60 / BPM
secPerBar = secPerBeat * 4  (assumes 4/4 time)
bars = duration / secPerBar
```

Example at 161.5 BPM:
- 1 beat = 0.372 seconds
- 1 bar = 1.488 seconds
- 4 bars = 5.95 seconds
- 8 bars = 11.9 seconds

---

## 🚀 **Next Steps**

Once you've finalized your sections:

1. **Save Session** (preserves sections + settings)
2. **Generate Patterns** (next feature to build)
3. **Edit in Piano Roll**
4. **Export MIDI**

---

## 💡 **Pro Tips**

1. **Start with auto-detection** - it's pretty accurate
2. **Review every section** - rename for clarity
3. **Think about density progression** - chorus should be busier than verse
4. **Use fills strategically** - not every transition needs one
5. **Split complex sections** - different patterns for verse A vs B
6. **Merge simple sections** - if pattern should stay the same
7. **Name consistently** - makes MIDI export cleaner

---

## 🎵 **Example: Rock Song Structure**

```
Section 1: Intro (4 bars, 50% density, no fill in, fill out)
Section 2: Verse 1 (8 bars, 65% density, fill in, fill out)
Section 3: Chorus (8 bars, 85% density, fill in, fill out)
Section 4: Verse 2 (8 bars, 65% density, fill in, fill out)
Section 5: Chorus (8 bars, 85% density, fill in, fill out)
Section 6: Bridge (8 bars, 70% density, fill in, fill out)
Section 7: Chorus (8 bars, 90% density, fill in, no fill out)
Section 8: Outro (4 bars, 40% density, fill in, no fill out)
```

**Total: 56 bars of perfectly aligned drum patterns!**

---

**Your sections are now ready for drum pattern generation! 🥁**
