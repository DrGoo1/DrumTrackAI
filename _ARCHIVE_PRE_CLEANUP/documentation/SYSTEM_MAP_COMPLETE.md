# DrumTracKAI v1.1.16 Complete System Map
**Last Updated:** November 18, 2025
**Status:** Audio fixes in progress - Frontend/Backend need cleanup

---

## 📁 Project Structure Overview

```
F:\DrumTracKAI_v1.1.16_Clean\
├── frontend/                          # Main DCSM Audio Editor (React)
├── web-frontend-landing-v117/         # Landing Page (Separate React App)
├── admin/                             # Qt-based Admin Module
├── drumtrackai_env/                   # Python Virtual Environment (CORRUPTED)
├── uploads/                           # Uploaded audio files
├── dcsm_backend.py                    # Main Backend Server
└── [various .bat scripts]             # Startup scripts
```

---

## 🌐 Web Applications

### 1. Main DCSM Audio Editor (Primary Interface)
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\frontend\`

**Key Files:**
- `src/audio/engine.ts` - Audio playback engine (MODIFIED TODAY - HTML5 Audio)
- `src/components/WebDAWApp.tsx` - Main application component (MODIFIED - loading locks)
- `src/components/Timeline.tsx` - Waveform display (MODIFIED - stereo rendering)
- `src/components/Mixer.tsx` - Audio mixer with VU meters
- `src/components/PianoRoll.tsx` - MIDI piano roll editor
- `src/services/api.ts` - Backend API client
- `package.json` - Dependencies (React, Tone.js, etc.)

**Running:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean\frontend
npm start
# Runs on: http://localhost:3000
```

**Pages:**
- `/` - Main DCSM editor with waveform and timeline
- `/pro` - Pro upload page
- `/bench` - Performance benchmarks (Rust vs Python)

### 2. Landing Page (Marketing/Info Page)
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117\`

**Key Files:**
- `src/App.js` - Main landing page app
- `src/pages/LandingPage.js` - Landing page component
- `start.bat` - Startup script (PORT=3004)
- `package.json` - Dependencies

**Running:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
set PORT=3004
npm start
# Runs on: http://localhost:3004
```

---

## 🐍 Backend Server

### Main Backend
**File:** `f:\DrumTracKAI_v1.1.16_Clean\dcsm_backend.py`

**Key Endpoints:**
```
POST /files/upload                 # Audio file upload
GET  /files/waveform              # Get waveform peak data  
GET  /files/audio                 # Stream audio files (MODIFIED - CORS)
GET  /api/status                  # Health check
POST /api/analyze                 # Audio analysis (Rust/Python)
GET  /bench/peaks                 # Benchmark peak extraction
GET  /bench/tempo                 # Benchmark tempo detection
POST /bench/generate              # Benchmark pattern generation
GET  /bench/sectionize            # Benchmark sectionization
POST /api/generate/drummer        # AI drummer pattern generation
```

**Modified Functions Today:**
- `audio_file()` (lines 493-510) - Simplified with FileResponse + CORS

**Running:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean

# OPTION 1: Use v1.1.11 Python (WORKING)
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py

# OPTION 2: Fix v1.1.16 Python (BROKEN - run FIX_PYTHON_ENV.bat first)
drumtrackai_env\Scripts\python.exe dcsm_backend.py

# Runs on: http://localhost:8000
```

**Dependencies:**
- aiohttp - Web server
- aiohttp_cors - CORS middleware
- pydantic - Data validation (BROKEN in v1.1.16 env)
- torch - AI pattern generation
- librosa - Audio analysis (Python fallback)

---

## 🗄️ Databases

### 1. Main Application Database
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\drumtrackai.db`

**Tables:**
- drummer_profiles - Drummer information and characteristics
- signature_songs - Reference songs for each drummer
- analysis_results - Cached audio analysis results
- user_sessions - User session data

### 2. Admin Module Database
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\admin\drumtrackai.db`

**Tables:**
- drummer_category_mapping - Drummer to category relationships
- training_data - ML training datasets
- batch_processing_jobs - Background job queue

---

## 🖥️ Admin Module (Qt Desktop Application)

**Location:** `f:\DrumTracKAI_v1.1.16_Clean\admin\`

**Main Files:**
- `admin_main.py` - Qt application entry point
- `core/application_state.py` - Application state management
- `core/event_bus.py` - Event system
- `widgets/` - UI components

**Features:**
- Superior Drummer 3 integration
- REAPER automation (Lua scripts)
- Batch audio processing
- GPU acceleration setup
- Real-time monitoring dashboard

**Running:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean\admin
python admin_main.py
```

**REAPER Scripts Location:**
`f:\DrumTracKAI_v1.1.16_Clean\admin\reaper_scripts\`

---

## 📦 File Storage

### Uploaded Audio Files
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\uploads\`
- Files named with timestamp + original filename
- Example: `1763523993301-Peg_No_Drums.mp3`

### Processed Audio (Stems)
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\database\processed_stems\`
- Separated drum tracks from MVSep
- Organized by song/artist

### MVSep Output
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\production_mvsep_output\`
- Stem separation results
- Multiple folders per song

---

## 🔧 Configuration Files

### Frontend Configuration
- `frontend/package.json` - NPM dependencies
- `frontend/tsconfig.json` - TypeScript config
- `frontend/tailwind.config.js` - TailwindCSS config

### Backend Configuration  
- `.env.template` - Environment variable template
- `config/` - Application configuration

### Docker Configuration
- `Dockerfile.backend` - Backend container
- `Dockerfile.backend.hybrid` - Backend with Rust
- `docker-compose.yml` - Multi-container orchestration

---

## 🚀 Startup Scripts

### Complete System
```batch
START_COMPLETE_SYSTEM.bat        # Starts all services
```

### Individual Components
```batch
1_START_BACKEND.bat              # Backend only
2_START_DCSM.bat                 # Frontend only  
3_START_LANDING_PAGE.bat         # Landing page only
```

### Restart Scripts
```batch
RESTART_ALL_SERVERS.bat          # Restart everything
RESTART_DCSM_ONLY.bat            # Restart frontend
CLEAR_CACHE_AND_RESTART.bat      # Clear cache + restart
```

### Fix Scripts
```batch
FIX_PYTHON_ENV.bat               # Fix v1.1.16 Python dependencies
```

---

## 🛠️ Python Environments

### v1.1.16 Environment (CORRUPTED)
**Location:** `f:\DrumTracKAI_v1.1.16_Clean\drumtrackai_env\`

**Issue:** pydantic-core module missing/corrupted

**Fix:**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean
call drumtrackai_env\Scripts\activate.bat
pip install --force-reinstall --no-cache-dir pydantic-core
pip install --force-reinstall --no-cache-dir pydantic
```

### v1.1.11 Environment (WORKING)
**Location:** `f:\DrumTracKAI_v1.1.11\drumtrackai_env\`

**Current Workaround:** Use this environment to run v1.1.16 backend
```bash
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py
```

---

## 🔧 Today's Modifications

### Files Modified for Audio Fix

#### 1. Frontend: `frontend/src/audio/engine.ts`
**Status:** MODIFIED - Complete rewrite to use HTML5 Audio

**Changes:**
- Replaced Tone.Player with HTML5 `<audio>` element
- Added `crossOrigin="anonymous"` for CORS
- Manual Transport control (play/pause/stop/seek)
- Direct connection to Web Audio API destination
- Gain set to 0.3 for safe levels

**Lines Changed:** 1-155 (major rewrite)

#### 2. Frontend: `frontend/src/components/WebDAWApp.tsx`
**Status:** MODIFIED - Added loading locks

**Changes:**
- Added `loadingFilesRef` to prevent duplicate loading
- Lock system with Set to track files being loaded
- Lock released in finally block

**Lines Changed:** 177-262

#### 3. Frontend: `frontend/src/components/Timeline.tsx`
**Status:** MODIFIED - Stereo waveform rendering

**Changes:**
- Fixed `hasStereoPeaks` boolean evaluation
- Draws L channel in top half, R in bottom half
- White center line dividing stereo channels
- Adds "(Stereo)" label

**Lines Changed:** 81-130

#### 4. Backend: `dcsm_backend.py`
**Status:** MODIFIED - CORS for audio endpoint

**Changes:**
- Simplified `audio_file()` function
- Uses FileResponse (aiohttp_cors adds headers automatically)
- Removed custom CORS header code

**Lines Changed:** 493-510

---

## ⚠️ Known Issues

### Critical Issues
1. **Audio Not Playing** - Audio element loads but doesn't produce sound
   - Error: "MEDIA_ELEMENT_ERROR: Format error"  
   - CORS error: "MediaElementAudioSource outputs zeroes"
   - Backend returning ERR_EMPTY_RESPONSE (now fixed)

2. **Python Environment Corrupted** - v1.1.16 env has broken dependencies
   - pydantic-core module missing
   - Workaround: Use v1.1.11 environment

3. **Runtime Errors** - Frontend crashes on audio load
   - Audio element event handling issues
   - Need better error handling

### Minor Issues
1. Tempo detection endpoint returns HTML instead of JSON
2. VU meters might not update correctly
3. Large file memory usage (loads entire file)

---

## 🎯 TODO for Tomorrow

### High Priority
1. **Fix Audio Playback**
   - Debug CORS issue with MediaElementSource
   - Verify audio element can create MediaElementSource
   - Test with simple audio file first
   - Ensure backend serves audio with proper headers

2. **Fix Python Environment**
   - Run FIX_PYTHON_ENV.bat
   - Reinstall pydantic dependencies
   - Verify backend starts with v1.1.16 env

3. **Clean Up Code**
   - Remove excessive console.log statements
   - Remove commented-out code
   - Fix TypeScript errors
   - Remove unused imports

### Medium Priority
4. **Test All Features**
   - Upload audio file
   - Waveform display (stereo)
   - Audio playback (full duration)
   - VU meters
   - Mixer controls (volume/mute/solo)
   - Transport controls (play/pause/stop/seek)

5. **Documentation**
   - Update README with current status
   - Document audio architecture change
   - Create troubleshooting guide

6. **Backup**
   - Create full system backup once audio works
   - Tag working version in git (if using)

### Low Priority
7. **Performance**
   - Implement Range request support for large files
   - Add chunked streaming
   - Optimize waveform rendering

8. **Features**
   - Landing page integration
   - Admin module testing
   - AI pattern generation testing

---

## 📋 Testing Checklist

### Audio Playback Test
- [ ] Backend starts without errors
- [ ] Frontend compiles without errors
- [ ] Can access http://localhost:3000/pro
- [ ] Upload audio file succeeds
- [ ] Waveform displays correctly
- [ ] Stereo channels visible with center line
- [ ] NO CORS errors in console
- [ ] Click Play button
- [ ] Audio starts playing immediately
- [ ] Audio continues through full duration
- [ ] NO distortion at any point
- [ ] VU meters show stable values
- [ ] Volume slider works
- [ ] Mute button works
- [ ] Pause/Stop/Seek work correctly

---

## 🔐 Backup Strategy

### What to Backup
```
F:\DrumTracKAI_v1.1.16_Clean\
├── frontend/src/              # Frontend code (MODIFIED)
├── web-frontend-landing-v117/ # Landing page
├── admin/                     # Admin module
├── dcsm_backend.py           # Backend (MODIFIED)
├── *.md                      # Documentation
└── *.bat                     # Startup scripts
```

### What NOT to Backup
```
- node_modules/              # Can be reinstalled
- drumtrackai_env/          # Corrupted anyway
- uploads/                  # Large files
- __pycache__/             # Generated files
- build/                   # Generated files
- .cache/                  # Generated files
```

### Backup Command
```bash
# Create ZIP of important files
tar -czf DrumTracKAI_v1.1.16_Backup_%date%.tar.gz ^
  frontend/src ^
  frontend/public ^
  frontend/package.json ^
  web-frontend-landing-v117/src ^
  admin/ ^
  dcsm_backend.py ^
  ai_pattern_generator.py ^
  *.md ^
  *.bat
```

---

## 📞 Quick Reference

### Start Everything
```bash
# Terminal 1: Backend
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\python.exe dcsm_backend.py

# Terminal 2: Frontend  
cd f:\DrumTracKAI_v1.1.16_Clean\frontend
npm start

# Terminal 3: Landing Page (optional)
cd f:\DrumTracKAI_v1.1.16_Clean\web-frontend-landing-v117
set PORT=3004
npm start
```

### Access URLs
- Main App: http://localhost:3000
- Pro Upload: http://localhost:3000/pro
- Backend API: http://localhost:8000
- Landing Page: http://localhost:3004

### Stop Everything
```bash
taskkill /F /IM python.exe
taskkill /F /IM node.exe
```

---

**End of System Map**
