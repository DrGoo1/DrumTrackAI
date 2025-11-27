# 🎥 YouTube LLM Learning System

**Complete Pipeline for Sourcing and Learning from YouTube Drum Performances**

Version: 1.0.0  
Date: November 21, 2025  
Status: ✅ Production Ready

---

## 📋 **Overview**

The YouTube LLM Learning System automatically sources, analyzes, and learns from YouTube drum performances to train your LLM models. It integrates your existing infrastructure:

- ✅ **YouTube Download Service** (`youtube_service.py`) - Already exists
- ✅ **YouTube Downloader** (`training/youtube_downloader.py`) - Already exists  
- ✅ **LLM Training Widget** (`ui/llm_training_widget.py`) - Already exists
- ✅ **Rust Audio-Core** - Already exists for analysis
- ✅ **Admin UI** - Already exists for management

**NEW:** Complete pipeline integration that ties everything together!

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                  YouTube LLM Learning Pipeline                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
      ┌───────────────────────┴───────────────────────┐
      │                                                 │
      ↓                                                 ↓
┌──────────┐                                    ┌──────────┐
│ STEP 1:  │                                    │ STEP 2:  │
│ SOURCE   │ → YouTube Search & Download  →     │ ANALYZE  │
└──────────┘                                    └──────────┘
      │                                                 │
      ↓                                                 ↓
┌──────────┐                                    ┌──────────┐
│ STEP 3:  │                                    │ STEP 4:  │
│ EXTRACT  │ ← Rust Audio-Core Analysis ←       │ DATASET  │
└──────────┘                                    └──────────┘
      │                                                 │
      └─────────────────────┬───────────────────────┘
                            ↓
                     ┌──────────┐
                     │ STEP 5:  │
                     │  TRAIN   │ → LLM Training Widget
                     └──────────┘
```

---

## ✨ **Features**

### **Intelligent Sourcing**
- ✅ Automatic YouTube search for specific drummers
- ✅ Predefined search queries for famous drummers
- ✅ Quality filtering (SNR, drum presence, duration)
- ✅ Batch operations for multiple drummers

### **Advanced Analysis**
- ✅ Tempo and beat detection via Rust audio-core
- ✅ Section detection (intro/verse/chorus/bridge/outro)
- ✅ Micro-timing analysis (swing, groove, humanization)
- ✅ Velocity/dynamics extraction
- ✅ Pattern complexity scoring

### **LLM Training Preparation**
- ✅ Feature extraction optimized for LLM learning
- ✅ Dataset building in structured JSON format
- ✅ Metadata tracking and versioning
- ✅ Integration with existing LLM training pipeline

### **User Experience**
- ✅ Professional Qt-based UI
- ✅ Real-time progress tracking
- ✅ Detailed logging
- ✅ Error handling and recovery
- ✅ Batch operations support

---

## 🚀 **Quick Start**

### **1. Start the Admin Interface**

```bash
cd f:\DrumTracKAI_v1.1.16_Clean\admin
python main.py
```

### **2. Navigate to YouTube Learning Tab**

In the admin interface:
1. Go to **"YouTube Learning"** tab
2. Select a drummer from the preset dropdown
3. Choose style (rock, jazz, funk, etc.)
4. Set max videos (recommended: 3-5 for testing)
5. Click **"🚀 Start Pipeline"**

### **3. Monitor Progress**

The pipeline will:
- ✅ Search YouTube for performances
- ✅ Download audio files
- ✅ Analyze quality and filter
- ✅ Extract features
- ✅ Build training dataset

### **4. Use the Dataset**

After completion:
- Dataset saved to `admin/data/youtube_llm_learning/datasets/`
- Metadata tracked in `learning_pipeline_metadata.json`
- Ready for LLM training in the **"LLM Training"** tab

---

## 💻 **Programmatic Usage**

### **Simple Pipeline Run**

```python
from admin.services.youtube_llm_learning_service import YouTubeLLMLearningPipeline

# Initialize pipeline
pipeline = YouTubeLLMLearningPipeline()

# Run complete pipeline
result = pipeline.run_complete_pipeline(
    drummer_name="Jeff Porcaro",
    style="rock",
    max_videos=5,
    start_training=False  # Set True to auto-start LLM training
)

print(f"✅ Sourced {result['files_sourced']} files")
print(f"📦 Dataset: {result['dataset_file']}")
```

### **Batch Processing**

```python
# Learn from multiple drummers
famous_drummers = [
    ("Jeff Porcaro", "rock"),
    ("John Bonham", "rock"),
    ("Neil Peart", "rock"),
    ("Steve Gadd", "jazz"),
]

results = pipeline.run_batch_pipeline(famous_drummers, max_videos_each=3)

successful = len([r for r in results if r['success']])
print(f"✅ {successful}/{len(results)} successful")
```

### **Convenience Functions**

```python
from admin.services.youtube_llm_learning_service import (
    quick_learn_from_youtube,
    batch_learn_famous_drummers
)

# Single drummer
result = quick_learn_from_youtube("Jeff Porcaro", "rock", 5)

# All famous drummers
results = batch_learn_famous_drummers(max_videos_each=3)
```

---

## 🔧 **Components**

### **1. YouTubeLLMLearningPipeline** (Service)
**Location:** `admin/services/youtube_llm_learning_service.py`

**Main Methods:**
- `search_and_source_drummer()` - Search and download from YouTube
- `extract_llm_training_features()` - Extract features for LLM
- `build_llm_training_dataset()` - Create structured dataset
- `run_complete_pipeline()` - Execute full pipeline
- `run_batch_pipeline()` - Batch processing

**Features Extracted:**
- Tempo and beat times
- Section boundaries (intro/verse/chorus/etc.)
- Micro-timing variance and stability
- Velocity dynamics and range
- Pattern complexity score
- Style markers

### **2. YouTubeLearningWidget** (UI)
**Location:** `admin/ui/youtube_learning_widget.py`

**Features:**
- Drummer selection dropdown (pre-populated)
- Style/genre selection
- Max videos slider
- Quality threshold control
- Auto-train checkbox
- Real-time progress bar
- Detailed logging
- Results summary list
- Batch operations button

---

## 📂 **Directory Structure**

```
admin/data/youtube_llm_learning/
├── downloads/                     # Downloaded audio files
│   ├── Jeff Porcaro Rosanna.wav
│   ├── John Bonham Moby Dick.wav
│   └── download_metadata.json
│
├── analysis/                      # Feature extraction results
│   ├── Jeff_Porcaro_Rosanna_features.json
│   └── John_Bonham_Moby_Dick_features.json
│
├── datasets/                      # LLM training datasets
│   ├── Jeff_Porcaro_20251121_082500_dataset.json
│   └── John_Bonham_20251121_083000_dataset.json
│
├── models/                        # Trained models (future)
│   └── drumtrackai_porcaro_v1.pt
│
└── learning_pipeline_metadata.json  # Pipeline tracking
```

---

## 📊 **Dataset Format**

Each dataset is a JSON file with this structure:

```json
{
  "dataset_id": "Jeff_Porcaro_20251121_082500",
  "drummer": "Jeff Porcaro",
  "style": "rock",
  "created": "2025-11-21T08:25:00",
  "examples": [
    {
      "audio_features": {
        "tempo": 98.5,
        "beats": [0.0, 0.61, 1.22, 1.83, ...],
        "sections": [
          {"start": 0, "end": 8, "label": "intro"},
          {"start": 8, "end": 24, "label": "verse"},
          {"start": 24, "end": 40, "label": "chorus"}
        ],
        "timing_variance": 0.0023,
        "timing_stability": 0.97,
        "dynamic_range": 0.68,
        "pattern_complexity": 0.82
      },
      "source_file": "/path/to/audio.wav",
      "quality_score": 0.89
    }
  ]
}
```

---

## 🎯 **Workflow Examples**

### **Example 1: Learn from Single Drummer**

```python
# 1. Initialize
from admin.services.youtube_llm_learning_service import YouTubeLLMLearningPipeline
pipeline = YouTubeLLMLearningPipeline()

# 2. Run pipeline
result = pipeline.run_complete_pipeline(
    drummer_name="Jeff Porcaro",
    style="rock",
    max_videos=5
)

# 3. Check results
if result['success']:
    print(f"✅ Success!")
    print(f"   Files: {result['files_sourced']}")
    print(f"   Dataset: {result['dataset_file']}")
    print(f"   Time: {result['elapsed_time']:.1f}s")
```

### **Example 2: Batch Learn Multiple Styles**

```python
# Learn rock, jazz, and funk
drummers = [
    ("Jeff Porcaro", "rock"),
    ("Steve Gadd", "jazz"),
    ("Clyde Stubblefield", "funk"),
]

results = pipeline.run_batch_pipeline(drummers, max_videos_each=3)

# Summary
for result in results:
    if result['success']:
        print(f"✅ {result['drummer']}: {result['files_sourced']} files")
    else:
        print(f"❌ {result['drummer']}: {result['error']}")
```

### **Example 3: Custom Quality Threshold**

```python
# Only accept highest quality performances
session = pipeline.search_and_source_drummer(
    drummer_name="Neil Peart",
    style="rock",
    max_videos=10,
    quality_threshold=0.9  # Very strict (0.7 is default)
)

print(f"Accepted {session['files_downloaded']} of 10 videos")
```

---

## 🎨 **Quality Scoring**

The pipeline automatically scores audio quality to filter out poor recordings:

### **Quality Factors:**

1. **Onset Density** (70% weight)
   - Measures clarity of drum hits
   - Higher = clearer recording

2. **Tempo Confidence** (30% weight)
   - Detectable BPM = good recording
   - Unclear tempo = rejected

### **Threshold Recommendations:**

- **0.5**: Accept most recordings (quantity over quality)
- **0.7**: Balanced (recommended default)
- **0.9**: Only pristine studio recordings

---

## 🔬 **Feature Extraction Details**

### **Timing Features:**
- **Timing Variance**: Measures micro-timing variations (groove)
- **Timing Stability**: Consistency of beat placement
- **Swing Factor**: Detects triplet/swing feel

### **Velocity Features:**
- **Dynamic Range**: Difference between softest/loudest hits
- **Average Onset Strength**: Overall intensity level
- **Accent Patterns**: Identifies emphasized beats

### **Pattern Features:**
- **Complexity Score**: Based on density + variance + dynamics
- **Section Types**: Intro/verse/chorus/bridge/outro detection
- **Fill Locations**: Identifies drum fills and transitions

---

## ⚙️ **Configuration**

### **Environment Variables:**

```bash
# Audio-core binary location (auto-detected if not set)
export AUDIO_CORE_BIN=/path/to/audio-core.exe

# Base directory for pipeline data
export YOUTUBE_LLM_DATA_DIR=/custom/path

# YouTube API rate limiting (optional)
export YOUTUBE_DOWNLOAD_DELAY=2  # seconds between downloads
```

### **Pipeline Parameters:**

```python
pipeline = YouTubeLLMLearningPipeline(
    base_dir=Path("custom/path"),
    audio_core_bin="path/to/audio-core.exe"
)
```

---

## 🐛 **Troubleshooting**

### **Issue 1: "yt-dlp not available"**

**Fix:**
```bash
pip install yt-dlp
```

### **Issue 2: "audio-core binary not found"**

**Fix:**
```bash
# Build Rust audio-core
cd audio-core
cargo build --release

# Or set environment variable
export AUDIO_CORE_BIN=/path/to/audio-core.exe
```

### **Issue 3: "No videos downloaded"**

**Possible causes:**
- YouTube rate limiting (wait and retry)
- Network issues
- Invalid drummer name

**Fix:**
- Check internet connection
- Try different drummer/search query
- Lower quality threshold

### **Issue 4: "Quality threshold too high, no files accepted"**

**Fix:**
- Lower quality threshold to 0.5 or 0.6
- Check downloaded files manually in `downloads/` directory
- Some drummers may have fewer high-quality recordings

---

## 📈 **Performance**

### **Typical Timings (per video):**

| Stage | Time | Notes |
|-------|------|-------|
| YouTube Search | 2-5s | Depends on network |
| Download | 10-30s | Depends on video length |
| Quality Analysis | 5-10s | Rust audio-core |
| Feature Extraction | 10-20s | Full analysis |
| **Total** | **~30-60s** | Per video |

### **Batch Processing:**
- 5 videos × 30s = ~2.5 minutes
- 20 videos × 40s = ~13 minutes
- Includes 2s delay between downloads (YouTube rate limit)

---

## 🔄 **Integration with LLM Training**

### **Automatic Training Trigger:**

```python
# Set start_training=True to automatically trigger LLM training
result = pipeline.run_complete_pipeline(
    drummer_name="Jeff Porcaro",
    style="rock",
    max_videos=5,
    start_training=True  # ← Triggers LLM training tab
)
```

### **Manual Training:**

1. Run pipeline to create dataset
2. Go to **"LLM Training"** tab in admin
3. Select dataset file
4. Configure training parameters
5. Click "Start Training"

---

## 🎓 **Best Practices**

### **For Best Results:**

1. **Start Small**: Test with 3-5 videos first
2. **Quality Over Quantity**: Use 0.7-0.8 threshold
3. **Varied Styles**: Source different styles for general model
4. **Batch Wisely**: Don't run 100 videos at once (rate limiting)
5. **Check Logs**: Monitor pipeline output for issues

### **Dataset Curation:**

1. **Mix Styles**: Rock + Jazz + Funk = versatile model
2. **Multiple Drummers**: 3-5 drummers per style
3. **Quality Check**: Manually verify first few downloads
4. **Incremental Building**: Add drummers gradually

---

## 📚 **Example Scripts**

### **Script 1: Quick Test**

```python
# test_youtube_pipeline.py
from admin.services.youtube_llm_learning_service import quick_learn_from_youtube

result = quick_learn_from_youtube("Jeff Porcaro", "rock", 3)
print(f"✅ Done! Dataset: {result['dataset_file']}")
```

### **Script 2: Batch All Famous Drummers**

```python
# batch_learn_all.py
from admin.services.youtube_llm_learning_service import batch_learn_famous_drummers

print("🎯 Learning from all famous drummers...")
results = batch_learn_famous_drummers(max_videos_each=3)

successful = [r for r in results if r['success']]
print(f"\n✅ Complete: {len(successful)}/{len(results)} successful")
```

### **Script 3: Custom Drummer List**

```python
# custom_batch.py
from admin.services.youtube_llm_learning_service import YouTubeLLMLearningPipeline

pipeline = YouTubeLLMLearningPipeline()

# Your custom list
drummers = [
    ("Travis Barker", "punk"),
    ("Danny Carey", "progressive"),
    ("Carter Beauford", "rock"),
]

results = pipeline.run_batch_pipeline(drummers, max_videos_each=5)
```

---

## 🔮 **Future Enhancements**

**Planned Features:**
- [ ] Video analysis (not just audio)
- [ ] Automatic drummer recognition
- [ ] Genre classification
- [ ] Style transfer learning
- [ ] Real-time streaming analysis
- [ ] Community dataset sharing
- [ ] Cloud storage integration

---

## ✅ **Status**

**Current Status:** ✅ **PRODUCTION READY**

**What Works:**
- ✅ YouTube search and download
- ✅ Quality filtering
- ✅ Feature extraction via Rust
- ✅ Dataset building
- ✅ UI integration
- ✅ Batch processing
- ✅ Progress tracking
- ✅ Error handling

**Dependencies:**
- ✅ `yt-dlp` (install: `pip install yt-dlp`)
- ✅ `audio-core` (Rust binary - already built)
- ✅ Existing admin infrastructure (already exists)

---

## 📞 **Support**

**Documentation:**
- This file: Complete system guide
- `youtube_llm_learning_service.py`: Code documentation
- `youtube_learning_widget.py`: UI documentation

**Issues:**
- Check logs in admin interface
- Review `learning_pipeline_metadata.json`
- Verify `audio-core.exe` exists

---

**🎥 YouTube LLM Learning System v1.0.0 - Ready to Learn!** 🎥

**Built:** November 21, 2025  
**For:** DrumTracKAI v1.1.16.2  
**Status:** 🟢 **PRODUCTION READY**
