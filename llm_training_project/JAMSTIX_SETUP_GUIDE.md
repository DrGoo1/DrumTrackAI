# 🥁 Jamstix + Reaper Training Data Setup Guide

## Overview

While your Colab training runs (2-3 hours), you can set up the Jamstix automation system to generate additional training data.

**What This Does:**
- Automatically generates hundreds of drum patterns from Jamstix
- Records them as MIDI in Reaper
- Converts to LLM training format
- Adds to your existing 91K training dataset

**Time:** 30-45 minutes setup, then runs automatically  
**Output:** 90+ additional training examples (expandable)

---

## 📋 What You Need

### **Software Required:**
- ✅ REAPER DAW (you have this)
- ✅ Jamstix plugin (installed in Reaper)
- ✅ Python with `mido` library

### **What's Already Built:**
- ✅ `JamstixBatchGenerator.lua` - Reaper automation script
- ✅ `jamstix_midi_to_jsonl.py` - MIDI converter
- ✅ Phase 2 brain implementation (for analyzing generated patterns)

---

## 🚀 Setup Steps

### **Step 1: Install Missing Dependencies** (2 minutes)

```bash
# Install MIDI library
pip install mido

# Verify installation
python -c "import mido; print('✅ mido installed')"
```

### **Step 2: Create Reaper Template** (10 minutes)

1. **Open REAPER**
2. **Create New Project**
3. **Add Tracks:**
   - Track 1: "Jamstix Generator"
     - Add Jamstix VST plugin
     - Set output to MIDI send → Track 2
   - Track 2: "MIDI Capture"
     - Set to receive MIDI from Track 1
     - Set record mode to "Output (MIDI)"

4. **Configure Jamstix:**
   - Open Jamstix on Track 1
   - Set to 16 bars
   - Set tempo to 100 BPM
   - Enable "Live mode" or "Perform mode"
   - Load a default preset

5. **Save Template:**
   - File → Save Project As
   - Save to: `C:\ReaperTemplates\JamstixTemplate.RPP`

### **Step 3: Update Lua Script Paths** (2 minutes)

The script at `phase1_data_generation/reaper_automation/JamstixBatchGenerator.lua` has these paths:

```lua
local TEMPLATE_PROJECT_PATH = "C:\\ReaperTemplates\\JamstixTemplate.RPP"
local OUTPUT_BASE = "F:\\DrumTracKAI_v1.1.16_Clean\\llm_training_project\\phase1_data_generation\\output\\jamstix_generated"
```

✅ Paths look correct! But verify:
- Template exists at that path
- Output directory will be created automatically

### **Step 4: Configure Jamstix Presets** (10 minutes)

The script will cycle through these combinations:

**Drummers (5):**
- Default Rock Drummer
- Funk Master
- Jazz Player
- Metal Beast
- Fusion Pro

**Styles (6):**
- Rock 8th
- Rock 16th
- Funk 16th
- Shuffle Half-Time
- Jazz Swing
- Latin Groove

**Song Presets (3):**
- Simple Verse-Chorus
- Intro-Verse-Chorus-Bridge
- Verse-Build-Chorus

**Total:** 5 × 6 × 3 = 90 combinations

**To configure:**
1. Open Jamstix in your template
2. Save presets matching these names
3. Or edit the Lua script to match your existing preset names

---

## 🔧 Completing the Lua Script

The current script has 2 TODOs we need to address:

### **TODO 1: Set Jamstix Presets Programmatically**

**Current issue:** Line 150-153
```lua
-- TODO: Set Jamstix preset via TrackFX_SetPreset or parameter automation
```

**Two options:**

#### **Option A: Manual Preset Change** (Easier, recommended)
Run the script in "pause mode" where you manually change presets:

