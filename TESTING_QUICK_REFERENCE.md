# 🚀 Testing Quick Reference - Drum Builder v2.0

**One-Page Command Reference**

---

## 📋 **Pre-Flight Check**

```bash
# Check all files present
START_TESTING.bat
```

**Status:** All v2.0 files confirmed present ✅

---

## 🎯 **Three Testing Approaches**

### **Option 1: Automated Testing** ⚡ FASTEST

```bash
# Test backend API (5 minutes)
TEST_BACKEND.bat

# Test frontend compilation (2 minutes)
TEST_FRONTEND.bat
```

### **Option 2: Manual Testing** 📝 THOROUGH

```bash
# Follow step-by-step guide
# Open: MANUAL_TESTING_GUIDE.md
```

### **Option 3: Interactive Testing** 🎮 HANDS-ON

```bash
# 1. Start backend (Terminal 1)
python dcsm_backend.py

# 2. Start frontend (Terminal 2)
cd frontend
npm start

# 3. Open browser
http://localhost:3000
```

---

## 🔧 **Quick Commands**

### **Backend Testing**

```bash
# Health check
curl http://localhost:8000/

# Test generation (v2.0)
curl -X POST http://localhost:8000/api/generate-drums \
  -H "Content-Type: application/json" \
  -d @test_config.json
```

### **Frontend Testing**

```bash
# TypeScript compilation
cd frontend
npm run build

# Start dev server
npm start
```

---

## ✅ **What to Verify**

### **Backend Response**

```json
{
  "ok": true,
  "drum_track": {
    "resolution_ppq": 960,           // ← Must be 960
    "notes": [{
      "microTimingMs": -2.3,         // ← v2.0 feature
      "instrumentId": "kick",        // ← v2.0 feature
      ...
    }],
    "performance_spec": { ... }      // ← LLM output
  },
  "metadata": {
    "builder_version": "v2.0"        // ← Version check
  }
}
```

### **Frontend Components**

- [x] DrumBuilderPanelV2 renders
- [x] 3 new sliders visible (humanize, ghosts, swing)
- [x] SectionTimelineStrip shows
- [x] RehumanizePanel functional
- [x] No TypeScript errors

---

## 📊 **Critical Tests**

| Test | Command | Expected Time |
|------|---------|---------------|
| Backend Health | `curl localhost:8000` | < 1s |
| Template Gen | POST with mode=template | < 100ms |
| AI Variation | POST with mode=ai_variation | < 2s |
| TypeScript Build | `npm run build` | < 30s |
| Re-humanize | Apply preset | < 10ms |

---

## 🐛 **Common Issues**

### **Backend Won't Start**

```bash
# Check Python environment
python --version  # Should be 3.11.x

# Check dependencies
pip install -r requirements.txt

# Check port availability
netstat -ano | findstr :8000
```

### **Frontend Won't Compile**

```bash
# Install dependencies
cd frontend
npm install

# Clear cache
npm cache clean --force
rm -rf node_modules
npm install
```

### **Import Errors**

```typescript
// Check paths in tsconfig.json
{
  "compilerOptions": {
    "baseUrl": "src",
    ...
  }
}
```

---

## 📁 **Test Output Files**

After running `TEST_BACKEND.bat`:

```
test_health.json              # Health check response
test_generation.json          # Template mode result
test_generation_v2.json       # v2.0 controls result
```

**What to check:**
- `resolution_ppq: 960`
- `microTimingMs` values present
- `performance_spec` exists
- `metadata.builder_version: "v2.0"`

---

## 🎯 **5-Minute Quick Test**

**The absolute minimum test to verify v2.0 works:**

### **Step 1: Backend (2 min)**

```bash
# Start backend
python dcsm_backend.py

# In another terminal, test
curl -X POST http://localhost:8000/api/generate-drums \
  -H "Content-Type: application/json" \
  -d "{\"style\":\"rock\",\"drummer\":\"jeff_porcaro\",\"intensity\":0.7,\"variation\":0.8,\"humanize\":true,\"humanizeAmount\":0.7,\"ghostNoteAmount\":0.6,\"swingAmount\":0.2,\"generationMode\":\"template\",\"sectionId\":\"test\",\"startMeasure\":0,\"endMeasure\":4,\"tempos\":[120,120,120,120],\"timeSignature\":[4,4],\"fillLocations\":[3],\"fillType\":\"auto\",\"buildScope\":\"selected_section\"}" \
  > result.json
```

**Check:** `result.json` has `resolution_ppq: 960` ✅

### **Step 2: Frontend (3 min)**

```bash
# Compile TypeScript
cd frontend
npm run build
```

**Check:** No errors in compilation ✅

**If both pass: v2.0 is working!** 🎉

---

## 📚 **Documentation Links**

| Document | Purpose |
|----------|---------|
| `START_HERE_DRUM_BUILDER_V2.md` | Starting point |
| `TESTING_PLAN_V2.md` | Complete test plan |
| `MANUAL_TESTING_GUIDE.md` | Step-by-step tests |
| `PHASES_3_4_5_COMPLETE.md` | Implementation summary |
| `DRUM_BUILDER_V2_IMPLEMENTATION_COMPLETE.md` | Full system overview |

---

## 🚦 **Testing Status**

Update as you go:

- [ ] Backend server starts
- [ ] API endpoint responds
- [ ] v2.0 fields in response
- [ ] 960 PPQ resolution confirmed
- [ ] Frontend compiles
- [ ] Components render
- [ ] End-to-end flow works
- [ ] Re-humanization works
- [ ] Section locks work
- [ ] Performance acceptable

---

## 🎊 **Success Criteria**

**Minimum (MVP):**
- ✅ Backend responds
- ✅ Frontend compiles
- ✅ drum_track in response
- ✅ 960 PPQ resolution

**Full (Production Ready):**
- ✅ All components render
- ✅ End-to-end generation works
- ✅ Re-humanization applies
- ✅ Performance < 2s for AI
- ✅ No console errors
- ✅ All 16 tests pass

---

## 🆘 **Need Help?**

1. **Read:** `MANUAL_TESTING_GUIDE.md`
2. **Check:** `TESTING_PLAN_V2.md`
3. **Review:** `START_HERE_DRUM_BUILDER_V2.md`
4. **Debug:** Check browser console (F12)
5. **Logs:** Check backend terminal output

---

## 📞 **Quick Troubleshooting**

| Symptom | Solution |
|---------|----------|
| Port 8000 in use | `taskkill /F /IM python.exe` |
| npm errors | `npm cache clean --force` |
| TypeScript errors | Check imports in components |
| Backend crash | Check Python version (3.11) |
| No response | Check firewall/antivirus |

---

**Last Updated:** November 21, 2025  
**Status:** 🟢 **READY FOR TESTING**

**Start here:** `START_TESTING.bat` 🚀
