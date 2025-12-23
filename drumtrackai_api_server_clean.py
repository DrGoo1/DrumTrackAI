# drumtrackai_api_server_clean.py
import os, asyncio, logging, mimetypes, time, shutil, json, subprocess
import sqlite3
from pathlib import Path
import numpy as np

from aiohttp import web
import aiohttp_cors
import asyncio
import json
import base64
import datetime
from pydantic import BaseModel
from backend.articulation_selector import select_articulation_for_note
from backend.render_to_plugin_midi import render_articulated_notes_to_midi

try:
    import soundfile as sf  # pip install soundfile
except Exception:
    sf = None

try:
    import librosa
except Exception:
    librosa = None

# ---------- Config ----------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", "8000"))
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = (BASE_DIR / "uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

SAMPLE_DB_PATH = Path(os.getenv("SAMPLE_DB_PATH", str((BASE_DIR / "admin" / "drumtrackai.db").resolve())))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
LOG = logging.getLogger("drumtrackai")

# Rust integration configuration
AUDIO_CORE_BIN = os.getenv("AUDIO_CORE_BIN", "audio-core")
USE_RUST = os.getenv("USE_RUST", "0") == "1"
AUDIO_CORE_MODE = os.getenv("AUDIO_CORE_MODE", "auto")  # auto, cli, pyo3

# Try to import PyO3 audio_core module
audio_core_rust = None
if USE_RUST and AUDIO_CORE_MODE in ["auto", "pyo3"]:
    try:
        import audio_core as audio_core_rust
        LOG.info("PyO3 audio_core module loaded successfully")
    except ImportError:
        if AUDIO_CORE_MODE == "pyo3":
            LOG.error("PyO3 mode requested but audio_core module not available")
        else:
            LOG.info("PyO3 audio_core not available, falling back to CLI")
        audio_core_rust = None

def run_audio_core(args: list) -> dict:
    """Run audio-core via PyO3 or CLI subprocess and return JSON result"""
    # Try PyO3 first if available and mode allows
    if audio_core_rust and AUDIO_CORE_MODE in ["auto", "pyo3"]:
        try:
            return run_audio_core_pyo3(args)
        except Exception as e:
            if AUDIO_CORE_MODE == "pyo3":
                raise Exception(f"PyO3 audio-core error: {e}")
            LOG.warning(f"PyO3 failed, falling back to CLI: {e}")
    
    # Fallback to CLI subprocess
    return run_audio_core_cli(args)

def run_audio_core_pyo3(args: list) -> dict:
    """Run audio-core via PyO3 in-process calls"""
    if not audio_core_rust:
        raise Exception("PyO3 audio_core module not available")
    
    cmd = args[0] if args else ""
    
    if cmd == "peaks":
        path = args[1]
        max_points = int(args[3]) if len(args) > 3 else 2000
        peaks = audio_core_rust.audio_peaks(path, max_points)
        return {"peaks": peaks}
    
    elif cmd == "analyze":
        path = args[1]
        min_bpm = float(args[3]) if len(args) > 3 else 60.0
        max_bpm = float(args[5]) if len(args) > 5 else 200.0
        tempo, beats, onsets = audio_core_rust.audio_analyze(path, min_bpm, max_bpm)
        return {"tempo": tempo, "beats": beats, "onsets": onsets}
    
    elif cmd == "sectionize-smart":
        path = args[1]
        bpm = float(args[3])
        min_bars = int(args[5])
        max_bars = int(args[7])
        sections = audio_core_rust.audio_sectionize_smart(path, bpm, min_bars, max_bars)
        return {"sections": [{"start": s[0], "end": s[1], "label": s[2]} for s in sections]}
    
    elif cmd == "generate":
        style = args[2]
        label = args[4]
        bars = int(args[6])
        bpm = float(args[8])
        seed = int(args[10]) if len(args) > 10 else 42
        midi_b64 = audio_core_rust.drum_generate(style, label, bars, bpm, seed)
        return {"midi": midi_b64}
    
    else:
        raise Exception(f"Unknown PyO3 command: {cmd}")

def run_audio_core_cli(args: list) -> dict:
    """Run audio-core Rust binary via CLI subprocess and return JSON result"""
    bin_path = shutil.which(AUDIO_CORE_BIN) or AUDIO_CORE_BIN
    try:
        proc = subprocess.run([bin_path] + args, capture_output=True, text=True, timeout=30)
        if proc.returncode != 0:
            raise Exception(f"audio-core failed (code {proc.returncode}): {proc.stderr.strip()}")
        return json.loads(proc.stdout)
    except subprocess.TimeoutExpired:
        raise Exception("audio-core timed out")
    except json.JSONDecodeError as e:
        raise Exception(f"bad json from audio-core: {e}")
    except Exception as e:
        raise Exception(f"audio-core error: {e}")

# Benchmarking endpoints
async def bench_peaks(request):
    key = request.query.get("key")
    impl = request.query.get("impl", "both")
    max_points = int(request.query.get("max_points", "3000"))
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    out = {}
    
    if impl in ("python", "both"):
        try:
            t0 = time.perf_counter()
            # Python fallback implementation
            if sf:
                y, sr = sf.read(str(path), dtype="float32", always_2d=False)
                if y.ndim == 2:
                    y = y.mean(axis=1)
                # Simple peak extraction
                if len(y) > max_points:
                    step = len(y) // max_points
                    peaks = [max(abs(y[i:i+step])) if i+step < len(y) else abs(y[i]) for i in range(0, len(y), step)]
                else:
                    peaks = [abs(x) for x in y]
                # Normalize
                max_val = max(peaks) if peaks else 1.0
                peaks = [p/max_val for p in peaks]
            else:
                peaks = [0.0] * min(max_points, 1000)
            
            out["python_ms"] = int((time.perf_counter() - t0) * 1000)
        except Exception as e:
            out["python_error"] = str(e)
    
    if impl in ("rust", "both") and USE_RUST:
        try:
            t0 = time.perf_counter()
            result = run_audio_core(["peaks", str(path), "--max-points", str(max_points)])
            out["rust_ms"] = int((time.perf_counter() - t0) * 1000)
        except Exception as e:
            out["rust_error"] = str(e)
    
    return web.json_response(out)


async def dcsm_export_midi(request: web.Request):
    """Export logical drum notes with articulationId to plugin-specific MIDI.

    Expected JSON body:
      {
        "plugin": "jamstix" | "sd3" | "ssd5" | ...,
        "ppq": 480,
        "notes": [
          {"t0": int, "t1": int, "pitch": int, "vel": int, "chan": int,
           "articulationId": str | null},
          ...
        ]
      }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)

    try:
        result = render_articulated_notes_to_midi(data)
        filename = f"dcsm_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mid"
        return web.json_response({
            "plugin": result.get("plugin"),
            "midi_base64": result.get("midi_base64"),
            "ticks_per_beat": result.get("ticks_per_beat"),
            "filename": filename,
        })
    except Exception as e:
        LOG.error(f"dcsm_export_midi failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def bench_analysis(request):
    key = request.query.get("key")
    impl = request.query.get("impl", "both")
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    out = {}
    
    if impl in ("python", "both"):
        try:
            t0 = time.perf_counter()
            if sf and librosa:
                y, sr = sf.read(str(path), dtype="float32", always_2d=False)
                if y.ndim == 2:
                    y = y.mean(axis=1)
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
            else:
                tempo, beats, onsets = 120.0, [], []
            
            out["python_ms"] = int((time.perf_counter() - t0) * 1000)
        except Exception as e:
            out["python_error"] = str(e)
    
    if impl in ("rust", "both") and USE_RUST:
        try:
            t0 = time.perf_counter()
            result = run_audio_core(["analyze", str(path)])
            out["rust_ms"] = int((time.perf_counter() - t0) * 1000)
        except Exception as e:
            out["rust_error"] = str(e)
    
    return web.json_response(out)

async def bench_generate(request):
    bpm = float(request.query.get("bpm", "120"))
    bars = int(request.query.get("bars", "8"))
    style = request.query.get("style", "rock")
    
    out = {}
    
    if USE_RUST:
        try:
            t0 = time.perf_counter()
            result = run_audio_core([
                "generate", 
                "--style", style,
                "--label", "verse",
                "--bars", str(bars),
                "--bpm", str(bpm),
                "--seed", "42"
            ])
            out["rust_ms"] = int((time.perf_counter() - t0) * 1000)
            out["notes"] = len(result.get("notes", []))
        except Exception as e:
            out["rust_error"] = str(e)
    else:
        out["rust_error"] = "Rust not enabled"
    
    return web.json_response(out)

# ---------- Helpers ----------
def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)

def compute_waveform(path: Path, max_points: int = 3000):
    # Try Rust implementation first if enabled
    if USE_RUST:
        try:
            result = run_audio_core(["peaks", str(path), "--max-points", str(max_points)])
            result["key"] = str(path.relative_to(UPLOAD_DIR))
            return result
        except Exception as e:
            LOG.warning(f"Rust waveform failed, falling back to Python: {e}")
    
    # Python fallback implementation
    if sf is None:
        # Fallback mock waveform if soundfile not available
        return {
            "sr": 44100,
            "peaks": [float(i % 100) / 100.0 for i in range(1000)],
            "key": str(path.relative_to(UPLOAD_DIR)),
            "duration": 30.5
        }

    data, sr = sf.read(str(path), dtype="float32", always_2d=False)
    # Prepare mono and stereo references
    left = None
    right = None
    if hasattr(data, 'ndim') and data.ndim == 2 and data.shape[1] >= 2:
        left = data[:, 0]
        right = data[:, 1]
        mono = data.mean(axis=1)
    else:
        mono = data if hasattr(data, '__len__') else np.asarray([])
    n = len(mono)
    duration = float(n) / float(sr) if sr and sr > 0 else 0.0

    def downsample_peaks(x: np.ndarray):
        if x is None or len(x) == 0:
            return []
        step = max(1, len(x) // max_points)
        trimmed = x[: step * max_points]
        if len(trimmed) == 0:
            return []
        abs_data = np.abs(trimmed)
        peaks = np.max(abs_data.reshape(-1, step), axis=1).tolist()
        m = float(np.max(peaks)) if len(peaks) else 1.0
        if m <= 1e-8:
            m = 1.0
        return (np.asarray(peaks) / m).clip(0.0, 1.0).tolist()

    peaks_mono = downsample_peaks(mono)
    peaks_l = downsample_peaks(left) if left is not None else None
    peaks_r = downsample_peaks(right) if right is not None else None

    result = {"sr": int(sr), "peaks": peaks_mono, "key": str(path.relative_to(UPLOAD_DIR)), "duration": duration}
    if peaks_l is not None and peaks_r is not None:
        result["peaksL"] = peaks_l
        result["peaksR"] = peaks_r
    return result

# ---------- Routes ----------
async def healthz(_):
    return web.json_response({"ok": True, "ts": time.time()})

async def upload(request: web.Request):
    reader = await request.multipart()
    part = await reader.next()
    if part is None or part.name != "file":
        return web.json_response({"error": "missing file field"}, status=400)

    filename = safe_name(part.filename or f"file-{int(time.time()*1000)}.wav")
    key = f"uploads/{int(time.time()*1000)}-{filename}"
    dest = (UPLOAD_DIR / key)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with dest.open("wb") as f:
        while True:
            chunk = await part.read_chunk()  # 8192 bytes by default
            if not chunk:
                break
            f.write(chunk)

    # Generate waveform data
    try:
        waveform = compute_waveform(dest)
    except Exception as e:
        LOG.warning(f"Waveform generation failed: {e}, using mock data")
        waveform = {
            "sr": 44100,
            "peaks": [float(i % 100) / 100.0 for i in range(1000)],
            "key": key,
            "duration": 30.5
        }

    return web.json_response({
        "success": True,
        "key": key,
        "file_id": key,
        "waveform": waveform,
        "message": "File uploaded successfully"
    })

async def waveform(request: web.Request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "missing key"}, status=400)
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "not found"}, status=404)
    try:
        wf = compute_waveform(path)
        return web.json_response(wf)
    except Exception as e:
        LOG.exception("waveform error")
        return web.json_response({"error": str(e)}, status=500)

async def audio_file(request: web.Request):
    # Optional (for Tone.Player). Not strictly needed for upload→waveform.
    key = request.query.get("key")
    if not key:
        return web.Response(status=400, text="missing key")
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.Response(status=404, text="not found")
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return web.FileResponse(str(path), headers={"Content-Type": mime})

# Legacy API endpoints for compatibility
async def api_status(_):
    return web.json_response({
        'status': 'online',
        'expert_model': '88.7% sophistication',
        'mvsep': 'available',
        'signature_songs': 3,
        'classic_beats': 40
    })

def bpm_to_tempo_us_per_beat(bpm_val: float) -> int:
    return int(60_000_000 / max(1.0, bpm_val))

def sec_to_ticks(dt_sec: float, us_per_beat: int, ppq: int) -> int:
    return int((dt_sec * 1_000_000) / max(1, us_per_beat) * ppq)

async def generate_midi_sections(request: web.Request):
    """Generate multi-track Type-1 drum MIDI using per-section beats.
    Tracks: tempo (meta), kick, snare, hihat. 4/4 downbeat heuristic for kick.
    """
    if mido is None:
        return web.json_response({"error": "mido not installed. pip install mido"}, status=500)
    if librosa is None or sf is None or np is None:
        return web.json_response({"error": "analysis libraries not available"}, status=500)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)

    key = data.get("key")
    sections = data.get("sections", [])
    options = data.get("options", {})
    swing = float(options.get("swing", 0.0))  # 0.0 (no swing) .. 0.6 (heavy)
    swing = max(0.0, min(0.6, swing))
    velocity_profile = str(options.get("velocity", "flat"))  # 'flat' | 'accent24'
    velocity_lanes = options.get("velocityLanes", {}) or {}
    vel_kick = str(velocity_lanes.get("kick", "flat"))       # 'flat' | 'punchy'
    vel_snare = str(velocity_lanes.get("snare", velocity_profile))  # 'flat' | 'accent24' | 'ghost'
    vel_hh = str(velocity_lanes.get("hihat", velocity_profile))     # 'flat' | 'accent24'
    vel_ride = str(velocity_lanes.get("ride", "flat"))       # 'flat' | 'washy'
    use_ride = bool(options.get("ride", False))
    use_crash = bool(options.get("crash", True))
    fill_type = str(options.get("fill", "none"))  # 'none'|'random'|'tomrun'|'snarebuzz'|'edmriser'
    fill_bars = int(options.get("fillBars", 1))
    fill_bars = 1 if fill_bars not in (1, 2) else fill_bars
    if not key or not isinstance(sections, list):
        return web.json_response({"error": "key and sections required"}, status=400)

    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)

    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if hasattr(y, 'ndim') and y.ndim == 2:
            y = y.mean(axis=1)
        n = len(y)
        dur = float(n) / float(sr) if sr else 0.0

        mid = mido.MidiFile(ticks_per_beat=480)
        tempo_track = mido.MidiTrack(); mid.tracks.append(tempo_track)
        kick_track = mido.MidiTrack(); mid.tracks.append(kick_track)
        snare_track = mido.MidiTrack(); mid.tracks.append(snare_track)
        hihat_track = mido.MidiTrack(); mid.tracks.append(hihat_track)
        ride_track = mido.MidiTrack(); mid.tracks.append(ride_track)
        crash_track = mido.MidiTrack(); mid.tracks.append(crash_track)

        # Build event lists per track with absolute times in seconds
        tempo_events = []  # (t_sec, tempo_us_per_beat)
        kick_events = []   # (t_sec, is_on)
        snare_events = []
        hihat_events = []
        ride_events = []
        crash_events = []

        for s in sections:
            s0 = float(max(0.0, s.get('start', 0.0)))
            s1 = float(min(dur, s.get('end', dur)))
            if s1 <= s0:
                continue
            i0 = int(s0 * sr)
            i1 = int(s1 * sr)
            seg = y[i0:i1]
            tempo_s, beats_idx = librosa.beat.beat_track(y=seg, sr=sr)
            beats_times = (librosa.frames_to_time(beats_idx, sr=sr) + s0).tolist()
            tempo_events.append((s0, bpm_to_tempo_us_per_beat(float(tempo_s))))
            # Crash at section start if enabled
            if use_crash:
                crash_events.append((s0, ('on', 110))); crash_events.append((s0 + 0.3, ('off', 0)))
            # Estimate 4/4 downbeat index for bar calculation
            downbeat_idx0 = 0
            if len(beats_times) >= 4:
                best_off, best_err = 0, 1e9
                for off in range(4):
                    idxs = list(range(off, len(beats_times), 4))
                    if not idxs:
                        continue
                    dists = [abs(beats_times[i] - s0) for i in idxs]
                    err = min(dists) if dists else 1e9
                    if err < best_err:
                        best_err, best_off = err, off
                downbeat_idx0 = best_off
            bar_starts = [beats_times[i] for i in range(downbeat_idx0, len(beats_times), 4)]
            for i, bt in enumerate(beats_times):
                # Quarter-note hats on the beat
                hv = 80
                if vel_hh == 'accent24' or velocity_profile == 'accent24':
                    hv = 90 if (i % 4 in (1,3)) else 75
                hihat_events.append((bt, ('on', hv)))
                hihat_events.append((bt + 0.08, ('off', 0)))
                if use_ride:
                    rv = 88 if vel_ride == 'flat' else 92
                    ride_events.append((bt, ('on', rv)))
                    ride_events.append((bt + 0.1, ('off', 0)))
                # 8th-note offbeat hats with swing (placement at bt + swingPos*interval)
                if i + 1 < len(beats_times):
                    interval = beats_times[i+1] - bt
                    off_pos = swing if swing > 0 else 0.5
                    off_t = bt + off_pos * interval
                    hv2 = 70
                    if vel_hh == 'accent24' or velocity_profile == 'accent24':
                        hv2 = 80 if (i % 4 in (1,3)) else 65
                    hihat_events.append((off_t, ('on', hv2)))
                    hihat_events.append((off_t + 0.06, ('off', 0)))
                # Snare on 2 and 4: beats 1 and 3 (0-indexed)
                if i % 4 in (1, 3):
                    if vel_snare == 'ghost':
                        sv = 88 if (i % 4 in (1,3)) else 60
                    else:
                        sv = 105 if (vel_snare == 'accent24' or velocity_profile == 'accent24') else 95
                    snare_events.append((bt, ('on', sv)))
                    snare_events.append((bt + 0.1, ('off', 0)))
                # Kick on downbeats (i % 4 == 0)
                if i % 4 == 0:
                    kv = 100
                    if vel_kick == 'punchy' or velocity_profile == 'accent24':
                        kv = 108
                    kick_events.append((bt, ('on', kv)))
                    kick_events.append((bt + 0.12, ('off', 0)))

            # Bar-aware fills near section end based on fill_type and fill_bars
            if fill_type != 'none' and len(bar_starts) >= 1:
                # choose last N bars within this section
                bars_to_fill = bar_starts[-fill_bars:]
                if not bars_to_fill:
                    bars_to_fill = [bar_starts[-1]]
                start_t = max(bars_to_fill[0], s0)
                end_t = beats_times[-1] if beats_times else (s1 - 0.001)
                interval = max(0.05, (end_t - start_t) / max(1, 4*fill_bars))
                def add_tomrun(start_t: float):
                    # 4 hits across last beat with ascending toms (45,47,50,48)
                    toms = [45, 47, 50, 48]
                    steps = len(toms) * fill_bars
                    for k in range(steps):
                        note = toms[k % len(toms)]
                        t = start_t + (k / steps) * (end_t - start_t)
                        sn = 96
                        crash_events.append((t, ('on_note', note, sn)))
                        crash_events.append((t + 0.09, ('off_note', note, 0)))
                def add_snarebuzz(start_t: float):
                    # buzz across the fill window
                    strokes = 8 * fill_bars
                    for k in range(strokes):
                        t = start_t + (k / strokes) * (end_t - start_t)
                        snare_events.append((t, ('on', 100)))
                        snare_events.append((t + 0.07, ('off', 0)))
                def add_edmriser(start_t: float):
                    # dense hats crescendo across the fill window
                    steps = 16 * fill_bars
                    for k in range(steps):
                        t = start_t + (k / steps) * (end_t - start_t)
                        vel = 70 + int(20 * (k / (steps - 1)))
                        hihat_events.append((t, ('on', vel)))
                        hihat_events.append((t + 0.05, ('off', 0)))
                ft = fill_type
                if ft == 'random':
                    ft = np.random.choice(['tomrun','snarebuzz','edmriser']) if np is not None else 'tomrun'
                if ft == 'tomrun':
                    add_tomrun(start_t)
                elif ft == 'snarebuzz':
                    add_snarebuzz(start_t)
                elif ft == 'edmriser':
                    add_edmriser(start_t)

        # Sort all events
        tempo_events.sort(key=lambda x: x[0])
        kick_events.sort(key=lambda x: x[0])
        snare_events.sort(key=lambda x: x[0])
        hihat_events.sort(key=lambda x: x[0])
        ride_events.sort(key=lambda x: x[0])
        crash_events.sort(key=lambda x: x[0])

        # Render tempo track (delta times based on last event time and current tempo context)
        last_t = 0.0
        last_tempo = 500000  # default 120 BPM
        for t_sec, tempo_val in tempo_events:
            dt_sec = max(0.0, t_sec - last_t)
            ticks = sec_to_ticks(dt_sec, last_tempo, mid.ticks_per_beat)
            tempo_track.append(mido.MetaMessage('set_tempo', tempo=tempo_val, time=ticks))
            last_t = t_sec
            last_tempo = tempo_val
        tempo_track.append(mido.MetaMessage('end_of_track', time=0))

        # Helper to render a note event list to a track with a fixed channel and note number
        def render_notes(track: mido.MidiTrack, events: list, note: int, channel: int = 9):
            last_time = 0.0
            # Use a simplistic constant tempo for delta conversion; DAWs will follow tempo track anyway.
            tempo_us = 500000
            for ev in events:
                t_sec, action = ev[0], ev[1]
                dt_sec = max(0.0, t_sec - last_time)
                ticks = sec_to_ticks(dt_sec, tempo_us, mid.ticks_per_beat)
                if isinstance(action, tuple):
                    if len(action) == 2:
                        kind, vel = action
                        if kind == 'on':
                            track.append(mido.Message('note_on', channel=channel, note=note, velocity=int(vel), time=ticks))
                        else:
                            track.append(mido.Message('note_off', channel=channel, note=note, velocity=0, time=ticks))
                    elif len(action) == 3:
                        # custom note events ('on_note'/'off_note', note, vel)
                        kind, n, vel = action
                        if kind == 'on_note':
                            track.append(mido.Message('note_on', channel=channel, note=int(n), velocity=int(vel), time=ticks))
                        else:
                            track.append(mido.Message('note_off', channel=channel, note=int(n), velocity=0, time=ticks))
                else:
                    # Back-compat boolean form
                    if action:
                        track.append(mido.Message('note_on', channel=channel, note=note, velocity=100, time=ticks))
                    else:
                        track.append(mido.Message('note_off', channel=channel, note=note, velocity=0, time=ticks))
                last_time = t_sec
            track.append(mido.MetaMessage('end_of_track', time=0))

        render_notes(kick_track, kick_events, 36)
        render_notes(snare_track, snare_events, 38)
        render_notes(hihat_track, hihat_events, 42)
        render_notes(ride_track, ride_events, 51)
        render_notes(crash_track, crash_events, 49)

        import io
        buf = io.BytesIO()
        mid.save(file=buf)
        b64 = base64.b64encode(buf.getvalue()).decode('ascii')
        filename = f"drumtrack_{path.stem}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mid"
        return web.json_response({"filename": filename, "base64": b64})
    except Exception as e:
        LOG.error(f"midi sections failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/healthz", healthz),
        # keep both paths for compatibility with your frontend(s)
        web.post("/api/upload", upload),
        web.post("/files/upload", upload),
        web.get("/files/waveform", waveform),
        web.get("/files/audio", audio_file),
        web.get("/api/status", api_status),
        # New analysis endpoints
        web.get("/analyze/onsets", analyze_onsets),
        web.get("/analyze/tempo", analyze_tempo),
        web.post("/analyze/tempo_sections", analyze_tempo_sections),
        web.post("/align/sections", align_sections),
        web.post("/generate/midi_sections", generate_midi_sections),
        # Session endpoints
        web.post("/session/{sid}", save_session),
        web.get("/session/{sid}", load_session),
        # Benchmark endpoints
        web.get("/bench/peaks", bench_peaks),
        web.get("/bench/analysis", bench_analysis),
        web.get("/bench/generate", bench_generate),
        # DCSM endpoints
        web.get("/dcsm/sectionize", dcsm_sectionize),
        web.post("/dcsm/generate", dcsm_generate),
        web.post("/dcsm/export_midi", dcsm_export_midi),

        # Sample DB endpoints
        web.get("/api/sample-collections", list_sample_collections),
        web.get("/api/drum-samples", list_drum_samples),
        web.get("/api/drum-samples/{sample_id}/audio", stream_drum_sample_audio),
    ])

    # CORS for dev
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_headers="*",
            allow_methods="*",
            expose_headers="*",
            allow_credentials=False,  # keep False for wildcard origins
        )
    })
    for route in list(app.router.routes()):
        try:
            cors.add(route)
        except Exception:
            pass

    async def on_startup(_):
        LOG.info("DrumTracKAI aiohttp API running on http://%s:%d", HOST, PORT)
    app.on_startup.append(on_startup)
    return app

async def _amain():
    app = make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()
    # keep process alive
    LOG.info("Serving forever on %s:%d", HOST, PORT)
    while True:
        await asyncio.sleep(3600)

# ---------- New Analysis & Session Endpoints ----------
class SectionIn(BaseModel):
    start: float
    end: float


def _db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SAMPLE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _get_allowed_sample_roots(conn: sqlite3.Connection) -> list[Path]:
    try:
        cur = conn.cursor()
        cur.execute("SELECT folder_path FROM sample_collections WHERE folder_path IS NOT NULL")
        roots: list[Path] = []
        for r in cur.fetchall():
            fp = r[0]
            if not fp:
                continue
            try:
                roots.append(Path(fp).resolve())
            except Exception:
                continue
        return roots
    except Exception:
        return []


def _is_under_any_root(path: Path, roots: list[Path]) -> bool:
    try:
        rp = path.resolve()
    except Exception:
        return False
    for root in roots:
        try:
            rr = root.resolve()
        except Exception:
            continue
        try:
            if rp == rr or rr in rp.parents:
                return True
        except Exception:
            continue
    return False


async def list_sample_collections(request: web.Request) -> web.Response:
    if not SAMPLE_DB_PATH.exists():
        return web.json_response({"error": "sample db not found", "db": str(SAMPLE_DB_PATH)}, status=404)
    try:
        conn = _db_connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, collection_name, description, manufacturer, category, folder_path, sample_count, created_at "
                "FROM sample_collections ORDER BY id"
            )
            rows = [dict(r) for r in cur.fetchall()]
            return web.json_response({"db": str(SAMPLE_DB_PATH), "collections": rows})
        finally:
            conn.close()
    except Exception as e:
        LOG.error(f"list_sample_collections failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def list_drum_samples(request: web.Request) -> web.Response:
    if not SAMPLE_DB_PATH.exists():
        return web.json_response({"error": "sample db not found", "db": str(SAMPLE_DB_PATH)}, status=404)

    collection_id = request.query.get("collection_id")
    drum_type = request.query.get("drum_type")
    limit = request.query.get("limit")
    offset = request.query.get("offset")

    try:
        limit_n = int(limit) if limit is not None else 200
    except Exception:
        limit_n = 200
    try:
        offset_n = int(offset) if offset is not None else 0
    except Exception:
        offset_n = 0

    try:
        conn = _db_connect()
        try:
            cur = conn.cursor()
            where = []
            params: list[object] = []

            join = ""
            if collection_id:
                join = " JOIN collection_samples cs ON cs.sample_id = ds.id "
                where.append("cs.collection_id = ?")
                params.append(collection_id)
            if drum_type:
                where.append("ds.drum_type = ?")
                params.append(drum_type)

            where_sql = (" WHERE " + " AND ".join(where)) if where else ""
            sql = (
                "SELECT ds.id, ds.file_path, ds.file_name, ds.file_size, ds.drum_type, ds.variation, ds.format, ds.kit_name "
                "FROM drum_samples ds" + join + where_sql + " ORDER BY ds.id LIMIT ? OFFSET ?"
            )
            params.extend([limit_n, offset_n])
            cur.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            return web.json_response({"db": str(SAMPLE_DB_PATH), "samples": rows, "limit": limit_n, "offset": offset_n})
        finally:
            conn.close()
    except Exception as e:
        LOG.error(f"list_drum_samples failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def stream_drum_sample_audio(request: web.Request) -> web.StreamResponse:
    if not SAMPLE_DB_PATH.exists():
        return web.json_response({"error": "sample db not found", "db": str(SAMPLE_DB_PATH)}, status=404)

    sample_id = request.match_info.get("sample_id")
    if not sample_id:
        return web.json_response({"error": "sample_id required"}, status=400)

    try:
        conn = _db_connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT file_path FROM drum_samples WHERE id = ?", (sample_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                return web.json_response({"error": "sample not found"}, status=404)

            file_path = Path(row[0])
            if not file_path.exists() or not file_path.is_file():
                return web.json_response({"error": "file not found", "file_path": str(file_path)}, status=404)

            roots = _get_allowed_sample_roots(conn)
            if roots and not _is_under_any_root(file_path, roots):
                return web.json_response({"error": "file path not allowed"}, status=403)

            ctype, _ = mimetypes.guess_type(str(file_path))
            if not ctype:
                ctype = "application/octet-stream"
            return web.FileResponse(path=str(file_path), headers={"Content-Type": ctype})
        finally:
            conn.close()
    except Exception as e:
        LOG.error(f"stream_drum_sample_audio failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def analyze_onsets(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    if not sf or not librosa:
        return web.json_response({"error": "librosa/soundfile not available"}, status=500)
    
    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
        return web.json_response({"sr": sr, "onsets": [float(t) for t in onsets]})
    except Exception as e:
        LOG.error(f"Onset analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

def _tempo_candidates_and_confidence(y: np.ndarray, sr: int, bpm_min: float = 60.0, bpm_max: float = 200.0):
    """Compute candidate BPMs and a simple confidence measure using a tempogram.
    Confidence is defined as the ratio of the top peak over the second peak (>=1.0).
    """
    try:
        # Compute onset strength envelope
        oenv = None
        try:
            import librosa
            oenv = librosa.onset.onset_strength(y=y, sr=sr)
            # Tempogram
            tg = librosa.feature.tempogram(onset_envelope=oenv, sr=sr)
            ac = tg.mean(axis=1)
            # Map auto-correlation lags to BPM
            # Avoid zero-lag; convert lag indices to BPM: bpm = 60 * sr / lag_samples
            lags = np.arange(1, len(ac))
            bpms = 60.0 * sr / (lags * 512) if False else None  # placeholder if hop mismatched
            # Better: use librosa.beat.tempo over a range and get aggregate
            tempo_candidates = librosa.beat.tempo(onset_envelope=oenv, sr=sr, aggregate=None)
            # Filter to requested range
            cand = [float(b) for b in tempo_candidates if bpm_min <= float(b) <= bpm_max]
            # Confidence via histogram peak ratio
            if len(cand) == 0:
                return [], 0.0
            hist, edges = np.histogram(cand, bins=20, range=(bpm_min, bpm_max))
            order = np.argsort(hist)[::-1]
            top = hist[order[0]] if len(order) > 0 else 1
            second = hist[order[1]] if len(order) > 1 else max(1, top)
            confidence = float(top) / float(max(1, second)) if top >= second else 1.0
            # Unique sorted
            uniq = sorted({round(c, 2) for c in cand})
            return uniq[:5], confidence
        except Exception:
            return [], 0.0
    except Exception:
        return [], 0.0

async def analyze_tempo(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    # Try Rust implementation first if enabled
    if USE_RUST:
        try:
            result = run_audio_core(["analyze", str(path)])
            return web.json_response({
                "tempo": float(result["tempo"]), 
                "beats": result["beats"],
                "onsets": result.get("onsets", [])
            })
        except Exception as e:
            LOG.warning(f"Rust tempo analysis failed, falling back to Python: {e}")
    
    # Python fallback implementation
    if not sf or not librosa:
        return web.json_response({"error": "librosa/soundfile not available"}, status=500)
    
    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        times = librosa.frames_to_time(beats, sr=sr)
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
        return web.json_response({
            "tempo": float(tempo), 
            "beats": [float(t) for t in times],
            "onsets": [float(t) for t in onsets]
        })
    except Exception as e:
        LOG.error(f"Tempo analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def align_sections(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)

    try:
        data = await request.json()
        sections = data if isinstance(data, list) else []
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)

    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)

    if not sf or not librosa:
        return web.json_response({"error": "audio analysis libraries not available"}, status=500)

    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if hasattr(y, 'ndim') and y.ndim == 2:
            y = y.mean(axis=1)
        n = len(y)
        dur = float(n) / float(sr) if sr else 0.0

        aligned = []
        tempos = []
        details = []
        global_phase = None  # 0..3 downbeat modulo for 4/4
        for s in sections:
            s0 = float(max(0.0, s.get("start", 0.0)))
            s1 = float(min(dur, s.get("end", s0 + 1.0)))
            if s1 <= s0:
                aligned.append({"start": s0, "end": s1})
                tempos.append(None)
                continue
            i0 = int(s0 * sr)
            i1 = int(s1 * sr)
            seg = y[i0:i1]
            # Per-section tempo and beat grid
            tempo_s, beats_s = librosa.beat.beat_track(y=seg, sr=sr)
            tempo_s_val = float(tempo_s) if isinstance(tempo_s, (int, float, np.floating)) else None
            tempos.append(tempo_s_val)
            times_s = librosa.frames_to_time(beats_s, sr=sr) + s0
            cands_s, conf_s = _tempo_candidates_and_confidence(y=seg, sr=sr)
            if len(times_s) == 0:
                # Fallback: no beats detected, keep original
                aligned.append({"start": s0, "end": s1})
                continue
            def snap_to_times(v: float):
                idx = int(np.argmin(np.abs(times_s - v)))
                return float(times_s[idx])
            start_a = snap_to_times(s0)
            end_a = snap_to_times(s1)
            if end_a <= start_a:
                # ensure minimum length
                end_a = max(start_a + 0.25, s1)
            # Estimate downbeat offset under 4/4 by choosing offset that best matches section start as downbeat
            downbeat_idx0 = 0
            if len(times_s) >= 4:
                best_off = 0
                best_err = 1e9
                for off in range(4):
                    # distance of section start to nearest beat congruent to off mod 4
                    idxs = np.arange(off, len(times_s), 4)
                    if len(idxs) == 0:
                        continue
                    dists = np.abs(times_s[idxs] - s0)
                    err = float(np.min(dists)) if len(dists) else 1e9
                    if err < best_err:
                        best_err = err
                        best_off = off
                downbeat_idx0 = int(best_off)
            # Establish a global phase based on first section's detected downbeat index
            if global_phase is None:
                global_phase = int(downbeat_idx0)
            # Snap start to nearest beat that matches global phase, if available
            phase_idxs = np.arange(global_phase, len(times_s), 4)
            if len(phase_idxs) > 0:
                idx = int(np.argmin(np.abs(times_s[phase_idxs] - s0)))
                start_a = float(times_s[phase_idxs[idx]])
            # Bars are every 4 beats starting at global phase
            bar_idxs = np.arange(global_phase if global_phase is not None else downbeat_idx0, len(times_s), 4)
            bars = [float(times_s[i]) for i in bar_idxs]
            aligned.append({"start": start_a, "end": end_a})
            details.append({
                "start": s0, "end": s1,
                "tempo": tempo_s_val,
                "candidates": cands_s,
                "confidence": conf_s,
                "beats": [float(t) for t in times_s.tolist()] if hasattr(times_s, 'tolist') else [float(t) for t in times_s],
                "downbeatIndex0": int(global_phase if global_phase is not None else downbeat_idx0),
                "bars": bars
            })

        # Average tempo ignoring None
        tempos_valid = [t for t in tempos if isinstance(t, (int, float))]
        avg_tempo = float(np.mean(tempos_valid)) if tempos_valid else None

        return web.json_response({"tempo": avg_tempo, "tempos": tempos, "sections": aligned, "details": details})
    except Exception as e:
        LOG.error(f"Section alignment failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

# --- Session Save/Load ---
class SessionModel(BaseModel):
    bpm: float
    loop: dict
    tracks: list
    sections: list
    notes: list

async def save_session(request):
    sid = request.match_info.get("sid")
    if not sid:
        return web.json_response({"error": "session ID required"}, status=400)
    
    try:
        payload = await request.json()
        p = (SESSIONS_DIR / f"{sid}.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        return web.json_response({"ok": True})
    except Exception as e:
        LOG.error(f"Session save failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def load_session(request):
    sid = request.match_info.get("sid")
    if not sid:
        return web.json_response({"error": "session ID required"}, status=400)
    
    p = (SESSIONS_DIR / f"{sid}.json")
    if not p.exists():
        return web.json_response({"error": "session not found"}, status=404)
    
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return web.json_response(data)
    except Exception as e:
        LOG.error(f"Session load failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

# DCSM Enhanced Analysis Endpoints
async def analyze_onsets(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    if not sf or not librosa:
        return web.json_response({"error": "audio analysis libraries not available"}, status=500)
    
    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
        return web.json_response({"sr": sr, "onsets": [float(t) for t in onsets]})
    except Exception as e:
        LOG.error(f"Onset analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def analyze_tempo(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    # Optional section slicing
    start_q = request.query.get("start")
    end_q = request.query.get("end")
    start_t = None
    end_t = None
    try:
        if start_q is not None:
            start_t = float(start_q)
        if end_q is not None:
            end_t = float(end_q)
    except Exception:
        start_t, end_t = None, None

    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)

    if not sf or not librosa:
        return web.json_response({"error": "audio analysis libraries not available"}, status=500)

    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if hasattr(y, 'ndim') and y.ndim == 2:
            y = y.mean(axis=1)
        # Apply section slicing if requested
        if start_t is not None or end_t is not None:
            n = len(y)
            dur = float(n) / float(sr) if sr else 0.0
            s = max(0.0, start_t or 0.0)
            e = min(dur, end_t if end_t is not None else dur)
            if e > s and sr:
                i0 = int(s * sr)
                i1 = int(e * sr)
                y = y[i0:i1]
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                times = librosa.frames_to_time(beats, sr=sr) + s
            else:
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
                times = librosa.frames_to_time(beats, sr=sr)
        else:
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            times = librosa.frames_to_time(beats, sr=sr)
        # Add candidates and confidence
        cands, conf = _tempo_candidates_and_confidence(y=y, sr=sr)
        return web.json_response({"tempo": float(tempo), "beats": [float(t) for t in times], "candidates": cands, "confidence": conf})
    except Exception as e:
        LOG.error(f"Tempo analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def analyze_tempo_sections(request):
    """Batch per-section tempo analysis.
    Request JSON: { key: str, sections: [{start: number, end: number}, ...] }
    Response: { results: [{ start, end, tempo, candidates, confidence }...] }
    """
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)
    key = data.get("key")
    sections = data.get("sections", [])
    if not key or not isinstance(sections, list):
        return web.json_response({"error": "key and sections required"}, status=400)

    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    if not sf or not librosa:
        return web.json_response({"error": "audio analysis libraries not available"}, status=500)

    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if hasattr(y, 'ndim') and y.ndim == 2:
            y = y.mean(axis=1)
        n = len(y)
        dur = float(n) / float(sr) if sr else 0.0

        results = []
        for s in sections:
            s0 = float(max(0.0, s.get('start', 0.0)))
            s1 = float(min(dur, s.get('end', dur)))
            if s1 <= s0:
                results.append({"start": s0, "end": s1, "tempo": None, "candidates": [], "confidence": 0.0})
                continue
            i0 = int(s0 * sr)
            i1 = int(s1 * sr)
            y_seg = y[i0:i1]
            tempo, beats = librosa.beat.beat_track(y=y_seg, sr=sr)
            cands, conf = _tempo_candidates_and_confidence(y=y_seg, sr=sr)
            results.append({"start": s0, "end": s1, "tempo": float(tempo), "candidates": cands, "confidence": conf})

        return web.json_response({"results": results})
    except Exception as e:
        LOG.error(f"tempo sections failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def align_sections(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    try:
        data = await request.json()
        sections = data if isinstance(data, list) else []
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    if not sf or not librosa:
        return web.json_response({"error": "audio analysis libraries not available"}, status=500)
    
    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        times = librosa.frames_to_time(beats, sr=sr)
        
        def snap(v: float):
            if len(times) == 0:
                return v
            idx = int(np.argmin(np.abs(times - v)))
            return float(times[idx])
        
        aligned = []
        for s in sections:
            start = snap(s.get("start", 0))
            end = max(snap(s.get("end", start + 1)), start + 0.25)
            aligned.append({"start": start, "end": end})
        
        return web.json_response({"tempo": float(tempo), "sections": aligned})
    except Exception as e:
        LOG.error(f"Section alignment failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

def main():
    # Windows: use Selector policy to avoid Proactor/signal quirks with aiohttp
    if os.name == "nt":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        LOG.info("Shutting down")

# Optional benchmark endpoint for A/B testing Python vs Rust
async def bench_analysis(request):
    key = request.query.get("key")
    impl = request.query.get("impl", "auto")
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    import time
    t0 = time.perf_counter()
    
    if impl == "rust" or (impl == "auto" and USE_RUST):
        try:
            result = run_audio_core(["analyze", str(path)])
            dur = time.perf_counter() - t0
            return web.json_response({
                "impl": "rust", 
                "ms": int(dur * 1000), 
                "tempo": result["tempo"],
                "beats": result["beats"],
                "onsets": result["onsets"]
            })
        except Exception as e:
            dur = time.perf_counter() - t0
            return web.json_response({
                "impl": "rust_failed", 
                "ms": int(dur * 1000), 
                "error": str(e)
            }, status=500)
    else:
        # Python implementation timing
        if not sf or not librosa:
            return web.json_response({"error": "librosa/soundfile not available"}, status=500)
        
        try:
            y, sr = sf.read(str(path), dtype="float32", always_2d=False)
            if y.ndim == 2:
                y = y.mean(axis=1)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            times = librosa.frames_to_time(beats, sr=sr)
            onsets = librosa.onset.onset_detect(y=y, sr=sr, units="time")
            dur = time.perf_counter() - t0
            
            return web.json_response({
                "impl": "python",
                "ms": int(dur * 1000),
                "tempo": float(tempo),
                "beats": [float(t) for t in times],
                "onsets": [float(t) for t in onsets]
            })
        except Exception as e:
            dur = time.perf_counter() - t0
            return web.json_response({
                "impl": "python_failed",
                "ms": int(dur * 1000),
                "error": str(e)
            }, status=500)

# DCSM endpoints for Rust integration
async def dcsm_sectionize(request):
    key = request.query.get("key")
    bpm = float(request.query.get("bpm", "120.0"))
    bars = int(request.query.get("bars", "8"))
    mode = request.query.get("mode", "bars")
    min_bars = int(request.query.get("min_bars", "4"))
    max_bars = int(request.query.get("max_bars", "16"))
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    if not USE_RUST or mode == "bars":
        # Simple fallback: fixed bars
        try:
            if sf:
                info = sf.info(str(path))
                duration = float(info.frames) / float(info.samplerate) if info.samplerate and info.frames else 0.0
            else:
                duration = 60.0  # fallback
            
            sec_per_bar = 60.0/bpm*4.0
            spans = []
            t = 0.0
            while t < duration: 
                spans.append([t, min(t+sec_per_bar*bars, duration)])
                t += sec_per_bar*bars
            return web.json_response({"sections": [{"start":s, "end":e, "label":"section"} for (s,e) in spans]})
        except Exception as e:
            LOG.error(f"Simple sectionize failed: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    # Smart mode via Rust
    try:
        result = run_audio_core(["sectionize-smart", str(path), "--bpm", str(bpm), "--min-bars", str(min_bars), "--max-bars", str(max_bars)])
        return web.json_response(result)
    except Exception as e:
        LOG.warning(f"Rust smart sectionize failed, falling back to simple: {e}")
        # Fallback to simple mode
        try:
            if sf:
                info = sf.info(str(path))
                duration = float(info.frames) / float(info.samplerate) if info.samplerate and info.frames else 0.0
            else:
                duration = 60.0
            sec_per_bar = 60.0/bpm*4.0
            spans = []
            t = 0.0
            while t < duration: 
                spans.append([t, min(t+sec_per_bar*bars, duration)])
                t += sec_per_bar*bars
            return web.json_response({"sections": [{"start":s, "end":e, "label":"section"} for (s,e) in spans]})
        except Exception as e2:
            LOG.error(f"Fallback sectionize failed: {e2}")
            return web.json_response({"error": str(e2)}, status=500)

async def dcsm_generate(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)
    
    bpm = data.get("bpm", 120.0)
    section = data.get("section", {})
    start = section.get("start", 0.0)
    end = section.get("end", 4.0)
    density = section.get("density", 0.6)
    swing = section.get("swing", 0.1)
    humanize = section.get("humanize", 0.15)
    style = section.get("style", "rock")
    performance_spec = data.get("performance_spec") or {}
    section_label = section.get("label", "section")
    
    if not USE_RUST:
        return web.json_response({"error": "rust generator disabled; set USE_RUST=1"}, status=503)
    
    try:
        args = [
            "generate", "--bpm", str(bpm),
            "--start", str(start), "--end", str(end),
            "--density", str(density), "--swing", str(swing), "--humanize", str(humanize),
            "--seed", "42", "--style", style
        ]
        result = run_audio_core(args)

        notes = result.get("notes")
        if isinstance(notes, list) and performance_spec:
            for n in notes:
                lane = str(n.get("lane", ""))
                vel = int(n.get("vel", 100))
                logical_note = {
                    "instrumentId": lane,
                    "velocity": vel,
                    "isGhost": False,
                    "isAccent": vel >= 110,
                }
                try:
                    n["articulationId"] = select_articulation_for_note(
                        logical_note,
                        performance_spec,
                        section_label,
                    )
                except Exception as e:
                    LOG.warning(f"articulation selection failed for note {n}: {e}")
        return web.json_response(result)
    except Exception as e:
        LOG.error(f"Rust generate failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

if __name__ == "__main__":
    main()
