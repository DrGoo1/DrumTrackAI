# ✅ Drum Builder v2.0 - Integration Checklist

**Step-by-Step Integration Guide**

Date: November 21, 2025  
Status: 🟡 **READY TO INTEGRATE**

---

## 📋 **Pre-Integration Checklist**

### **Environment Setup**

- [ ] **Python Environment Active**
  ```bash
  # Activate your environment
  source drumtrackai_env/bin/activate  # Linux/Mac
  # OR
  drumtrackai_env\Scripts\activate.ps1  # Windows
  ```

- [ ] **OpenAI Package Installed**
  ```bash
  pip install openai
  # OR specific version
  pip install openai==1.3.5
  ```

- [ ] **OpenAI API Key Set**
  ```bash
  # Add to .env file
  OPENAI_API_KEY=sk-your-key-here
  OPENAI_MODEL=gpt-4o-mini
  
  # OR set in shell
  export OPENAI_API_KEY=sk-your-key-here  # Linux/Mac
  $env:OPENAI_API_KEY="sk-your-key-here"  # Windows PowerShell
  ```

- [ ] **Verify Installation**
  ```bash
  python -c "import openai; print(f'OpenAI version: {openai.__version__}')"
  ```

---

## 🔍 **Phase 1: Locate Current System**

### **Find API Endpoint**

- [ ] **Locate drum generation endpoint**
  - [ ] Check `backend/api/generate_drums.py`
  - [ ] Check `backend/drumtrackai_api_server_clean.py`
  - [ ] Check other API files
  - [ ] Document current endpoint location: `____________________`

- [ ] **Identify current function name**
  - [ ] Document function name: `____________________`
  - [ ] Document route: `____________________`

- [ ] **Review current request format**
  - [ ] List current fields: `____________________`
  - [ ] Note any custom validation: `____________________`

- [ ] **Review current response format**
  - [ ] Document return structure: `____________________`
  - [ ] Note if MIDI export is included: `____________________`

---

## 🔧 **Phase 2: Add Imports**

### **Backend Imports**

- [ ] **Add to top of API file:**
  ```python
  from drum_generation import DrumGenerationConfig
  from drum_generation.llm_performance_spec import get_performance_spec_from_llm
  from dcsmpiano import (
      build_drumtrack_for_dcsm,
      convert_dcsm_track_to_legacy_midi_notes,
  )
  ```

- [ ] **Test imports work:**
  ```python
  python -c "from drum_generation import DrumGenerationConfig; print('✅ Imports work!')"
  ```

- [ ] **Add logging if needed:**
  ```python
  import logging
  logger = logging.getLogger(__name__)
  ```

---

## 📝 **Phase 3: Update Request Schema**

### **Add New Fields**

- [ ] **Add to request model/schema:**
  ```python
  # NEW fields to add:
  humanizeAmount: float = 0.7
  ghostNoteAmount: float = 0.7
  swingAmount: float = 0.0
  buildScope: str = "full_song"
  guideEnabled: bool = False
  guideInstrument: str = "mix"
  ```

- [ ] **Maintain backward compatibility:**
  - [ ] All new fields have defaults
  - [ ] Existing fields unchanged
  - [ ] Optional fields marked optional

- [ ] **Update validation if needed:**
  - [ ] humanizeAmount: 0.0 - 1.0
  - [ ] ghostNoteAmount: 0.0 - 1.0
  - [ ] swingAmount: 0.0 - 1.0

---

## 🏗️ **Phase 4: Add Helper Functions**

### **SongMap Summary**

- [ ] **Create `build_songmap_summary()` function:**
  ```python
  def build_songmap_summary(songmap) -> dict:
      return {
          "bars": len(songmap.bars),
          "sections": [
              {
                  "label": s.label,
                  "startBar": s.start_bar_index,
                  "endBar": s.end_bar_index,
                  "energy": s.energy,
              }
              for s in songmap.sections
          ],
      }
  ```

- [ ] **Test with real SongMap data**

### **Drummer Profile**

- [ ] **Create `get_drummer_profile()` function:**
  ```python
  def get_drummer_profile(drummer_name: str) -> dict:
      return {
          "name": drummer_name,
          "timing_tightness": 0.8,
          "ghost_note_frequency": 0.5,
          "preferred_feel": "straight",
      }
  ```

- [ ] **Optional: Load from database**
  - [ ] Query drumtrackai.db
  - [ ] Use real drummer profiles

### **Section Label**

- [ ] **Create `get_section_label()` function:**
  ```python
  def get_section_label(songmap, section_id: str) -> str:
      for s in songmap.sections:
          if s.id == section_id:
              return s.label
      return section_id.replace("_", " ").title()
  ```

---

## 🔨 **Phase 5: Integrate Builder**

### **Update Main Handler**

- [ ] **Parse request to config:**
  ```python
  config = DrumGenerationConfig.from_dict(request_data)
  ```

- [ ] **Generate or get SongMap:**
  ```python
  songmap = analyze_audio_file(audio_path)
  # OR use existing songmap
  ```

- [ ] **Generate pattern (existing logic):**
  ```python
  internal_events = your_existing_pattern_generator(...)
  # Should return list of dicts with:
  # - time_sec, length_sec, instrument_id, midi_pitch, velocity
  ```

- [ ] **Get performance spec:**
  ```python
  perf_spec = get_performance_spec_from_llm(
      cfg=config,
      section_label=get_section_label(songmap, config.sectionId),
      songmap_summary=build_songmap_summary(songmap),
      drummer_profile=get_drummer_profile(config.drummer),
  )
  ```

- [ ] **Build DCSM track:**
  ```python
  dcsm_track = build_drumtrack_for_dcsm(
      songmap=songmap,
      internal_drum_events=internal_events,
      style_id=config.style,
      performance_spec=perf_spec,
      resolution_ppq=960,
  )
  ```

- [ ] **Export to MIDI:**
  ```python
  midi_bytes = export_to_smf(dcsm_track)
  midi_b64 = base64.b64encode(midi_bytes).decode('utf-8')
  ```

- [ ] **Return response:**
  ```python
  return {
      "ok": True,
      "midi_smf_base64": midi_b64,
      "drum_track": dcsm_track.to_dict(),  # NEW
      "midi_notes": convert_dcsm_track_to_legacy_midi_notes(dcsm_track),  # OLD
  }
  ```

---

## 🧪 **Phase 6: Test Integration**

### **Unit Test**

- [ ] **Test config parsing:**
  ```python
  request = {...}
  config = DrumGenerationConfig.from_dict(request)
  assert config.style == "rock"
  ```

- [ ] **Test performance spec generation:**
  ```python
  spec = get_performance_spec_from_llm(...)
  assert "phrases" in spec
  ```

- [ ] **Test track building:**
  ```python
  track = build_drumtrack_for_dcsm(...)
  assert len(track.notes) > 0
  ```

### **Integration Test**

- [ ] **Test with sample request:**
  ```bash
  curl -X POST http://localhost:8000/api/generate-drums \
    -H "Content-Type: application/json" \
    -d @test_request.json
  ```

- [ ] **Verify response structure:**
  - [ ] Has `drum_track` field
  - [ ] Has `midi_smf_base64` field
  - [ ] Has `midi_notes` field (legacy)

- [ ] **Check drum_track contents:**
  - [ ] Has `track_id`
  - [ ] Has `resolution_ppq` (should be 960)
  - [ ] Has `notes` array
  - [ ] Has `performance_spec`

- [ ] **Check notes have micro-timing:**
  - [ ] Some notes have non-zero `microTimingMs`
  - [ ] Notes have `instrumentId`
  - [ ] Notes have proper `barIndex`, `tickInBar`

### **LLM Test**

- [ ] **Verify LLM is called:**
  - [ ] Check logs for "LLM generated performance spec"
  - [ ] OR check logs for "using default spec" (if fallback)

- [ ] **Test with humanize=false:**
  - [ ] Should use flat spec
  - [ ] All microTimingMs should be 0.0

- [ ] **Test with humanize=true:**
  - [ ] Should call LLM or analytics
  - [ ] microTimingMs should vary

---

## 📊 **Phase 7: Validation**

### **Output Validation**

- [ ] **Check MIDI resolution:**
  ```python
  assert track.resolution_ppq == 960
  ```

- [ ] **Check note count:**
  ```python
  assert len(track.notes) > 0
  assert len(track.notes) < 10000  # Sanity check
  ```

- [ ] **Check performance spec structure:**
  ```python
  spec = track.performance_spec
  assert "phrases" in spec
  assert len(spec["phrases"]) > 0
  assert "profiles" in spec["phrases"][0]
  ```

- [ ] **Check backward compatibility:**
  ```python
  legacy_notes = convert_dcsm_track_to_legacy_midi_notes(track)
  assert len(legacy_notes) == len(track.notes)
  ```

### **Quality Checks**

- [ ] **Micro-timing is reasonable:**
  - [ ] All offsets between -20ms and +20ms
  - [ ] Non-zero when humanize enabled
  - [ ] Zero when humanize disabled

- [ ] **Velocities are reasonable:**
  - [ ] All velocities between 1 and 127
  - [ ] Accents are louder than ghosts
  - [ ] Varies with intensity setting

- [ ] **Timing is musical:**
  - [ ] Notes fall on expected subdivisions
  - [ ] No notes at impossible times
  - [ ] Fills at specified locations

---

## 🎯 **Phase 8: Performance Testing**

### **LLM Performance**

- [ ] **Measure LLM call time:**
  ```python
  import time
  start = time.time()
  spec = get_performance_spec_from_llm(...)
  elapsed = time.time() - start
  print(f"LLM call took {elapsed:.2f}s")
  # Should be < 5 seconds
  ```

- [ ] **Test fallback performance:**
  ```python
  # Temporarily break OpenAI connection
  spec = get_performance_spec_from_llm(...)
  # Should still work (use analytics fallback)
  ```

### **Track Building Performance**

- [ ] **Measure build time:**
  ```python
  start = time.time()
  track = build_drumtrack_for_dcsm(...)
  elapsed = time.time() - start
  print(f"Track build took {elapsed:.2f}s")
  # Should be < 1 second
  ```

---

## 🚀 **Phase 9: Production Readiness**

### **Error Handling**

- [ ] **Test with invalid config:**
  - [ ] Missing required fields
  - [ ] Invalid enum values
  - [ ] Out of range values

- [ ] **Test with LLM failures:**
  - [ ] No API key
  - [ ] Invalid API key
  - [ ] API timeout
  - [ ] Invalid JSON response

- [ ] **Test with data failures:**
  - [ ] Empty SongMap
  - [ ] No pattern events
  - [ ] Invalid tempo values

### **Logging**

- [ ] **Add appropriate log levels:**
  - [ ] INFO: "Generating drum track for section X"
  - [ ] INFO: "LLM generated performance spec with Y phrases"
  - [ ] WARNING: "LLM unavailable, using analytics fallback"
  - [ ] ERROR: "Failed to build drum track: ..."

- [ ] **Test log output:**
  ```bash
  python -m logging --level=INFO your_api_server.py
  ```

### **Documentation**

- [ ] **Update API documentation:**
  - [ ] Document new request fields
  - [ ] Document new response fields
  - [ ] Add example requests/responses

- [ ] **Update environment setup:**
  - [ ] Document OPENAI_API_KEY requirement
  - [ ] Document optional settings

---

## ✅ **Final Verification**

### **Smoke Test**

- [ ] **Full end-to-end test:**
  1. [ ] Start server
  2. [ ] Send request with humanize=true
  3. [ ] Verify LLM called (check logs)
  4. [ ] Verify response has drum_track
  5. [ ] Verify notes have micro-timing
  6. [ ] Export MIDI and test in DAW

- [ ] **Test all generation modes:**
  - [ ] Template mode
  - [ ] AI variation mode
  - [ ] Full AI mode

- [ ] **Test all humanize settings:**
  - [ ] humanize=false (flat)
  - [ ] humanize=true, humanizeAmount=0.2 (tight)
  - [ ] humanize=true, humanizeAmount=0.8 (loose)

- [ ] **Test all build scopes:**
  - [ ] buildScope="full_song"
  - [ ] buildScope="selected_section"

### **Success Criteria**

- [ ] ✅ All tests pass
- [ ] ✅ LLM integration works
- [ ] ✅ Fallback works when LLM unavailable
- [ ] ✅ Output has high-res micro-timing
- [ ] ✅ Backward compatibility maintained
- [ ] ✅ Performance is acceptable (<5s total)
- [ ] ✅ Logs are informative
- [ ] ✅ Error handling is robust

---

## 📝 **Integration Notes**

### **Issues Encountered**

```
Issue 1: _______________________________________________
Solution: _______________________________________________

Issue 2: _______________________________________________
Solution: _______________________________________________

Issue 3: _______________________________________________
Solution: _______________________________________________
```

### **Customizations Made**

```
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________
```

### **Pending Items**

```
1. _______________________________________________
2. _______________________________________________
3. _______________________________________________
```

---

## 🎓 **Resources**

### **Documentation**

- `DRUM_BUILDER_QUICK_START.md` - Quick integration guide
- `DRUM_BUILDER_COMPLETE_ARCHITECTURE.md` - Full specification
- `DRUM_BUILDER_IMPLEMENTATION_STATUS.md` - Progress tracking
- `backend/examples/integration_example.py` - Code examples

### **Support**

- Check logs with `level=DEBUG` for detailed info
- Review example code in `backend/examples/`
- Test individual components with `backend/tests/`

---

## ✨ **Completion**

### **When All Checkboxes Are Checked:**

🎉 **INTEGRATION COMPLETE!**

You now have:
- ✅ LLM-powered performance layer
- ✅ High-resolution MIDI output
- ✅ Backward compatibility
- ✅ Professional drum humanization
- ✅ Production-ready system

**Next Steps:**
1. Deploy to staging environment
2. Test with real users
3. Monitor LLM usage/costs
4. Proceed to Phase 3 (Frontend)

---

**Date Completed:** ____________________  
**Completed By:** ____________________  
**Time Taken:** ____________________  
**Notes:** ____________________

---

**Status:** 🟡 **READY TO START**

Use this checklist to track your integration progress!
