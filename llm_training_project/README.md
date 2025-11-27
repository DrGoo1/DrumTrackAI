# 🎓 DrumTracKAI LLM Training Project

**Separate from main app - focused on training a specialized drummer LLM**

## 🎯 **Project Goals**

Build a large-scale LLM that understands:
1. **Pattern Generation** - Create drum patterns (notes, rhythms, fills)
2. **Performance Specs** - Microtiming, velocities, human feel
3. **Drum Reasoning** - Why drummers play what they play

## 📚 **Training Data Sources**

### **1. Jamstix Manual (Permission Granted)**
- Complete manual extraction and curation
- Humanization logic, fill rules, limb constraints
- Groove weights, timing rules, drummer models

### **2. Public Domain Drum Instruction**
- Pre-1928 drum method books
- George B. Bruce - Drummer's and Fifer's Guide (1869)
- US Army marching band manuals
- Rudiment explanations and stickings

### **3. University Drumline Packets**
- Free educational PDFs
- Technique descriptions
- Accent patterns, stick heights

### **4. Jamstix-Generated Training Data**
- Automated Reaper + Jamstix batch generation
- Thousands of MIDI examples with metadata
- Different drummers, styles, song structures

### **5. E-GMD Dataset** (Already Extracted)
- 91,074 professional drummer MIDI performances
- Enhanced features (ghost notes, swing, fills, etc.)

## 🏗️ **Architecture**

### **Phase 1: Data Generation (Jamstix as Teacher)**
```
Reaper + Jamstix → MIDI + Metadata → Training JSONL
```

### **Phase 2: Brain Implementation**
```
Jamstix Concepts → DrumTracKAI Code → LLM Training Examples
```

## 📁 **Project Structure**

```
llm_training_project/
├── README.md (this file)
├── phase1_data_generation/
│   ├── reaper_automation/
│   │   ├── JamstixBatchGenerator.lua
│   │   ├── JamstixTemplate.RPP
│   │   └── README.md
│   ├── corpus_builders/
│   │   ├── jamstix_midi_to_jsonl.py
│   │   ├── jamstix_manual_curator.py
│   │   ├── public_domain_extractor.py
│   │   └── egmd_to_llm_format.py
│   └── output/
│       ├── jamstix_generated/
│       ├── manual_curated/
│       └── combined/
├── phase2_brain_implementation/
│   ├── jamstix_attributes.py
│   ├── performance_spec_generator.py
│   ├── limb_constraint_engine.py
│   ├── fill_designer.py
│   └── groove_weight_calculator.py
├── training_datasets/
│   ├── pattern_train.jsonl
│   ├── performance_train.jsonl
│   ├── explanation_train.jsonl
│   └── multitask_full.jsonl
├── prompts/
│   ├── pattern_generation_template.txt
│   ├── performance_spec_template.txt
│   └── explanation_template.txt
└── docs/
    ├── TRAINING_DATA_SOURCES.md
    ├── PHASE1_GUIDE.md
    ├── PHASE2_GUIDE.md
    └── LLM_TRAINING_GUIDE.md
```

## 🚀 **Quick Start**

### **Phase 1: Generate Jamstix Training Data**
```bash
# 1. Setup Reaper template with Jamstix
# 2. Run Lua script in Reaper
# 3. Convert to JSONL
python phase1_data_generation/corpus_builders/jamstix_midi_to_jsonl.py
```

### **Phase 2: Implement Brain in DrumTracKAI**
```python
from phase2_brain_implementation.jamstix_attributes import enrich_events
from phase2_brain_implementation.performance_spec_generator import generate_spec

# Enrich drum events with Jamstix-style attributes
enriched_events = enrich_events(pattern, style="rock", drummer="bonham")

# Generate performance spec
spec = generate_spec(enriched_events, feel="laid_back", intensity=0.9)
```

## 📊 **Training Data Format**

All training data uses consistent JSONL format:
```json
{
  "task": "generate_pattern",
  "input": {...},
  "output": {...},
  "meta": {...}
}
```

## 🎯 **Target LLM Behaviors**

1. ✅ **Micro-timing reasoning**
2. ✅ **Fill design**
3. ✅ **Ghost note logic**
4. ✅ **Rudiment-aware fills**
5. ✅ **Limb-aware playability**
6. ✅ **Stylistic imitation**
7. ✅ **Pattern generation**
8. ✅ **High-level arrangement**

## 📈 **Expected Outcomes**

- **Large specialized drummer LLM**
- **Pattern generation capability**
- **Performance spec generation**
- **Drum reasoning explanations**
- **Style-aware composition**
- **Human-like feel application**

## ⚖️ **Legal & Licensing**

- ✅ **Jamstix manual:** Permission granted by author
- ✅ **Public domain books:** Pre-1928, freely available
- ✅ **University packets:** Educational use allowed
- ✅ **E-GMD:** Research dataset
- ✅ **Generated data:** Original work

## 🔗 **Integration with Main App**

This project is **separate** but feeds into main DrumTracKAI:
- Trained LLM models → imported into main app
- Brain concepts → implemented in main codebase
- No Jamstix binary dependency

---

**Status:** 🟢 **Ready to Build**  
**Next:** Run Phase 1 data generation scripts
