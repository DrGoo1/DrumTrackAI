# 🧪 Next Steps - Testing Drum Builder v2.0

**Quick Testing Guide for Phases 1 & 2**

---

## ⚡ **Quick Test (5 minutes)**

### **1. Start Backend**

```powershell
# Activate environment (if using virtual environment)
.\drumtrackai_env\Scripts\activate.ps1

# Start server
python dcsm_backend.py
```

### **2. Test Basic Generation**

```powershell
# Save this as test_request.json
{
  "sectionId": "verse_1",
  "startMeasure": 0,
  "endMeasure": 3,
  "tempos": [120, 120, 120, 120],
  "timeSignature": [4, 4],
  "style": "rock",
  "drummer": "jeff_porcaro",
  "intensity": 0.7,
  "variation": 0.5,
  "generationMode": "full_ai",
  "humanize": true,
  "fillLocations": [],
  "fillType": "auto"
}

# Test with curl (or PowerShell equivalent)
curl -X POST http://localhost:8000/api/generate-drums `
  -H "Content-Type: application/json" `
  -d @test_request.json
```

### **3. Check Response**

**Success indicators:**
- ✅ Status 200 OK
- ✅ `"ok": true` in response
- ✅ `"midi_notes"` array present
- ✅ `"metadata"` object present

**v2.0 indicators (if modules loaded):**
- ✅ `"drum_track"` object present
- ✅ `"metadata.builder_version": "v2.0"`
- ✅ Notes have `microTimingMs` field

---

## 🔬 **Detailed Testing**

### **Test 1: Verify Import**

```powershell
python -c "from drum_generation_api import generate_drums; print('✅ API imports OK')"
python -c "from backend.drum_generation import DrumGenerationConfig; print('✅ v2.0 modules OK')"
```

**Expected:**
```
✅ API imports OK
✅ v2.0 modules OK
```

**If fails:**
```
Check backend/ directory exists
Check __init__.py files present
Check Python path includes current directory
```

### **Test 2: Test with LLM (Optional)**

```powershell
# Set API key
$env:OPENAI_API_KEY = "sk-your-key-here"
$env:OPENAI_MODEL = "gpt-4o-mini"

# Same test as Quick Test above
```

**Check logs for:**
```
INFO:drum_generation.llm_performance_spec:LLM generated performance spec with X phrases
```

### **Test 3: Test Fallback**

```powershell
# Temporarily rename backend folder
Rename-Item backend backend_disabled

# Run test again
curl -X POST http://localhost:8000/api/generate-drums ...

# Should still work with legacy generation
# Check: "metadata.builder_version": "v1.1_legacy"

# Restore
Rename-Item backend_disabled backend
```

### **Test 4: Test Different Settings**

**High Humanize:**
```json
{
  ...
  "humanize": true,
  "humanizeAmount": 0.9,
  "ghostNoteAmount": 0.8,
  "swingAmount": 0.5
}
```

**No Humanize:**
```json
{
  ...
  "humanize": false
}
```

Compare `microTimingMs` values in responses.

---

## 📊 **Test Matrix**

| Test | Expected Result | Status |
|------|----------------|--------|
| Basic request works | 200 OK, has midi_notes | ⬜ |
| v2.0 modules import | No import errors | ⬜ |
| v2.0 response format | Has drum_track field | ⬜ |
| Micro-timing applied | Non-zero microTimingMs | ⬜ |
| LLM integration | Logs show LLM call | ⬜ |
| Fallback works | Still works without backend/ | ⬜ |
| Different drummers | Each produces output | ⬜ |
| Different styles | Each produces output | ⬜ |
| Humanize on/off | microTimingMs changes | ⬜ |

---

## 🎯 **Success Criteria**

### **Minimum (Must Work)**

- [x] Backend starts without errors
- [ ] `/api/generate-drums` returns 200 OK
- [ ] Response has `midi_notes` array
- [ ] Response has `metadata` object

### **Optimal (v2.0 Working)**

- [ ] Response has `drum_track` object
- [ ] `metadata.builder_version` is "v2.0"
- [ ] Notes have `microTimingMs` field
- [ ] Different humanize settings produce different results

### **Advanced (LLM Working)**

- [ ] Logs show LLM API call
- [ ] `performance_spec` included in response
- [ ] Per-instrument profiles visible
- [ ] Fallback works if LLM unavailable

---

## 🐛 **Common Issues**

### **Issue: Import Error**

```
ModuleNotFoundError: No module named 'backend.drum_generation'
```

**Fix:**
```powershell
# Check files exist
Test-Path backend\drum_generation\__init__.py
Test-Path backend\dcsmpiano\__init__.py

# Add to Python path
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"
```

### **Issue: OpenAI Error**

```
WARNING: OpenAI not available
```

**Fix:**
```powershell
pip install openai
```

This is optional - system works without it.

### **Issue: Legacy Fallback**

```
"metadata.builder_version": "v1.1_legacy"
```

**Not an error!** System is working, just using fallback.

**To get v2.0:**
- Ensure backend/ modules exist
- Check import errors in logs
- Restart server

---

## 📝 **Test Checklist**

### **Before Testing**

- [ ] Backend server started
- [ ] No import errors in console
- [ ] Port 8000 accessible

### **Basic Tests**

- [ ] Test 1: Basic request → 200 OK
- [ ] Test 2: Response has required fields
- [ ] Test 3: Different drummers work
- [ ] Test 4: Different styles work

### **v2.0 Tests**

- [ ] Test 5: `drum_track` present in response
- [ ] Test 6: `microTimingMs` varies with humanize
- [ ] Test 7: Logs show "Using Drum Builder v2.0"

### **LLM Tests (Optional)**

- [ ] Test 8: OpenAI API key set
- [ ] Test 9: LLM call succeeds
- [ ] Test 10: `performance_spec` in response

### **Fallback Tests**

- [ ] Test 11: Works without OpenAI
- [ ] Test 12: Works without backend/ modules
- [ ] Test 13: Always returns valid JSON

---

## 🎓 **Understanding Results**

### **v2.0 Response Example**

```json
{
  "ok": true,
  "drum_track": {
    "track_id": "abc-123",
    "resolution_ppq": 960,
    "notes": [
      {
        "id": "note-1",
        "barIndex": 0,
        "tickInBar": 0,
        "velocity": 110,
        "microTimingMs": -2.3,  // ← v2.0 feature!
        "instrumentId": "kick",
        "isAccent": true
      }
    ]
  },
  "midi_notes": [...],  // Legacy format
  "metadata": {
    "builder_version": "v2.0",
    "generation_time_ms": 234.5,
    "performance_from_llm": true,
    "resolution_ppq": 960
  }
}
```

### **Legacy Response Example**

```json
{
  "ok": true,
  "midi_notes": [
    {
      "time": 0.0,
      "note": 36,
      "velocity": 110,
      "drum": "kick"
    }
  ],
  "metadata": {
    "builder_version": "v1.1_legacy",
    "generation_time_ms": 12.3
  }
}
```

---

## 🚀 **After Testing**

### **If All Tests Pass**

✅ **Ready for Phase 3!**

Proceed to frontend integration:
1. Create TypeScript types
2. Update API client
3. Add new UI controls

### **If Some Tests Fail**

Check which category:
- **Import errors** → Fix Python path
- **API errors** → Check server logs
- **LLM errors** → Optional, system still works
- **Response errors** → Report issue

### **If All Tests Fail**

1. Check server is running: `http://localhost:8000/healthz`
2. Check logs for errors
3. Try legacy endpoint first
4. Review `INTEGRATION_CHECKLIST.md`

---

## 📞 **Getting Help**

### **Check Logs**

```powershell
# Enable debug logging
$env:LOG_LEVEL = "DEBUG"
python dcsm_backend.py
```

Look for:
- Import errors
- API call failures
- LLM responses

### **Check Documentation**

- `DRUM_BUILDER_QUICK_START.md` - Integration guide
- `PHASE_2_COMPLETE_API_INTEGRATION.md` - API details
- `INTEGRATION_CHECKLIST.md` - Step-by-step

### **Check Examples**

- `backend/examples/integration_example.py`
- `backend/tests/test_drum_builder_v2.py`

---

## ✨ **Success!**

When tests pass, you have:

✅ Working Drum Builder v2.0 backend  
✅ LLM integration (optional)  
✅ High-resolution MIDI output  
✅ Backward compatible API  
✅ Ready for frontend integration  

**Next:** Phase 3 - Frontend Integration

---

**🧪 Happy Testing!**

Date: November 21, 2025  
For: DrumTracKAI v1.1.16.3
