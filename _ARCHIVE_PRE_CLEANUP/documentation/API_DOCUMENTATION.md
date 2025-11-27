# 📡 DrumTracKAI API Documentation

**Complete REST API Reference for v1.1.16**

---

## 🌐 Base URL

```
Development: http://localhost:8000
Production: <your-production-url>
```

All endpoints return JSON responses unless otherwise specified.

---

## 📤 File Operations

### **Upload Audio File**

```http
POST /api/upload
POST /files/upload  (alias)
```

**Request:**
- Content-Type: `multipart/form-data`
- Field name: `file`
- Supported formats: MP3, WAV, FLAC, AAC
- Max size: 500MB

**Response:**
```json
{
  "success": true,
  "key": "1700000000000-filename.mp3",
  "file_id": "1700000000000-filename.mp3",
  "waveform": {
    "sr": 44100,
    "peaks": [0.1, 0.3, 0.5, ...],
    "key": "1700000000000-filename.mp3",
    "duration": 180.5
  },
  "message": "File uploaded successfully"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/audio.mp3"
```

---

### **Get Waveform Data**

```http
GET /files/waveform?key={file_key}&width={width}
```

**Parameters:**
- `key` (required): File key from upload response
- `width` (optional): Desired peak count (default: 1000)

**Response:**
```json
{
  "sr": 44100,
  "peaks": [0.1, 0.3, 0.5, ...],
  "key": "file_key",
  "duration": 180.5
}
```

---

### **Stream Audio File**

```http
GET /files/audio?key={file_key}
```

**Parameters:**
- `key` (required): File key from upload response

**Response:**
- Content-Type: `audio/mpeg` (or appropriate for file type)
- Audio file stream

---

## 🎵 Audio Analysis

### **Analyze Audio (Full Analysis)**

```http
POST /api/analyze
```

**Request:**
```json
{
  "file_id": "file_key"
}
```

**Response:**
```json
{
  "success": true,
  "job_id": "analysis_job_id",
  "status": "complete",
  "tempo": 120.5,
  "estimated_time": "0s"
}
```

---

### **Get Analysis Results**

```http
GET /api/results/{job_id}
```

**Response:**
```json
{
  "job_id": "analysis_job_id",
  "sophistication": "87.5%",
  "accuracy": "93.2%",
  "tempo": "120.5 BPM",
  "patterns": ["Detected Pattern"],
  "confidence": "high",
  "drummer_style": "Dynamic",
  "bpm_value": 120.5,
  "beats": [0.0, 0.5, 1.0, 1.5, ...],
  "onsets": [0.0, 0.125, 0.25, ...]
}
```

---

### **Detect Tempo**

```http
GET /analyze/tempo?key={file_key}
```

**Parameters:**
- `key` (required): File key

**Response:**
```json
{
  "tempo": 120.5,
  "beats": [0.0, 0.5, 1.0, 1.5, 2.0, ...]
}
```

**Example:**
```bash
curl "http://localhost:8000/analyze/tempo?key=1700000000000-song.mp3"
```

---

### **Detect Onsets**

```http
GET /analyze/onsets?key={file_key}
```

**Parameters:**
- `key` (required): File key

**Response:**
```json
{
  "sr": 44100,
  "onsets": [0.0, 0.125, 0.345, 0.567, ...]
}
```

---

### **Analyze Tempo Per Section**

```http
POST /analyze/tempo_sections
```

**Request:**
```json
{
  "key": "file_key",
  "sections": [
    {"start": 0.0, "end": 10.0},
    {"start": 10.0, "end": 20.0},
    {"start": 20.0, "end": 30.0}
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "start": 0.0,
      "end": 10.0,
      "tempo": 120.5,
      "confidence": 0.85,
      "candidates": [120.5, 241.0, 60.25]
    },
    {
      "start": 10.0,
      "end": 20.0,
      "tempo": 122.0,
      "confidence": 0.92,
      "candidates": [122.0, 244.0, 61.0]
    }
  ],
  "global_tempo": 121.25
}
```

---

### **Align Sections to Beats**

```http
POST /align/sections
```

**Request:**
```json
{
  "key": "file_key",
  "sections": [
    {"start": 1.23, "end": 5.67},
    {"start": 5.67, "end": 10.89}
  ]
}
```

**Response:**
```json
{
  "tempo": 120.0,
  "sections": [
    {"start": 1.0, "end": 6.0},
    {"start": 6.0, "end": 11.0}
  ]
}
```

---

## 🥁 Drummer Profiles (NEW!)

### **List All Drummers**

```http
GET /api/drummers
```

**Response:**
```json
{
  "drummers": [
    {
      "id": "studio_groove_master",
      "display_name": "Studio Groove Master",
      "tagline": "Precision pocket playing with sophisticated ghost notes",
      "genre_tags": ["Jazz Fusion", "Pop", "Rock", "Session Work"],
      "difficulty": "Advanced",
      "icon": "🎩",
      "color": "#4F46E5",
      "description": "Master of the pocket with unmatched control...",
      "best_for": [
        "Steely Dan style tracks",
        "Toto grooves",
        "Session-quality recording"
      ],
      "signature_techniques": [
        "Half-time shuffle",
        "Ghost notes",
        "Ride cymbal mastery"
      ]
    },
    // ... 9 more drummers
  ]
}
```

**Example:**
```bash
curl http://localhost:8000/api/drummers
```

---

### **Get Specific Drummer Details**

```http
GET /api/drummers/{drummer_id}
```

**Parameters:**
- `drummer_id`: One of the 10 DrumTrackAI drummer IDs

**Response:**
```json
{
  "id": "studio_groove_master",
  "display_name": "Studio Groove Master",
  "tagline": "Precision pocket playing...",
  "genre_tags": ["Jazz Fusion", "Pop", "Rock"],
  "difficulty": "Advanced",
  "icon": "🎩",
  "color": "#4F46E5",
  "description": "Master of the pocket...",
  "best_for": ["Steely Dan style tracks", ...],
  "signature_techniques": ["Half-time shuffle", ...],
  "characteristics": {
    "timing_precision_mean": 0.86,
    "micro_timing_tendency": 0.02,
    "tempo_stability": 0.63,
    "groove_score": 0.82,
    "ghost_note_density": 0.75,
    "ride_preference": 0.70,
    "swing_comfort": 0.85,
    "half_time_mastery": 0.95,
    "technical_precision": 0.86,
    "dynamics_range": 0.85,
    // ... 40+ more characteristics
  }
}
```

**Available Drummer IDs:**
- `studio_groove_master`
- `metal_atomic_clock`
- `progressive_polymath`
- `funk_machine`
- `jazz_innovator`
- `rock_powerhouse`
- `alternative_innovator`
- `world_fusion_master`
- `hip_hop_architect`
- `metal_chaos_master`

**Example:**
```bash
curl http://localhost:8000/api/drummers/studio_groove_master
```

---

## 🎼 Pattern Generation

### **Generate with Drummer Profile (NEW!)**

```http
POST /api/generate_with_drummer
```

**Request:**
```json
{
  "drummer_id": "studio_groove_master",
  "bpm": 161.0,
  "sections": [
    {
      "start": 0.0,
      "end": 10.0,
      "fill_in": false,
      "fill_out": true,
      "label": "intro",
      "density": 0.7
    },
    {
      "start": 10.0,
      "end": 25.0,
      "fill_in": false,
      "fill_out": false,
      "label": "verse",
      "density": 0.6
    }
  ],
  "song_analysis": {
    "swing_amount": 0.15,
    "syncopation_level": 0.70
  },
  "export_midi": false
}
```

**Request Fields:**
- `drummer_id` (required): Drummer to use for generation
- `bpm` (required): Tempo in beats per minute
- `sections` (required): Array of sections to generate
  - `start`: Section start time in seconds
  - `end`: Section end time in seconds
  - `fill_in`: Add fill at beginning (default: false)
  - `fill_out`: Add fill at end (default: false)
  - `label`: Section type - "intro", "verse", "chorus", "bridge", "outro"
  - `density`: Note density override 0.0-1.0 (optional)
- `song_analysis` (optional): Additional song characteristics
  - `swing_amount`: Swing feel 0.0-0.35
  - `syncopation_level`: Syncopation 0.0-1.0
  - `note_density`: "low", "medium", "high"
- `export_midi` (optional): Include base64 MIDI (default: false)

**Response:**
```json
{
  "notes": [
    {
      "time": 0.0,
      "lane": "kick",
      "vel": 0.95
    },
    {
      "time": 0.125,
      "lane": "hihat",
      "vel": 0.65
    },
    {
      "time": 0.25,
      "lane": "snare",
      "vel": 0.90
    },
    // ... hundreds more notes
  ],
  "midi_base64": null,
  "drummer_id": "studio_groove_master",
  "params_used": {
    "style": "jazz",
    "swing_preset": "heavy",
    "vel_preset": "accent24",
    "fill_preset": "tomrun",
    "density": 0.75,
    "humanize": 0.14
  }
}
```

**Response Fields:**
- `notes`: Array of generated MIDI notes
  - `time`: Note time in seconds
  - `lane`: Drum lane - "kick", "snare", "hihat", "ohat", "ride", "tom", "crash", "clap"
  - `vel`: Velocity 0.0-1.0
- `midi_base64`: Base64-encoded MIDI file (if requested)
- `drummer_id`: Drummer used for generation
- `params_used`: Actual parameters applied to Rust generator

**Example:**
```bash
curl -X POST http://localhost:8000/api/generate_with_drummer \
  -H "Content-Type: application/json" \
  -d '{
    "drummer_id": "studio_groove_master",
    "bpm": 120,
    "sections": [{
      "start": 0,
      "end": 8,
      "fill_in": false,
      "fill_out": false,
      "label": "verse",
      "density": 0.7
    }]
  }'
```

---

### **Generate (Generic, No Drummer)**

```http
POST /dcsm/generate
```

**Request:**
```json
{
  "bpm": 120.0,
  "density": 0.7,
  "swing": 0.0,
  "humanize": 0.1,
  "seed": 42,
  "sections": [
    {
      "start": 0.0,
      "end": 8.0,
      "fill_in": false,
      "fill_out": false,
      "density": 0.7
    }
  ]
}
```

**Response:**
```json
{
  "notes": [
    {"time": 0.0, "lane": "kick", "vel": 0.95},
    {"time": 0.125, "lane": "hihat", "vel": 0.65},
    // ...
  ],
  "midi_base64": null
}
```

---

## 🎚️ Sectionization

### **Smart Sectionization**

```http
GET /dcsm/sectionize?key={file_key}&bpm={bpm}&mode={mode}&min_bars={min}&max_bars={max}
```

**Parameters:**
- `key` (required): File key
- `bpm` (optional): Tempo hint (default: auto-detect)
- `mode` (optional): "bars" or "smart" (default: "smart")
- `min_bars` (optional): Minimum section length in bars (default: 4)
- `max_bars` (optional): Maximum section length in bars (default: 16)

**Response:**
```json
{
  "sections": [
    {
      "start": 0.0,
      "end": 10.5,
      "label": "intro",
      "confidence": 0.85
    },
    {
      "start": 10.5,
      "end": 28.0,
      "label": "verse",
      "confidence": 0.92
    },
    {
      "start": 28.0,
      "end": 45.5,
      "label": "chorus",
      "confidence": 0.88
    },
    {
      "start": 45.5,
      "end": 63.0,
      "label": "verse",
      "confidence": 0.90
    },
    {
      "start": 63.0,
      "end": 80.5,
      "label": "chorus",
      "confidence": 0.93
    },
    {
      "start": 80.5,
      "end": 100.0,
      "label": "outro",
      "confidence": 0.78
    }
  ],
  "bpm": 120.5
}
```

**Labels:**
- `intro`: Introduction section
- `verse`: Verse section
- `chorus`: Chorus section
- `bridge`: Bridge section
- `outro`: Ending section

**Example:**
```bash
curl "http://localhost:8000/dcsm/sectionize?key=file.mp3&mode=smart&min_bars=4&max_bars=16"
```

---

## 💾 Session Management

### **Save Session**

```http
POST /session/{session_id}
```

**Request:**
```json
{
  "bpm": 120,
  "loop": {
    "enabled": true,
    "start": 0.0,
    "end": 16.0
  },
  "tracks": [
    {
      "key": "file_key",
      "name": "Track 1",
      "color": "#4F46E5",
      "peaks": [...],
      "sr": 44100,
      "seconds": 180.5
    }
  ],
  "sections": [
    {
      "id": "section_1",
      "start": 0.0,
      "end": 10.0,
      "density": 0.7,
      "fillIn": false,
      "fillOut": true,
      "label": "intro"
    }
  ],
  "notes": [
    {"time": 0.0, "lane": "kick", "vel": 0.95},
    {"time": 0.125, "lane": "hihat", "vel": 0.65}
  ]
}
```

**Response:**
```json
{
  "ok": true
}
```

---

### **Load Session**

```http
GET /session/{session_id}
```

**Response:**
Same structure as save request - returns saved session data.

---

## 🏎️ Performance Benchmarking

### **Benchmark Peak Extraction**

```http
GET /bench/peaks?key={file_key}&impl={impl}
```

**Parameters:**
- `key` (required): File key
- `impl` (optional): "rust", "python", or "auto" (default: "auto")

**Response:**
```json
{
  "impl": "rust",
  "ms": 65,
  "peaks": 1000,
  "width": 1000
}
```

---

### **Benchmark Analysis**

```http
GET /bench/analysis?key={file_key}&impl={impl}
```

**Parameters:**
- `key` (required): File key
- `impl` (optional): "rust", "python", or "auto" (default: "auto")

**Response:**
```json
{
  "impl": "rust",
  "ms": 180,
  "tempo": 120.5,
  "beats": [0.0, 0.5, 1.0, ...],
  "onsets": [0.0, 0.125, 0.25, ...]
}
```

---

### **Benchmark Generation**

```http
GET /bench/generate?bpm={bpm}&bars={bars}&style={style}
```

**Parameters:**
- `bpm` (optional): Tempo (default: 120)
- `bars` (optional): Number of bars (default: 8)
- `style` (optional): Style name (default: "rock")

**Response:**
```json
{
  "impl": "rust",
  "ms": 2,
  "note_count": 128,
  "bpm": 120,
  "bars": 8,
  "style": "rock"
}
```

---

## 🏥 Health Check

### **Health Status**

```http
GET /healthz
```

**Response:**
```json
{
  "ok": true,
  "ts": 1700000000.123
}
```

---

### **API Status**

```http
GET /api/status
```

**Response:**
```json
{
  "status": "operational",
  "version": "1.1.16",
  "rust_available": true,
  "features": {
    "audio_upload": true,
    "tempo_detection": true,
    "sectionization": true,
    "pattern_generation": true,
    "drummer_profiles": true
  }
}
```

---

## ❌ Error Responses

All error responses follow this format:

```json
{
  "error": "Error description",
  "status": 400
}
```

### **Common Error Codes:**

**400 Bad Request**
- Missing required parameters
- Invalid JSON body
- Invalid file format

**404 Not Found**
- File key doesn't exist
- Drummer ID not found
- Session not found

**500 Internal Server Error**
- Analysis failed
- Generation failed
- Database error

---

## 📊 Rate Limiting

Currently no rate limiting implemented. Production deployment should add:
- Per-IP limits
- Per-user limits (with authentication)
- Upload size/frequency limits

---

## 🔐 Authentication

Currently no authentication required. Production deployment should add:
- API keys
- OAuth2
- JWT tokens
- User accounts

---

## 🎯 Example Workflows

### **Complete Upload → Analyze → Generate Workflow**

```bash
# 1. Upload file
UPLOAD_RESPONSE=$(curl -X POST http://localhost:8000/api/upload \
  -F "file=@song.mp3")
FILE_KEY=$(echo $UPLOAD_RESPONSE | jq -r '.key')

# 2. Analyze tempo
TEMPO_RESPONSE=$(curl "http://localhost:8000/analyze/tempo?key=$FILE_KEY")
BPM=$(echo $TEMPO_RESPONSE | jq -r '.tempo')

# 3. Get smart sections
SECTIONS=$(curl "http://localhost:8000/dcsm/sectionize?key=$FILE_KEY&mode=smart")

# 4. List drummers
DRUMMERS=$(curl "http://localhost:8000/api/drummers")

# 5. Generate with drummer
curl -X POST http://localhost:8000/api/generate_with_drummer \
  -H "Content-Type: application/json" \
  -d "{
    \"drummer_id\": \"studio_groove_master\",
    \"bpm\": $BPM,
    \"sections\": [{\"start\": 0, \"end\": 8, \"label\": \"verse\", \"fill_out\": false}]
  }"
```

---

## 📚 Related Documentation

- [README_MAIN.md](README_MAIN.md) - Overview & quick start
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [DRUMMER_INTEGRATION.md](DRUMMER_INTEGRATION.md) - Drummer system details
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues

---

**API Version:** 1.1.16  
**Last Updated:** November 16, 2024  
**Status:** ✅ Production Ready
