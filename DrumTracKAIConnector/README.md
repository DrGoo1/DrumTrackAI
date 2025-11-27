# DrumTracKAI Connector Plugin

**VST3 / AU / Standalone plugin that connects your DAW to the DrumTracKAI AI backend.**

## Features

- ✅ **Audio Analysis**: Captures audio from your DAW and sends it to DrumTracKAI for drum generation
- ✅ **MIDI Analysis**: Captures MIDI patterns and generates humanized drum tracks
- ✅ **Real-time Playback**: Generated drums play automatically in your DAW
- ✅ **Drag & Drop**: Export generated MIDI files directly to your DAW timeline
- ✅ **Lightweight**: All heavy processing happens on the backend server
- ✅ **Cross-platform**: Windows (VST3), macOS (VST3/AU)

---

## Requirements

### Build Requirements
- **CMake** 3.15 or later
- **JUCE Framework** 7.x
- **C++ Compiler**:
  - Windows: Visual Studio 2019/2022
  - macOS: Xcode 12+
- **Python 3.11** (for backend server)

### Runtime Requirements
- DrumTracKAI backend server running (default: `http://localhost:8000`)

---

## Setup

### 1. Clone JUCE

```bash
cd f:/DrumTracKAI_v1.1.16_Clean/deps
git clone --depth=1 --branch=7.0.9 https://github.com/juce-framework/JUCE.git
```

### 2. Configure CMake

**Windows:**
```bash
cd f:/DrumTracKAI_v1.1.16_Clean/DrumTracKAIConnector
mkdir build
cd build
cmake .. -G "Visual Studio 17 2022" -A x64
```

**macOS:**
```bash
cd /path/to/DrumTracKAIConnector
mkdir build
cd build
cmake .. -G Xcode
```

### 3. Build

**Windows:**
```bash
cmake --build . --config Release
```

**macOS:**
```bash
cmake --build . --config Release
```

### 4. Install Plugin

The plugin will be automatically copied to:
- **Windows VST3**: `C:\Program Files\Common Files\VST3\`
- **macOS VST3**: `~/Library/Audio/Plug-Ins/VST3/`
- **macOS AU**: `~/Library/Audio/Plug-Ins/Components/`

---

## Usage

### 1. Start DrumTracKAI Backend

```bash
cd f:/DrumTracKAI_v1.1.16_Clean
python drumtrackai_api_server_clean.py
```

Backend runs at: `http://localhost:8000`

### 2. Load Plugin in DAW

1. Open your DAW (Reaper, Ableton, FL Studio, Logic, etc.)
2. Create a new MIDI track
3. Load "DrumTracKAI Connector" as a MIDI effect/instrument
4. Set input to your audio/MIDI source

### 3. Generate Drums

**From Audio:**
1. Play some audio in your DAW
2. Click "Analyze Last Audio" in the plugin
3. Wait for processing (5-30 seconds)
4. Drums will play automatically!

**From MIDI:**
1. Record or play MIDI in your DAW
2. Click "Analyze MIDI" in the plugin
3. Get AI-generated humanized drums

### 4. Export MIDI

- Drag the green MIDI box to your DAW timeline
- Edit the MIDI as needed
- Route to your favorite drum instrument

---

## Plugin Settings

### Server URL
Default: `http://localhost:8000/api/generate`

For remote server:
```
https://your-drumtrackai-server.com/api/generate
```

### API Key
Optional authentication key if your backend requires it.

---

## Architecture

```
DAW Audio/MIDI
    ↓
Plugin (captures 30 seconds)
    ↓
HTTP POST → DrumTracKAI Backend
    ↓
AI Analysis + Generation
    ↓
MIDI Response ← Backend
    ↓
Plugin outputs MIDI
    ↓
DAW plays drums
```

---

## Backend API Contract

The plugin expects this JSON contract:

**Request:**
```json
{
  "api_key": "optional",
  "mode": "audio",  // or "midi"
  "bpm": 120.0,
  "time_sig": "4/4",
  "audio_wav_base64": "...",  // if mode == "audio"
  "midi_smf_base64": "..."    // if mode == "midi"
}
```

**Response:**
```json
{
  "ok": true,
  "status_message": "success",
  "midi_smf_base64": "..."  // Standard MIDI File in base64
}
```

---

## Troubleshooting

### Plugin not found in DAW
- Check plugin was copied to correct folder
- Rescan plugins in your DAW
- On macOS: check Gatekeeper permissions

### "Connection failed" error
- Ensure backend server is running
- Check Server URL is correct
- Verify firewall allows localhost:8000

### No drums playing
- Check MIDI output is routed to an instrument
- Verify DAW transport is playing
- Try clicking "Clear" and regenerating

---

## Development

### Project Structure
```
DrumTracKAIConnector/
  CMakeLists.txt          # Build configuration
  Source/
    PluginProcessor.h/cpp # Main audio processor
    PluginEditor.h/cpp    # GUI
    NetworkClient.h/cpp   # HTTP client
    MidiUtils.h/cpp       # MIDI conversion
```

### Adding Features
- Modify `PluginEditor.cpp` for UI changes
- Update `PluginProcessor.cpp` for audio/MIDI processing
- Adjust `NetworkClient.cpp` for API changes

---

## License

Part of DrumTracKAI v1.1.16  
© 2025 Umbo Gumbo LLC

---

## Credits

- **JUCE Framework**: https://juce.com
- **DrumTracKAI**: AI drum generation system
- **Developed for**: Professional music production workflows
