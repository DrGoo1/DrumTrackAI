# 🔧 **DrumTracKAI v1.1.16 - Admin Guide**

**Complete System Administration & Development Guide**

---

## 📋 **Table of Contents**

1. [System Overview](#system-overview)
2. [Installation & Setup](#installation--setup)
3. [AI System Management](#ai-system-management)
4. [Drummer Profile Management](#drummer-profile-management)
5. [Automated Profile Builder](#automated-profile-builder)
6. [Database Management](#database-management)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)
9. [Development](#development)

---

## 🎯 **System Overview**

### **Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│                  DrumTracKAI v1.1.16                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Frontend (React)   →   Backend (Python/aiohttp)       │
│       ↓                        ↓                        │
│  REST API          →   AI Generator (PyTorch)          │
│                            ↓                            │
│                    Database (SQLite)                    │
│                    - 91,074 patterns                    │
│                    - 12 drummer profiles                │
│                    - Maturity tracking                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### **Core Components:**

1. **AI Pattern Generator** (`ai_pattern_generator.py`)
   - GrooVAE model (3.8M parameters)
   - Trained on 91,074 patterns
   - GPU-accelerated inference

2. **Category System** (`drummer_categories.py`)
   - 7 categories
   - 12 individual drummers
   - Pure characteristics (no blending)

3. **Maturity Tracking** (`drummer_profile_maturity.py`)
   - Song-level tracking
   - Automatic scoring
   - Recommendations

4. **Profile Builder** (`automated_drummer_profile_builder.py`)
   - YouTube download
   - MVSep drum extraction
   - Pattern analysis
   - Database update

---

## 🚀 **Installation & Setup**

### **Prerequisites:**
```bash
# Required
- Python 3.11+
- Node.js v20+
- CUDA 11.8+ (for GPU acceleration)
- 16GB RAM minimum
- MVSep API key (for profile building)

# Optional
- 7-Zip (for backups)
- Git (for version control)
```

### **Step 1: Python Environment**
```bash
cd f:\DrumTracKAI_v1.1.16_Clean

# Use existing v1.1.11 environment
f:\DrumTracKAI_v1.1.11\drumtrackai_env\Scripts\activate

# Or create new environment
python -m venv drumtrackai_env
drumtrackai_env\Scripts\activate
pip install -r requirements.txt
```

### **Step 2: Install Dependencies**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install librosa soundfile numpy==1.24.3
pip install aiohttp aiohttp-cors
pip install yt-dlp  # For YouTube downloads
```

### **Step 3: Verify Installation**
```bash
python test_profile_builder.py
```

**Expected:** All 7 tests pass ✅

---

## 🤖 **AI System Management**

### **Model Information:**
```
Name: GrooVAE
Parameters: 3.8M
Training: 100 epochs, 3 hours on RTX 3070
Validation Loss: 47.4057
Database: 91,074 patterns
```

### **Files:**
- `groove_vae_model.py` - Model architecture
- `groove_vae_best.pth` - Trained weights (47.4 val loss)
- `train_groove_vae_gpu.py` - Training script
- `validate_groove_vae.py` - Validation suite
- `prepare_training_data.py` - Data preparation

### **Retraining the Model:**

**When to retrain:**
- Added 10,000+ new patterns
- Significant drummer additions
- Want to improve specific styles

**How to retrain:**
```bash
# 1. Prepare data (if new patterns added)
python prepare_training_data.py

# 2. Train on GPU
python train_groove_vae_gpu.py

# 3. Validate
python validate_groove_vae.py

# 4. If better, replace model
copy groove_vae_best.pth groove_vae_backup.pth
# New model auto-saved as groove_vae_best.pth
```

**Training takes:** ~3 hours on RTX 3070, ~12 hours on CPU

---

## 👤 **Drummer Profile Management**

### **Current Profiles (12):**

**Category assignments in** `drummer_categories.py`:

```python
DRUMMER_CATEGORIES = {
    "studio_session_masters": {
        "drummers": [
            {
                "id": "studio_session_1",
                "source_drummer": "jeff_porcaro",
                ...
            }
        ]
    },
    ...
}
```

### **Viewing All Profiles:**
```bash
curl http://localhost:8000/api/ai/drummer-categories
curl http://localhost:8000/api/ai/maturity-stats
```

### **Adding New Drummer to Category:**

**Step 1: Run automated builder** (see next section)

**Step 2: Update `drummer_categories.py`:**
```python
"funk_soul_masters": {
    "drummers": [
        {...},  # Existing drummers
        {       # NEW
            "id": "funk_soul_2",
            "display_name": "Drummer #2",
            "source_drummer": "clyde_stubblefield",  # From automation
            "description": "...",
            "best_for": [...],
            "signature_techniques": [...],
            "difficulty": "Advanced"
        }
    ]
}
```

**Step 3: Restart backend**
```bash
python dcsm_backend.py
```

---

## 🤖 **Automated Profile Builder**

### **Overview:**
Fully automated system to add new drummers:
```
YouTube Download → MVSep Extraction → Analysis → Database → Done!
```

### **Prerequisites:**
```bash
# 1. Install dependencies
pip install yt-dlp librosa soundfile

# 2. Set MVSep API key
set MVSEP_API_KEY=your_key_from_mvsep.com
```

### **Pre-Configured Drummers:**

**File:** `automated_drummer_profile_builder.py`

**Queue (3 drummers ready):**
1. Clyde Stubblefield (Funky Drummer)
2. Steve Gadd (Session legend)
3. Phil Collins (Pop icon)

### **Usage:**

**List available:**
```bash
python automated_drummer_profile_builder.py --list
```

**Build one drummer:**
```bash
python automated_drummer_profile_builder.py --drummers clyde_stubblefield
```

**Build all queued:**
```bash
python automated_drummer_profile_builder.py
```

### **Adding New Drummer to Queue:**

Edit `automated_drummer_profile_builder.py`:
```python
DRUMMER_QUEUE = [
    # ... existing
    {
        "id": "bernard_purdie",
        "name": "Bernard Purdie",
        "category": "funk_soul_masters",
        "drummer_number": 3,
        "display_name": "Drummer #3",
        "styles": ["Funk", "Soul", "Shuffle"],
        "era": "1960s-present",
        "signature_songs": [
            {
                "title": "Purdie Shuffle",
                "youtube_url": "https://www.youtube.com/watch?v=...",
                "tempo": 88,
                "notes": "Signature shuffle pattern"
            },
            # Add 2-4 more songs
        ]
    }
]
```

Then run: `python automated_drummer_profile_builder.py --drummers bernard_purdie`

### **Process Details:**

**What happens:**
1. Downloads each song from YouTube (yt-dlp)
2. Sends to MVSep API for drum isolation
3. Analyzes drum patterns with librosa
4. Calculates characteristics (ghost notes, ride preference, etc.)
5. Saves to `drummer_profiles` table
6. Saves style vectors to `drummer_style_vectors` table
7. Tracks songs in `drummer_analyzed_songs` table
8. Updates maturity metrics
9. Provides recommendations

**Time per drummer:** ~30-40 minutes (3-4 songs)

**Output location:**
- Downloads: `E:/DrumTracKAI_Master/05_YouTube_Downloads/`
- MVSep stems: `E:/DrumTracKAI_Master/06_MVSep_Stems/`

---

## 🗄️ **Database Management**

### **Database Location:**
```
f:/DrumTracKAI_v1.1.16_Clean/admin/drumtrackai.db
```

### **Tables:**

1. **drum_patterns** (91,074 entries)
   - Pattern data, tempo, style, complexity
   - Source of all training data

2. **drummer_profiles**
   - Drummer metadata (id, name, styles, era)
   - Created by automation

3. **drummer_style_vectors**
   - Quantified characteristics (ghost notes, ride preference, etc.)
   - Used by AI generator

4. **drummer_analyzed_songs**
   - Songs used for each profile
   - Title, URL, tempo, pattern count
   - Maturity tracking

5. **drummer_profile_metrics**
   - Maturity scores, levels, recommendations
   - Auto-updated

### **Querying Database:**
```bash
# SQLite command line
sqlite3 admin/drumtrackai.db

# Check patterns
SELECT COUNT(*) FROM drum_patterns;

# Check drummers
SELECT drummer_id, name FROM drummer_profiles;

# Check maturity
SELECT drummer_id, maturity_level, maturity_score 
FROM drummer_profile_metrics
ORDER BY maturity_score DESC;
```

### **Backup Database:**
```bash
copy admin\drumtrackai.db admin\drumtrackai_backup_%date%.db
```

---

## 🚀 **Deployment**

### **Local Development:**
```bash
# Backend
python dcsm_backend.py

# Frontend (if available)
cd web-frontend
npm start
```

### **Production Deployment:**

**Option 1: Docker** (if configured)
```bash
docker-compose up -d
```

**Option 2: Standalone**
```bash
# Backend as service
nohup python dcsm_backend.py > backend.log 2>&1 &

# Frontend as static files
cd web-frontend
npm run build
# Serve build/ directory with nginx
```

### **Environment Variables:**
```bash
# Optional: Use Rust audio-core for 5-7x speedup
set USE_RUST=1
set AUDIO_CORE_BIN=audio-core\target\release\audio-core.exe

# MVSep for automated profile building
set MVSEP_API_KEY=your_key_here
```

---

## 🔍 **Monitoring & Maintenance**

### **System Health:**
```bash
# Check AI status
curl http://localhost:8000/api/ai/status

# Check pattern count
curl http://localhost:8000/api/ai/styles

# Check maturity stats
curl http://localhost:8000/api/ai/maturity-stats
```

### **Log Files:**
```bash
# Backend logs
tail -f backend.log

# Automation logs
# Shown in real-time during profile building
```

### **Performance Metrics:**
```bash
# Generation time should be <1 second
# Database queries <10ms
# MIDI export <50ms
```

---

## 🐛 **Troubleshooting**

### **"CUDA out of memory"**
**Solution:**
```python
# In ai_pattern_generator.py, change:
device = 'cpu'  # Instead of 'cuda'
```

### **"Model file not found"**
**Check:**
```bash
ls groove_vae_best.pth  # Should exist
```
**Fix:** Re-download or retrain model

### **"Database locked"**
**Cause:** Multiple connections
**Fix:**
```bash
# Close all connections
# Restart backend
python dcsm_backend.py
```

### **"MVSep API error"**
**Check:**
```bash
echo %MVSEP_API_KEY%  # Should show your key
```
**Fix:** Get key from mvsep.com

### **"YouTube download failed"**
**Update yt-dlp:**
```bash
pip install --upgrade yt-dlp
```

---

## 💻 **Development**

### **Project Structure:**
```
DrumTracKAI_v1.1.16_Clean/
├── admin/
│   ├── drumtrackai.db              # Main database
│   └── admin_window.py             # Admin GUI
├── ai_pattern_generator.py         # AI generator core
├── groove_vae_model.py             # VAE architecture
├── groove_vae_best.pth             # Trained model
├── drummer_categories.py           # Category system
├── drummer_profile_maturity.py     # Maturity tracking
├── automated_drummer_profile_builder.py  # Automation
├── backend_ai_endpoints.py         # AI API
├── dcsm_backend.py                 # Main backend
└── web-frontend/                   # React app
```

### **Adding New Features:**

**New AI endpoint:**
1. Add handler in `backend_ai_endpoints.py`
2. Register route in `setup_ai_routes()`
3. Test with curl
4. Document in API docs

**New drummer characteristic:**
1. Add to `drummer_profile_maturity.py` calculations
2. Update `_apply_drummer_profile()` in `ai_pattern_generator.py`
3. Test generation

**New category:**
1. Add to `DRUMMER_CATEGORIES` in `drummer_categories.py`
2. Add icon, color, description
3. Add drummers to category
4. Restart backend

### **Testing:**
```bash
# Test profile builder
python test_profile_builder.py

# Test AI generator
python ai_pattern_generator.py

# Test model validation
python validate_groove_vae.py
```

---

## 📦 **Backup & Version Control**

### **Create Backup:**
```bash
backup_codebase.bat
```
Creates timestamped backup in `F:\Backups\DrumTracKAI\`

### **Git Save:**
```bash
git_save_progress.bat
```
Commits all changes with descriptive message

### **What to Backup:**
- ✅ Source code
- ✅ `groove_vae_best.pth` (trained model)
- ✅ `admin/drumtrackai.db` (database)
- ✅ Configuration files
- ❌ `node_modules/` (can reinstall)
- ❌ Downloaded songs (can re-download)

---

## 📊 **Performance Tuning**

### **GPU Acceleration:**
```python
# Ensure CUDA is used
device = 'cuda' if torch.cuda.is_available() else 'cpu'
```

**Expected speedup:**
- CPU: 200-500ms per generation
- GPU: 20-100ms per generation

### **Database Optimization:**
```sql
-- Add indices
CREATE INDEX idx_tempo ON drum_patterns(tempo_bpm);
CREATE INDEX idx_style ON drum_patterns(style);
CREATE INDEX idx_drummer ON drummer_analyzed_songs(drummer_id);
```

### **Batch Processing:**
For multiple patterns, use batch generation API (if implemented)

---

## 🔒 **Security**

### **API Keys:**
```bash
# Never commit API keys to git
# Store in environment variables
set MVSEP_API_KEY=...

# Add to .gitignore:
.env
*.key
api_keys.txt
```

### **Database:**
```bash
# Regular backups
# Restrict file permissions
# No public access
```

---

## 📈 **Future Enhancements**

### **Planned:**
- [ ] Real-time pattern generation
- [ ] Style transfer between drummers
- [ ] Pattern morphing/interpolation
- [ ] MIDI editing in-app
- [ ] Cloud deployment
- [ ] Mobile app

### **Research:**
- [ ] Transformer-based architecture
- [ ] Multi-track generation (bass + drums)
- [ ] Real audio synthesis (not just MIDI)

---

## 📞 **Support**

### **Documentation:**
- User Guide: `USER_README.md`
- Maturity System: `PROFILE_MATURITY_SYSTEM.md`
- Category System: `DRUMMER_ASSIGNMENT_GUIDE.md`
- API Docs: `API_DOCUMENTATION.md` (if exists)

### **Common Tasks:**

**Add drummer:**
```bash
python automated_drummer_profile_builder.py --drummers <name>
# Then update drummer_categories.py
```

**Retrain model:**
```bash
python train_groove_vae_gpu.py
```

**Check system:**
```bash
python test_profile_builder.py
curl http://localhost:8000/api/ai/status
```

---

## ✅ **Admin Checklist**

### **Daily:**
- [ ] Check backend is running
- [ ] Monitor system health

### **Weekly:**
- [ ] Review maturity stats
- [ ] Check for failed generations
- [ ] Backup database

### **Monthly:**
- [ ] Full system backup
- [ ] Review new drummer additions
- [ ] Update dependencies
- [ ] Performance review

### **As Needed:**
- [ ] Add new drummers (automation)
- [ ] Retrain model (if significant data added)
- [ ] Update categories
- [ ] Deploy updates

---

**You're now ready to administer DrumTracKAI v1.1.16!** 🎯
