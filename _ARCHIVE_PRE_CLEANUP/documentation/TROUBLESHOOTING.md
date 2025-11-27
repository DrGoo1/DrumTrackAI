# 🔧 DrumTracKAI Troubleshooting Guide

**Common Issues and Solutions**

---

## 🐍 Python / Backend Issues

### **Problem: `ImportError: No module named 'librosa'` or `numpy`**

**Cause:** Wrong Python version or missing dependencies

**Solution:**
```bash
# 1. Check Python version (MUST be 3.11.x)
python --version

# 2. Activate virtual environment
.\drumtrackai_env\Scripts\activate

# 3. Install exact versions
pip install numpy==1.24.3 librosa==0.10.1 scipy==1.10.1
```

**Why 3.11.x?** Librosa 0.10.1 has LLVM dependencies that break on Python 3.12+

---

### **Problem: `ModuleNotFoundError: No module named 'drummer_mapping_service'`**

**Cause:** Running from wrong directory

**Solution:**
```bash
# Always run from project root
cd f:\DrumTracKAI_v1.1.16_Clean
python dcsm_backend.py
```

---

### **Problem: Backend starts but drummer list is empty**

**Cause:** `drummer_mapping_service.py` not loaded

**Solution:**
```bash
# 1. Check import in dcsm_backend.py
grep "from drummer_mapping_service" dcsm_backend.py

# Should see:
# from drummer_mapping_service import get_drummer_service

# 2. Test drummer service directly
python test_drummer_connection.py

# 3. Check for Python errors on startup
python dcsm_backend.py 2>&1 | grep -i error
```

---

### **Problem: `sqlite3.OperationalError: unable to open database file`**

**Cause:** Admin database not found

**Solution:**
```bash
# 1. Check database exists
ls admin/drumtrackai.db

# 2. If missing, system will use fallback characteristics
# This is OK for testing, but analysis won't be real

# 3. To get real database:
#    - Run admin drummer analysis
#    - OR copy from backup
```

**Note:** System still works with fallback, just uses default characteristics

---

### **Problem: Rust generator not working**

**Cause:** Rust binary not built or not found

**Solution:**
```bash
# 1. Build Rust audio-core
cd audio-core
cargo build --release

# 2. Set environment variable
set AUDIO_CORE_BIN=%CD%\audio-core\target\release\audio-core.exe

# 3. Enable Rust
set USE_RUST=1

# 4. Restart backend
python dcsm_backend.py

# 5. Verify Rust is working
curl "http://localhost:8000/bench/analysis?key=test.mp3&impl=rust"
```

---

### **Problem: `subprocess.TimeoutExpired` when generating**

**Cause:** Rust command taking too long or hanging

**Solution:**
```bash
# 1. Test Rust directly
cd audio-core
cargo run --release -- generate --bpm 120 --start 0 --end 8 --style rock

# 2. If that works, check backend timeout
# In dcsm_backend.py, increase timeout:
# result = subprocess.run(..., timeout=60)  # Increase from 30

# 3. If Rust hangs, rebuild:
cd audio-core
cargo clean
cargo build --release
```

---

## ⚛️ Frontend / React Issues

### **Problem: `npm start` fails with `ENOENT` or dependency errors**

**Cause:** Corrupted node_modules

**Solution:**
```bash
cd frontend

# 1. Clean install
rm -rf node_modules package-lock.json
npm install

# 2. If still fails, check Node version
node --version  # Should be 16+

# 3. Try with legacy peer deps
npm install --legacy-peer-deps

# 4. Start
npm start
```

---

### **Problem: Drummer list doesn't load in UI**

**Cause:** API call failing or backend not running

**Solution:**
```bash
# 1. Check backend is running
curl http://localhost:8000/healthz
# Should return: {"ok": true, "ts": ...}

# 2. Test drummer endpoint directly
curl http://localhost:8000/api/drummers

# 3. Check browser console (F12)
# Look for CORS errors or network failures

# 4. Check frontend API base URL
# In frontend/src/services/api.ts
# Should use relative URLs: '/api/drummers' not 'http://localhost:8000/api/drummers'
```

---

### **Problem: `CORS` errors in browser console**

**Cause:** Backend CORS not configured for frontend

**Solution:**
```python
# In dcsm_backend.py, verify CORS setup:

cors = aiohttp_cors.setup(app, defaults={
    "*": aiohttp_cors.ResourceOptions(
        allow_headers="*",
        allow_methods="*",
        expose_headers="*",
        allow_credentials=False
    )
})

# Apply CORS to all routes:
for route in list(app.router.routes()):
    try:
        cors.add(route)
    except Exception:
        pass
```

---

### **Problem: Generated drums don't play**

**Cause:** Audio engine not initialized or files not accessible

**Solution:**
```typescript
// 1. Check browser console for audio errors
// Look for: "Failed to load audio" or CORS errors

// 2. Verify audio files are accessible
// Open: http://localhost:8000/files/audio?key=YOUR_FILE_KEY
// Should stream audio

// 3. Check Web Audio API
// In browser console:
const AudioContext = window.AudioContext || window.webkitAudioContext;
const ctx = new AudioContext();
console.log(ctx.state);  // Should be "running" or "suspended"

// 4. Click anywhere to resume (browsers require user interaction)
document.addEventListener('click', () => {
    ctx.resume();
});
```

---

### **Problem: Waveform not displaying**

**Cause:** Peak extraction failed or waveform data missing

**Solution:**
```bash
# 1. Check backend logs for errors
python dcsm_backend.py 2>&1 | grep -i "waveform\|peak"

# 2. Test waveform endpoint
curl "http://localhost:8000/files/waveform?key=YOUR_FILE&width=1000"

# 3. Try smaller audio file first
# Large files (>500MB) may timeout

# 4. Check file format
# Supported: MP3, WAV, FLAC, AAC
# Unsupported: OGG, M4A, WMA
```

---

## 🦀 Rust / Audio-Core Issues

### **Problem: `cargo build` fails with compiler errors**

**Cause:** Outdated Rust or missing dependencies

**Solution:**
```bash
# 1. Update Rust
rustup update

# 2. Check Rust version (need 1.70+)
rustc --version

# 3. Clean and rebuild
cd audio-core
cargo clean
cargo build --release

# 4. If still fails, check Cargo.toml dependencies
# All versions should be compatible
```

---

### **Problem: Rust binary runs but produces no output**

**Cause:** Wrong CLI arguments or input file issues

**Solution:**
```bash
cd audio-core

# 1. Test with simple command
cargo run --release -- --help

# 2. Test analysis
cargo run --release -- analyze path/to/audio.wav

# 3. Test generation
cargo run --release -- generate --bpm 120 --start 0 --end 8 --style rock

# 4. Check for JSON output
# Should print valid JSON, not error messages
```

---

### **Problem: Audio decoding fails**

**Cause:** Unsupported format or corrupt file

**Solution:**
```bash
# 1. Check file format
file audio.mp3

# 2. Try converting with ffmpeg
ffmpeg -i input.m4a -acodec libmp3lame output.mp3

# 3. Use WAV for guaranteed compatibility
ffmpeg -i input.mp3 -acodec pcm_s16le output.wav

# 4. Test with simple sine wave
ffmpeg -f lavfi -i "sine=frequency=440:duration=5" test.wav
```

---

## 🎵 Audio / Generation Issues

### **Problem: Generated drums sound robotic**

**Cause:** Humanization too low or no swing applied

**Solution:**
```json
// Increase humanization in generation request:
{
  "drummer_id": "studio_groove_master",
  "humanize": 0.20,  // Increase from default
  // Drummer service already applies humanization based on characteristics
}

// Or use drummer with more humanization:
// "alternative_innovator" has humanize: 0.20
// "studio_groove_master" has humanize: 0.14
```

---

### **Problem: Drums don't match song tempo**

**Cause:** Wrong BPM detected or not using per-section tempo

**Solution:**
```bash
# 1. Verify tempo detection
curl "http://localhost:8000/analyze/tempo?key=YOUR_FILE"

# 2. Use per-section tempo analysis
curl -X POST http://localhost:8000/analyze/tempo_sections \
  -H "Content-Type: application/json" \
  -d '{"key": "YOUR_FILE", "sections": [...]}'

# 3. Manually override BPM in UI
# Use detected tempo × 2 or ÷ 2 if double/half time

# 4. For tempo changes, use multiple sections with different BPMs
```

---

### **Problem: Wrong drummer style applied**

**Cause:** Drummer characteristics not loading from DB

**Solution:**
```bash
# 1. Test drummer details endpoint
curl http://localhost:8000/api/drummers/studio_groove_master

# Should include "characteristics" object with real values

# 2. If characteristics is empty, check database
sqlite3 admin/drumtrackai.db
SELECT * FROM drummer_style_vectors WHERE drummer_id = 'jeff_porcaro';

# 3. If no results, system uses fallback
# Either:
#   a) Run admin analysis to populate
#   b) Use fallback (still works, just default values)
```

---

## 📁 File / Upload Issues

### **Problem: Upload fails with `413 Request Entity Too Large`**

**Cause:** File too large for server limit

**Solution:**
```python
# In dcsm_backend.py, increase limit:

app = web.Application(client_max_size=1024**3)  # 1GB
```

Or use smaller files (<500MB recommended).

---

### **Problem: Upload succeeds but analysis fails**

**Cause:** Corrupt file or unsupported format

**Solution:**
```bash
# 1. Check file integrity
ffprobe input.mp3

# 2. Re-encode with ffmpeg
ffmpeg -i input.mp3 -c:a libmp3lame -b:a 320k output.mp3

# 3. Try WAV format (most compatible)
ffmpeg -i input.mp3 output.wav

# 4. Check file duration
# Very short (<1s) or very long (>10min) may cause issues
```

---

## 🔍 Debugging Tips

### **Enable Verbose Logging**

```python
# In dcsm_backend.py, add at top:

import logging
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

### **Test Each Component Independently**

```bash
# 1. Test drummer service
python test_drummer_connection.py

# 2. Test Rust audio-core
cd audio-core && cargo test

# 3. Test API endpoints
curl http://localhost:8000/api/drummers
curl http://localhost:8000/healthz

# 4. Test frontend build
cd frontend && npm run build
```

### **Check Environment Variables**

```bash
# Windows
echo %USE_RUST%
echo %AUDIO_CORE_BIN%
echo %ADMIN_DB_PATH%

# Should be:
# USE_RUST=1
# AUDIO_CORE_BIN=f:\DrumTracKAI_v1.1.16_Clean\audio-core\target\release\audio-core.exe
# ADMIN_DB_PATH=f:\DrumTracKAI_v1.1.16_Clean\admin\drumtrackai.db (optional)
```

---

## 📊 Performance Issues

### **Problem: Analysis is very slow**

**Solution:**
```bash
# 1. Enable Rust (5-7x faster)
set USE_RUST=1
set AUDIO_CORE_BIN=audio-core\target\release\audio-core.exe

# 2. Build Rust in release mode (NOT debug)
cd audio-core
cargo build --release  # NOT cargo build

# 3. Use smaller files for testing
# Or use /bench endpoints to compare:
curl "http://localhost:8000/bench/analysis?key=test.mp3&impl=rust"
curl "http://localhost:8000/bench/analysis?key=test.mp3&impl=python"
```

### **Problem: Frontend is sluggish**

**Solution:**
```bash
# 1. Build for production
cd frontend
npm run build

# 2. Serve built files (not dev server)
# Use nginx or serve:
npx serve -s build

# 3. Check browser dev tools
# Look for performance bottlenecks

# 4. Reduce waveform width
# In Timeline.tsx, reduce peak count:
const width = 500;  // Instead of 1000
```

---

## 🚨 Emergency: Complete Reset

If nothing works, start fresh:

```bash
# 1. Backend
cd f:\DrumTracKAI_v1.1.16_Clean
rm -rf drumtrackai_env
python -m venv drumtrackai_env
.\drumtrackai_env\Scripts\activate
pip install -r requirements.txt

# 2. Rust
cd audio-core
cargo clean
cargo build --release

# 3. Frontend
cd frontend
rm -rf node_modules package-lock.json
npm install

# 4. Test
python test_drummer_connection.py
python dcsm_backend.py
cd frontend && npm start
```

---

## 📞 Getting Help

If you're still stuck:

1. **Check Logs:**
   - Backend: Terminal output
   - Frontend: Browser console (F12)
   - Rust: `cargo run` output

2. **Gather Info:**
   - Python version: `python --version`
   - Node version: `node --version`
   - Rust version: `rustc --version`
   - OS: Windows/Linux/Mac
   - Error message (full stack trace)

3. **Test Minimal Example:**
   - Single file upload
   - Single drummer selection
   - Single generation request
   - Note exactly where it fails

4. **Check Documentation:**
   - [README_MAIN.md](README_MAIN.md)
   - [ARCHITECTURE.md](ARCHITECTURE.md)
   - [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## ✅ Quick Checklist

Before reporting an issue, verify:

- [ ] Python 3.11.x (not 3.12+)
- [ ] Virtual environment activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Rust built in release mode (`cargo build --release`)
- [ ] Frontend dependencies installed (`npm install`)
- [ ] Backend running on port 8000
- [ ] Frontend running on port 3000
- [ ] No CORS errors in browser console
- [ ] Test script passes (`python test_drummer_connection.py`)

---

**Document Version:** 1.0  
**Last Updated:** November 16, 2024  
**Status:** ✅ Comprehensive
