# DrumTracKAI v1.1.16.1 - Codebase Cleanup Plan

## 🎯 Objective
Clean up the codebase by archiving unused/legacy files while preserving all active v1.1.16.1 components.

---

## ✅ **KEEP - Active Components**

### Core Plugin & Backend
- `DrumTracKAIConnector/` - JUCE VST3/AU plugin (v1.1.16.1)
- `plugin_endpoint.py` - Plugin HTTP API backend
- `dcsm_backend.py` - Main DCSM backend (if actively used)
- `drumtrackai_env/` - Python virtual environment

### Rust Components
- `audio-core/` - Rust audio processing
- `rust-core/` - Core Rust modules
- `rust-audio/` - Audio DSP modules
- `Cargo.toml`, `Cargo.lock` - Rust configuration
- `target/` - Rust build output

### Configuration & Dependencies
- `.gitignore` - Git configuration
- `.env.template` - Environment template
- `requirements.txt` - Python dependencies
- `docker-compose.yml` - Docker config (if used)

### Current Documentation
- `README.md` - Main README (updated)
- `GUIDE_TRACK_IMPLEMENTATION.md` - Guide track docs
- `COMPLETE_PLUGIN_INTEGRATION_GUIDE.md` - Plugin integration
- `README_START_HERE.md` - Getting started guide

### Essential Scripts
- `LAUNCH_V1116.bat` - Main launcher
- `BACKUP_v1.1.16_with_guide_track.bat` - Backup script
- `STOP_ALL.bat` - Stop services

### Data Directories
- `uploads/` - User uploads
- `sessions/` - Session data
- `database/` - Database files (if actively used)
- `models/` - AI models (if exist)

---

## 📦 **ARCHIVE - Legacy/Unused**

### Legacy Documentation (100+ files)
All `.md` files except the ones listed above:
- Session summaries from previous versions
- Old implementation plans
- Deprecated architecture docs
- Training status documents
- Integration guides for old features

### Deprecated Scripts (50+ files)
- `START_*.bat` variants (keep only LAUNCH_V1116.bat)
- `TEST_*.bat` files
- `DEPLOY_*.bat` old deployment scripts
- `RESTART_*.bat` variants
- `CHECK_*.bat` debug scripts
- `OPEN_*.bat` page openers

### Old Frontend Versions
- `frontend/` - Old frontend
- `web-frontend-landing-v117/` - Old landing page
- `*.OLD` files (landing_page.html.OLD, etc.)
- `temp_main.js` - Temporary file (900KB)

### Legacy Backend Components
- `admin/` - Old admin interface (if not used)
- `tracktion-hybrid/` - Old hybrid approach (replaced by plugin)
- `simple_backend.py` - Superseded
- `minimal_backend.py` - Superseded
- `*.backup` files

### Test & Analysis Files
- `test_*.py` scripts (unless actively used)
- `analyze_*.py` scripts
- `test_*.html` files
- `test_output.json`, `test_pattern.json`
- `sectionalization_test_results.json`
- `e_drive_analysis_report.json` (30MB)
- `database_scan_results.txt` (640KB)
- `midi_migration_log_*.json` (339KB)

### Training Scripts (if not actively used)
- `train_*.py` files
- `prepare_training_data.py`
- `bootstrap_training.py`
- `auto_train_complete.py`
- Training-related files

### Generated/Temporary Files
- `ai_generated_test.mid`
- `generated_peg_drums.mid`
- `rust_output.json`
- `songmap_test.json`
- `commit_message.txt`
- `validation_report.json`
- `Saves` (empty file)
- `DB` (empty file)

### PowerShell/Build Scripts
- `*.ps1` files (analyze_file.ps1, etc.)
- `backup_*.bat` duplicates
- `git_*.bat` scripts
- Migration/deployment scripts

---

## 📂 **Archive Structure**

Create: `F:\DrumTracKAI_v1.1.16_Clean\_ARCHIVE_PRE_CLEANUP\`

Subdirectories:
- `documentation/` - All legacy .md files
- `scripts/` - Deprecated .bat, .ps1, .py scripts
- `old_frontends/` - frontend/, web-frontend-landing-v117/
- `test_files/` - Test outputs and analysis results
- `training/` - Training scripts and models (if not used)
- `legacy_backend/` - Old backend components

---

## 🗂️ **Final Clean Structure**

```
DrumTracKAI_v1.1.16_Clean/
├── DrumTracKAIConnector/      # JUCE Plugin
├── audio-core/                # Rust audio processing
├── rust-core/                 # Rust core
├── rust-audio/                # Rust audio DSP
├── drumtrackai_env/           # Python venv
├── target/                    # Rust builds
├── uploads/                   # User uploads
├── sessions/                  # Session data
├── database/                  # Database (if used)
├── models/                    # AI models (if used)
├── plugin_endpoint.py         # Plugin backend
├── dcsm_backend.py            # DCSM backend (if used)
├── requirements.txt           # Python deps
├── Cargo.toml                 # Rust config
├── README.md                  # Main docs
├── GUIDE_TRACK_IMPLEMENTATION.md
├── COMPLETE_PLUGIN_INTEGRATION_GUIDE.md
├── README_START_HERE.md
├── LAUNCH_V1116.bat           # Main launcher
├── BACKUP_v1.1.16_with_guide_track.bat
├── STOP_ALL.bat
├── .gitignore
├── .env.template
└── _ARCHIVE_PRE_CLEANUP/      # All archived files
```

---

## ⚠️ **Safety Measures**

1. **Full Backup First** - Already completed ✅
2. **Move, Don't Delete** - All files go to archive
3. **Test After Cleanup** - Verify plugin and backend work
4. **Keep Archive Accessible** - Can restore if needed

---

## 📋 **Execution Steps**

1. Create archive directory structure
2. Move legacy documentation
3. Move deprecated scripts
4. Move old frontend versions
5. Move test/analysis files
6. Move training scripts
7. Remove empty directories
8. Update README with new structure
9. Test system functionality
10. Create post-cleanup backup

---

**Estimated Space Savings:** ~200-300 files moved to archive
**Current File Count:** ~400+ files
**Target File Count:** ~50-100 active files
