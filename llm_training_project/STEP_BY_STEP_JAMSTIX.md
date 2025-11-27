# 🎯 Jamstix Training System - Step-by-Step Guide

## ✅ You're Already 80% There!

Everything is ready except REAPER. Here's exactly what to do:

---

## 🚀 **Quick Start (15 minutes)**

### **Step 1: Install REAPER** (5 minutes)

1. **Download REAPER:**
   - Go to: https://www.reaper.fm/download.php
   - Click "Download Reaper" (Windows 64-bit)
   - File: ~15 MB

2. **Install:**
   - Run installer
   - Accept defaults
   - No restart needed

3. **Trial is Fully Functional:**
   - 60-day free trial
   - All features work
   - $60 for personal license (optional)

---

### **Step 2: Open Your Jamstix Template** (2 minutes)

**You already have the template saved!**

1. **Open REAPER**
2. **File → Open Project**
3. Navigate to: `C:\Users\dagol\ReaperTemplates\`
4. Open: `JamstixTemplate.rpp`

**That's it!** Your template loads with:
- Track 1: Jamstix plugin
- Track 2: MIDI Capture

---

### **Step 3: Run the Automation Script** (1 minute)

1. **In REAPER, click: Actions → Show action list**
2. **Click: "Load ReaScript..."** (bottom left)
3. **Navigate to:**
   ```
   F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\
   phase1_data_generation\reaper_automation\
   ```
4. **Select:** `JamstixBatchGenerator_COMPLETE.lua`
5. **Click "Run"**

---

### **Step 4: Generate Jamstix Data** (1-2 hours automatic)

The script will:

1. **Prompt you for each combination:**
   ```
   Set Jamstix preset:
   Drummer: Default_Rock
   Style: Rock_8th
   Preset: Simple_Verse_Chorus
   
   [OK] [Cancel]
   ```

2. **You set the Jamstix preset manually** (in the plugin)
3. **Click OK**
4. **Script records MIDI automatically** (16 bars)
5. **Saves to:** `F:\DrumTrackAI_Jamstix_Dataset\jam_0001_...`
6. **Repeats for all 90 combinations**

---

### **Step 5: Convert to Training Data** (2 minutes)

After generating some Jamstix examples:

```bash
cd F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\phase1_data_generation\corpus_builders
python jamstix_dataset_builder.py
```

**Output:** `jamstix_pattern_train.jsonl` (ready for LLM training!)

---

## 🎓 **Alternative: If You Don't Have REAPER Yet**

### **You Can Still Use the Jamstix Brain Right Now!**

The **Phase 2 Jamstix Brain** works independently:

```bash
cd F:\DrumTracKAI_v1.1.16_Clean\llm_training_project
python test_jamstix_integration.py
```

This gives you:
- ✅ Limb assignment
- ✅ Priority calculation
- ✅ Micro-timing
- ✅ Conflict detection
- ✅ DCSM integration

**No REAPER needed for Phase 2!**

---

## 📊 **What Each Phase Does**

### **Phase 1: Data Generation** (Requires REAPER)
```
REAPER + Jamstix 
    ↓
Record MIDI (automated)
    ↓
Convert to JSONL
    ↓
LLM Training Data
```

### **Phase 2: Brain Logic** (Works NOW)
```
Any Pattern Events
    ↓
Jamstix Brain Enrichment
    ↓
Limbs, Priority, Timing, etc.
    ↓
DCSM DrumTrack
```

---

## 🔄 **Full Workflow (When You Have REAPER)**

### **One-Time Setup:**
1. Install REAPER (5 min)
2. Open template (already exists)
3. Load Lua script (1 min)

### **Generate Data:**
```
Run Lua script 
→ Set 90 Jamstix presets manually (1-2 hours)
→ Script records all automatically
→ 90 MIDI files + metadata saved
```

### **Convert & Use:**
```bash
python jamstix_dataset_builder.py
# Creates: jamstix_pattern_train.jsonl

# Optional: Combine with existing data
python combine_training_datasets.py
# Now have 91K+ examples!

# Re-train LLM on expanded dataset
# (Use RUN_IN_COLAB_FIXED.py again)
```

---

## 💡 **Recommended Path**

### **Option A: Use Phase 2 Now (No REAPER)**
```bash
python test_jamstix_integration.py
```
- Test the brain logic
- Integrate with your backend
- Works with existing patterns

### **Option B: Get REAPER + Generate Data**
1. Install REAPER (free trial)
2. Run automation (generates 90 examples)
3. Expand your training dataset
4. Re-train LLM with more data

### **Option C: Both!**
- Use Phase 2 brain immediately
- Install REAPER when you want more training data
- They work together or separately

---

## 🎯 **Fastest Way to See Results**

**Right now (2 minutes):**
```bash
cd F:\DrumTracKAI_v1.1.16_Clean\llm_training_project
python test_jamstix_integration.py
```

You'll see:
```
✅ Attribute enrichment working!
✅ Limb conflicts detected and resolved!
✅ DCSM track building complete!
✅ Performance specs generated!
```

**With REAPER (15 minutes setup):**
1. Download REAPER: https://www.reaper.fm/download.php
2. Install (5 min)
3. Open template (already exists)
4. Run script
5. Generate unlimited training data

---

## 🆘 **Troubleshooting**

### **"I don't have Jamstix plugin"**
- Phase 2 brain works WITHOUT Jamstix plugin
- Phase 1 data generation needs Jamstix
- Alternative: Use existing 91K training data

### **"REAPER says template not found"**
```bash
# Check if template exists:
dir C:\Users\dagol\ReaperTemplates\JamstixTemplate.rpp

# If missing, create it:
# See: JAMSTIX_COMPLETE_SETUP.md section 2
```

### **"Lua script not loading"**
- Make sure file extension is `.lua`
- Load via: Actions → Show action list → Load ReaScript
- Not: Actions → Load action list

---

## 📁 **File Locations Reference**

```
Template:
  C:\Users\dagol\ReaperTemplates\JamstixTemplate.rpp

Lua Script:
  F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\
  phase1_data_generation\reaper_automation\
  JamstixBatchGenerator_COMPLETE.lua

Output:
  F:\DrumTrackAI_Jamstix_Dataset\
  jam_0001_Default_Rock_Rock_8th_Simple_Verse_Chorus\

Converter:
  F:\DrumTracKAI_v1.1.16_Clean\llm_training_project\
  phase1_data_generation\corpus_builders\
  jamstix_dataset_builder.py
```

---

## ✅ **Summary**

**You have 2 complete systems:**

1. **Jamstix Brain (Phase 2)** ✅ Works NOW
   - No REAPER needed
   - Test: `python test_jamstix_integration.py`

2. **Jamstix Data Generator (Phase 1)** ⚠️ Needs REAPER
   - Install REAPER (free trial)
   - Generate unlimited training data
   - 15 minutes to set up

**Recommended:** Test Phase 2 now, install REAPER later if you want more data!

---

## 🚀 **Quick Commands**

```bash
# Check system status
python activate_jamstix_system.py

# Test Jamstix brain (works now!)
python test_jamstix_integration.py

# Convert Jamstix MIDI to training data (after REAPER generation)
python phase1_data_generation/corpus_builders/jamstix_dataset_builder.py
```

---

**Ready to go!** Pick your path and start! 🎉
