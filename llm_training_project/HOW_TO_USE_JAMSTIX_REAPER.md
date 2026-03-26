# 🎯 How to Use the Jamstix/Reaper Training System

## **Simple 3-Step Process**

---

## 📋 **Prerequisites Check**

Run this first to see what you need:

```bash
cd F:\DrumTracKAI_v1.1.16_Clean\llm_training_project
python activate_jamstix_system.py
```

**You need:**
1. ✅ REAPER installed ([download here](https://www.reaper.fm/download.php))
2. ✅ Jamstix plugin installed in REAPER
3. ✅ Template created (we'll do this below if needed)

---

## 🚀 **STEP 1: Create the REAPER Template** (One-time, 10 minutes)

### **A. Open REAPER**
- Launch REAPER application

### **B. Create Tracks**

**Track 1: "Jamstix Drums"**
1. Right-click in track area → Insert new track
2. Name it "Jamstix Drums"
3. Click **FX** button on the track
4. Add Jamstix plugin (VST/VST3)
5. **Important:** In Jamstix track routing:
   - Click the **Route** button
   - Add new send → Track 2
   - Set to MIDI

**Track 2: "MIDI Capture"**
1. Insert new track below Jamstix track
2. Name it "MIDI Capture"
3. Right-click track → **Input: MIDI**
4. Set input to receive from Jamstix track
5. **Important:** Set record mode:
   - Right-click record button
   - Select "Record: output (MIDI)"
6. **Arm the track** (click red record button)

### **C. Configure Project**

1. **Set Tempo:** 100 BPM (can change later)
2. **Set Time Signature:** 4/4
3. **Set Project Length:** 16 bars
4. **Configure Jamstix:**
   - Open Jamstix on Track 1
   - Set to 16 bars
   - Enable performance mode
   - Load a default preset

### **D. Save Template**

1. **File → Save Project As**
2. Navigate to: `C:\Users\dagol\ReaperTemplates\`
3. Save as: `JamstixTemplate.rpp`

**✅ Done! You only need to do this once.**

---

## 🎵 **STEP 2: Run the Automation Script** (1-2 hours for 90 examples)

### **A. Load Your Template**

1. Open REAPER
2. **File → Open Project**
3. Select: `C:\Users\dagol\ReaperTemplates\JamstixTemplate.rpp`

### **B. Load the Lua Script**

1. In REAPER: **Actions → Show action list**
2. Click **"Load ReaScript..."** button (bottom left)
3. Navigate to:
   ```
   F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\
   phase1_data_generation\reaper_automation\
   ```
4. Select: `JamstixBatchGenerator_COMPLETE.lua`
5. Click **"Run"**

### **C. Generate Data (Interactive Process)**

The script will show a dialog for each combination:

**Dialog Example:**
```
Set Jamstix preset:

Drummer: Default_Rock
Style: Rock_8th  
Preset: Simple_Verse_Chorus

[OK] [Cancel]
```

**What you do:**
1. **Open Jamstix** plugin on Track 1
2. **Set the preset** to match:
   - Change drummer/brain to "Default_Rock" (or similar)
   - Select style: "Rock_8th" (or create/save this style)
   - Set song structure to "Simple_Verse_Chorus"
3. **Click OK** in the dialog
4. **Script automatically:**
   - Records 16 bars
   - Saves MIDI file
   - Saves metadata
   - Moves to next combination

**Repeat 90 times** (for all combinations)

### **Time Estimate:**
- 1 minute per combination
- 90 combinations = ~1.5 hours
- Can pause anytime (script saves progress)

### **Output Location:**
```
F:\DrumTrackAI_Jamstix_Dataset\
├── jam_0001_Default_Rock_Rock_8th_Simple_Verse_Chorus\
│   ├── drums.mid
│   └── jamstix_meta.json
├── jam_0002_Default_Rock_Rock_16th_Simple_Verse_Chorus\
│   ├── drums.mid
│   └── jamstix_meta.json
...
└── jam_0090_Fusion_Pro_Latin_Groove_Verse_Build_Chorus\
    ├── drums.mid
    └── jamstix_meta.json
```

---

## 📊 **STEP 3: Convert to Training Data** (2 minutes)

### **A. Run the Converter**

```bash
cd F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\phase1_data_generation\corpus_builders
python jamstix_dataset_builder.py
```

**Output:**
```
======================================================================
Jamstix Dataset Builder - COMPLETE VERSION
======================================================================
Input:  F:\DrumTrackAI_Jamstix_Dataset
Output: F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\training_datasets\jamstix_pattern_train.jsonl

✓ Processed 10 combinations...
✓ Processed 20 combinations...
...

======================================================================
SUMMARY
======================================================================
✅ Processed: 90
⚠️  Skipped:   0
❌ Failed:    0
📁 Output:    jamstix_pattern_train.jsonl
📊 Size:      2.5 MB
======================================================================

✅ Success! Jamstix training data ready.
```

### **B. (Optional) Combine with Existing Data**

```bash
cd F:\DrumTracKAI_v1.1.16_Clean\llm_training_project
python combine_training_datasets.py
```

This creates a new `multitask_full_expanded.jsonl` with:
- 91,074 E-GMD patterns
- 44 Public domain
- 38 Jamstix brain
- **90 Jamstix patterns** ← NEW!
- **= 91,246 total examples**

---

## 🎯 **Quick Reference Card**

```
┌─────────────────────────────────────────────────────┐
│         JAMSTIX/REAPER QUICK REFERENCE              │
├─────────────────────────────────────────────────────┤
│ 1. CHECK STATUS                                     │
│    $ python activate_jamstix_system.py              │
│                                                     │
│ 2. GENERATE DATA                                    │
│    - Open REAPER                                    │
│    - Load template                                  │
│    - Actions → Load ReaScript                       │
│    - Run JamstixBatchGenerator_COMPLETE.lua         │
│    - Set 90 presets manually                        │
│                                                     │
│ 3. CONVERT TO TRAINING DATA                         │
│    $ python jamstix_dataset_builder.py              │
│                                                     │
│ 4. (OPTIONAL) RETRAIN LLM                           │
│    - Combine datasets                               │
│    - Use RUN_IN_COLAB_FIXED.py                      │
│    - Train on 91K+ examples                         │
└─────────────────────────────────────────────────────┘
```

---

## 💡 **Tips & Tricks**

### **Speed Up Generation**

1. **Create Preset Folders in Jamstix:**
   - Pre-save all combinations as Jamstix presets
   - Then just load preset for each dialog

2. **Batch Similar Styles:**
   - Do all "Rock" styles first
   - Then all "Funk" styles
   - Less context switching

3. **Take Breaks:**
   - Script saves after each combination
   - Can stop and resume anytime

### **Expand Beyond 90**

**Current script generates:**
- 5 drummers × 6 styles × 3 presets = 90

**To generate more:**

Edit `JamstixBatchGenerator_COMPLETE.lua`:

```lua
-- Add more drummers
local DRUMMERS = {
  "Default_Rock",
  "Funk_Master",
  "Jazz_Player",
  "Metal_Beast",
  "Fusion_Pro",
  "Classic_Rock",    -- ADD MORE
  "RnB_Groover",
  "Latin_Specialist",
}

-- Add more styles
local STYLES = {
  "Rock_8th",
  "Rock_16th",
  "Funk_16th",
  "Shuffle_HalfTime",
  "Jazz_Swing",
  "Latin_Groove",
  "Motown_16th",     -- ADD MORE
  "HipHop_Bounce",
  "Reggae_One_Drop",
}
```

**Result:** More combinations = more training data!

---

## 🔧 **Troubleshooting**

### **"Template not found"**
```bash
# Check if template exists
dir C:\Users\dagol\ReaperTemplates\JamstixTemplate.rpp

# If missing, go to STEP 1 and create it
```

### **"Lua script doesn't run"**
- Make sure file extension is `.lua` (not `.txt`)
- Load via "ReaScript" not "Action list"
- Check REAPER console for errors

### **"No MIDI recorded"**
- Check Track 2 is armed for recording
- Verify Jamstix is sending MIDI to Track 2
- Check Jamstix is actually playing

### **"Conversion script fails"**
```bash
# Make sure mido is installed
pip install mido

# Check output directory exists
dir F:\DrumTrackAI_Jamstix_Dataset
```

---

## 📈 **What to Do with Generated Data**

### **Option 1: Train a Jamstix-Focused Model**

Train an LLM just on Jamstix data:

```python
# Upload jamstix_pattern_train.jsonl to Colab
# Use RUN_IN_COLAB_FIXED.py
# Result: LLM that generates Jamstix-style patterns
```

### **Option 2: Expand Existing Training**

Combine with your 91K dataset:

```bash
python combine_training_datasets.py
# Upload multitask_full_expanded.jsonl to Colab
# Result: LLM trained on 91K+ examples including Jamstix
```

### **Option 3: Use for Pattern Analysis**

```python
# Use generated patterns to:
# - Test your backend
# - Validate Jamstix brain logic
# - Create demo patterns
# - Build pattern library
```

---

## ✅ **Success Checklist**

After completing all steps, you should have:

- [x] REAPER template saved
- [x] Jamstix configured
- [x] 90 MIDI files generated in `F:\DrumTrackAI_Jamstix_Dataset\`
- [x] `jamstix_pattern_train.jsonl` created
- [x] (Optional) Combined with existing training data
- [x] Ready to retrain LLM or use patterns

---

## 🎉 **Summary**

**The Process:**
1. **Create template** (10 min, one-time)
2. **Run automation** (1.5 hours, set 90 presets)
3. **Convert to JSONL** (2 minutes)

**The Result:**
- 90+ professional Jamstix drum patterns
- LLM training format
- Unlimited expansion capability
- $0 cost

**Next:**
- Retrain your LLM with expanded data
- Or keep generating more patterns
- Or use patterns for testing

---

**Ready to start?**

```bash
# Check what you need
python activate_jamstix_system.py

# Then follow STEP 1 above!
```

🥁 **Your Jamstix training data factory is ready!** 🏭
