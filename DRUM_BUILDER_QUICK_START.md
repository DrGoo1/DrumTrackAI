# 🚀 Drum Builder Quick Start Guide

**Get the new drum builder running in minutes**

---

## ✅ **What's Already Done**

✅ Complete backend foundation (Phase 1)  
✅ LLM integration with comprehensive prompts  
✅ High-resolution MIDI output  
✅ Performance layer with micro-timing  
✅ Backward compatibility maintained  

---

## 🎯 **Quick Integration (5 Steps)**

### **Step 1: Set OpenAI API Key**

```bash
# Add to your .env file
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
USE_LLM_PERFORMANCE=true
```

### **Step 2: Find Your Current Drum Generation Endpoint**

Look for this file (approximate location):
```
backend/api/generate_drums.py
OR
backend/drumtrackai_api_server_clean.py
```

Find the function that handles `/api/generate-drums` POST requests.

### **Step 3: Add Imports**

At the top of your API file, add:

```python
from drum_generation import DrumGenerationConfig
from drum_generation.llm_performance_spec import get_performance_spec_from_llm
from dcsmpiano import build_drumtrack_for_dcsm, convert_dcsm_track_to_legacy_midi_notes
```

### **Step 4: Update API Handler**

Replace or wrap your existing handler:

```python
@app.post("/api/generate-drums")
async def generate_drums(request: dict):
    """
    Generate drum track with LLM-powered performance layer.
    """
    
    # 1. Parse request to DrumGenerationConfig
    config = DrumGenerationConfig.from_dict(request)
    
    # 2. Get SongMap (your existing analysis)
    songmap = analyze_audio_file(audio_path)  # Your existing function
    
    # 3. Get drummer profile (simple version)
    drummer_profile = {
        "timing_tightness": 0.85,
        "ghost_note_frequency": 0.6,
        "preferred_feel": "laid_back",
        "style_specialties": [config.style],
    }
    
    # 4. Build SongMap summary for LLM
    songmap_summary = {
        "bars": len(songmap.bars),
        "sections": [
            {
                "label": s.label,
                "startBar": getattr(s, 'start_bar_index', 0),
                "endBar": getattr(s, 'end_bar_index', 0),
                "energy": getattr(s, 'energy', 0.5),
            }
            for s in getattr(songmap, 'sections', [])
        ],
    }
    
    # 5. Generate pattern (your existing function)
    internal_events = generate_drum_pattern(
        config=config,
        songmap=songmap,
    )  # Returns list of dicts with time_sec, instrument_id, etc.
    
    # 6. Get performance spec from LLM
    section_label = config.sectionId.replace("_", " ").title()
    
    perf_spec = get_performance_spec_from_llm(
        cfg=config,
        section_label=section_label,
        songmap_summary=songmap_summary,
        drummer_profile=drummer_profile,
    )
    
    # 7. Build high-resolution DCSM track
    dcsm_track = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id=config.style,
        performance_spec=perf_spec,
        resolution_ppq=960,
    )
    
    # 8. Generate SMF for plugin (your existing function or new one)
    midi_bytes = export_to_smf(dcsm_track)
    midi_b64 = base64.b64encode(midi_bytes).decode('utf-8')
    
    # 9. Return both formats
    return {
        "ok": True,
        "status_message": "Generated drum track with LLM performance",
        "midi_smf_base64": midi_b64,
        "drum_track": dcsm_track.to_dict(),  # NEW high-res format
        "midi_notes": convert_dcsm_track_to_legacy_midi_notes(dcsm_track),  # OLD format
        "metadata": {
            "style": config.style,
            "drummer": config.drummer,
            "humanized": config.humanize,
            "performance_from_llm": True,
        }
    }
```

### **Step 5: Update Request Schema**

Make sure your request accepts these fields:

```python
# Existing fields (you already have these)
sectionId: str
startMeasure: int
endMeasure: int
tempos: List[float]
timeSignature: Tuple[int, int]
style: str
drummer: str
intensity: float
variation: float
generationMode: str
humanize: bool
fillLocations: List[int]
fillType: str

# NEW fields (add these)
humanizeAmount: float = 0.7
ghostNoteAmount: float = 0.7
swingAmount: float = 0.0
buildScope: str = "full_song"
guideEnabled: bool = False
guideInstrument: str = "mix"
```

---

## 🧪 **Test It**

### **Simple Test Request**

```bash
curl -X POST http://localhost:8000/api/generate-drums \
  -H "Content-Type: application/json" \
  -d '{
    "sectionId": "verse_1",
    "startMeasure": 0,
    "endMeasure": 7,
    "tempos": [120, 120, 120, 120, 120, 120, 120, 120],
    "timeSignature": [4, 4],
    "style": "rock",
    "drummer": "jeff_porcaro",
    "intensity": 0.7,
    "variation": 0.5,
    "generationMode": "full_ai",
    "humanize": true,
    "humanizeAmount": 0.7,
    "ghostNoteAmount": 0.6,
    "swingAmount": 0.2,
    "fillLocations": [7],
    "fillType": "auto",
    "buildScope": "full_song"
  }'
```

### **Check Response**

You should see:
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
        "velocity": 110,
        "instrumentId": "kick",
        "microTimingMs": -2.3,
        ...
      }
    ],
    "performance_spec": {
      "styleId": "rock",
      "globalFeel": "straight",
      "phrases": [...]
    }
  }
}
```

---

## 🔧 **Troubleshooting**

### **Issue: "OpenAI not available"**

**Solution:**
```bash
pip install openai
# OR
pip install openai==1.3.5
```

### **Issue: "Module not found: drum_generation"**

**Solution:**
```bash
# Make sure you're in the right directory
cd backend

# Check __init__.py files exist
ls drum_generation/__init__.py
ls dcsmpiano/__init__.py

# Add to Python path if needed
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### **Issue: "SongMap has no attribute 'bars'"**

**Solution:** Your SongMap structure might be different. Check your actual SongMap structure:
```python
print(type(songmap))
print(dir(songmap))
print(songmap.__dict__)
```

Then adjust the code accordingly.

### **Issue: "LLM returns invalid JSON"**

**Solution:** The system automatically falls back to analytics-based defaults. Check logs:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

You'll see:
```
INFO:drum_generation.llm_performance_spec:LLM generated performance spec with 1 phrases
```

Or fallback message:
```
WARNING:drum_generation.llm_performance_spec:LLM call failed, using default spec
```

---

## 📊 **Verify It's Working**

### **Check 1: LLM Called**

Look in your logs for:
```
INFO:drum_generation.llm_performance_spec:LLM generated performance spec with X phrases
```

### **Check 2: Micro-Timing Applied**

Check response notes have `microTimingMs`:
```json
{
  "notes": [
    {
      "microTimingMs": -3.2,  // ✅ This should be non-zero
      ...
    }
  ]
}
```

### **Check 3: Performance Spec Included**

Check response has full spec:
```json
{
  "performance_spec": {
    "phrases": [
      {
        "profiles": [
          {
            "instrumentId": "snare_center",
            "microTiming": {
              "subdivisionOffsetsMs": [-5, 2, -3, ...],  // ✅ Should have values
              ...
            }
          }
        ]
      }
    ]
  }
}
```

---

## 🎨 **Frontend Integration (Coming Soon)**

Once backend is working, frontend integration is straightforward:

```typescript
// 1. Update request type
interface DrumGenRequest {
  // ...existing fields...
  humanizeAmount: number;
  ghostNoteAmount: number;
  swingAmount: number;
  buildScope: "full_song" | "selected_section";
}

// 2. Update API call
const response = await fetch("/api/generate-drums", {
  method: "POST",
  body: JSON.stringify(request),
});

const data = await response.json();

// 3. Use new drum_track format
const track: DrumTrackForDCSM = data.drum_track;
pianoRoll.loadTrack(track);
```

---

## 🎯 **Next Steps After Integration**

1. ✅ Verify LLM integration works
2. ✅ Test with different styles/drummers
3. ✅ Test humanize on/off
4. ✅ Test different humanize amounts
5. 🔲 Add frontend controls (Phase 3)
6. 🔲 Add section locking (Phase 4)
7. 🔲 Add client-side re-humanization (Phase 5)

---

## 💡 **Pro Tips**

### **Tip 1: Start Simple**

Test with humanize=false first to ensure pattern generation works:
```json
{
  "humanize": false,
  ...
}
```

Then enable humanize and watch the logs.

### **Tip 2: Compare Outputs**

Generate the same section twice:
1. Once with `humanize: false`
2. Once with `humanize: true, humanizeAmount: 0.8`

Compare `microTimingMs` values in notes.

### **Tip 3: Cache API Key**

```bash
# Add to your shell profile
export OPENAI_API_KEY=sk-your-key-here
```

### **Tip 4: Use Cheaper Model First**

```bash
# For testing
OPENAI_MODEL=gpt-4o-mini  # Cheap, fast

# For production
OPENAI_MODEL=gpt-4o  # Best quality
```

---

## 📞 **Support**

If you encounter issues:

1. Check `DRUM_BUILDER_IMPLEMENTATION_STATUS.md` for detailed component info
2. Check `DRUM_BUILDER_COMPLETE_ARCHITECTURE.md` for full specification
3. Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## ✅ **Success Checklist**

- [ ] OpenAI API key set in environment
- [ ] Imports added to API file
- [ ] API handler updated
- [ ] Request schema updated
- [ ] Test request returns `drum_track` object
- [ ] Notes have non-zero `microTimingMs` values
- [ ] `performance_spec` included in response
- [ ] Logs show "LLM generated performance spec"
- [ ] Legacy `midi_notes` still works
- [ ] MIDI export still works

**When all checked:** ✅ **Backend integration complete!**

---

**Status:** 🟢 **READY TO INTEGRATE**

**Estimated Time:** 30 minutes - 2 hours depending on your current API structure.
