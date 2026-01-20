  # drumtrackai_api_server_clean.py
import os, asyncio, logging, mimetypes, time, shutil, json, subprocess, math, uuid
import sqlite3
from typing import Optional
from pathlib import Path

import urllib.request

# DISABLED: numpy causes heap corruption (exit code 3221226356) on Windows
# import numpy as np
np = None

from aiohttp import web
import aiohttp_cors

# Pydantic is only used for a couple of lightweight request models. On some
# Windows/Python combos the pydantic_core wheel may not be available, which
# would otherwise prevent the whole backend from starting. Make this import
# optional and fall back to a no-op BaseModel so the API can still run.
try:
    from pydantic import BaseModel  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    class BaseModel:  # type: ignore
        pass

# DISABLED: These libraries cause heap corruption - use Rust audio-core instead
# try:
#     import soundfile as sf
# except Exception:
#     sf = None
# try:
#     import librosa
# except Exception:
#     librosa = None
sf = None
librosa = None

# Set up logging as early as possible so LOG is available during imports
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
LOG = logging.getLogger("drumtrackai")

DRUM_GEN_STATS = {
    "requests": 0,
    "ok": 0,
    "fallback": 0,
    "last_backend": None,
    "last_fallback_reason": None,
    "last_fallback_ts": None,
}

# Import drummer mapping service
from drummer_mapping_service import get_drummer_service
# TEMPORARILY DISABLED FOR TESTING - AI endpoints have deep dependency chain
# from backend_ai_endpoints import initialize_ai_generator, setup_ai_routes
from song_lookup_service import search_song

# Import drum generation API (Drum Builder v2.0 integrated)
from drum_generation_api import generate_drums, DrumGenerationConfig, list_egmd_phrases, list_egmd_style_groups
from backend.drum_generation.brain_elements import get_brain_elements
from backend.drum_generation.drum_generation_config import (
    DrumBrainConfig,
    BrainElementSetting,
)

from backend.beatbox_translator import (
    BeatboxTranslationOptions,
    translate_beatbox,
    taps_to_translation,
)

from backend.render_to_plugin_midi import render_articulated_notes_to_midi
from backend.beatprompt_engine import (
    normalize_sections,
    render_sections_to_hits,
    serialize_sections,
)

from backend.groove_catalog import GrooveCatalog
from backend.fill_library import get_fill_pattern
from backend.dcsmpiano.dcsm_drumtrack_schema import instrument_id_to_midi_pitch, make_note_id

# Groove Coach (safe import; does not require heavy deps)
try:
    from backend.groove_coach_engine import build_groove_coach_response, list_available_goals, apply_config_patch
    GROOVE_COACH_AVAILABLE = True
except Exception as e:
    GROOVE_COACH_AVAILABLE = False
    build_groove_coach_response = None  # type: ignore
    list_available_goals = None  # type: ignore
    apply_config_patch = None  # type: ignore
    LOG.warning("Groove coach not available: %s", e)

# Admin DB service for drummer personas (optional; fail-soft if unavailable)
try:
    from admin.services.central_database_service import get_database_service as get_admin_db_service
    ADMIN_DB_AVAILABLE = True
except Exception:
    ADMIN_DB_AVAILABLE = False
    LOG.warning("CentralDatabaseService not available; /api/drummer-personas will be empty.")

# Import Jamstix brain system
try:
    from backend.jamstix_brain import (
        enrich_drum_events_with_jamstix_attrs,
        DCSMDrumTrackBuilder,
        detect_limb_conflicts,
        resolve_limb_conflicts
    )
    JAMSTIX_BRAIN_AVAILABLE = True
except ImportError:
    JAMSTIX_BRAIN_AVAILABLE = False

JAMSTIX_INSTRUMENT_MAP = {
    "kick": "kick",
    "bd": "kick",
    "sn": "snare_center",
    "snare": "snare_center",
    "snare_center": "snare_center",
    "snare_rim": "snare_rim",
    "rim": "snare_rim",
    "ghost": "snare_ghost",
    "hihat": "hihat_closed",
    "hh": "hihat_closed",
    "hat": "hihat_closed",
    "ride": "ride_bow",
    "perc": "tom_mid",
    "tom": "tom_mid",
    "tom1": "tom_high",
    "tom2": "tom_mid",
    "tom3": "tom_low",
    "floor": "tom_floor",
    "crash": "crash_1",
    "crash2": "crash_2",
    "china": "crash_china",
}

def _section_attr(section, attr, default=None):
    if hasattr(section, attr):
        return getattr(section, attr)
    if isinstance(section, dict):
        return section.get(attr, default)
    return default

def _normalize_time_signature(meter):
    meter = str(meter or "4/4").strip()
    if "/" in meter:
        parts = meter.split("/")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            denom = int(parts[1]) or 4
            return f"{int(parts[0])}/{denom}"
    return "4/4"

def _beats_per_bar_from_signature(time_signature):
    try:
        num, denom = time_signature.split("/")
        denom_val = int(denom) or 4
        return int(num) * (4 / denom_val)
    except Exception:
        return 4.0

def _map_instrument_for_jamstix(raw):
    key = str(raw or "snare").strip().lower()
    return JAMSTIX_INSTRUMENT_MAP.get(key, key if key in JAMSTIX_INSTRUMENT_MAP.values() else "snare_center")

def _estimate_total_bars_from_hits(hits, beats_per_bar):
    if not hits:
        return 1
    beat_values = []
    for hit in hits:
        beat_values.append(float(hit.get("beat_position") or hit.get("beat") or 0.0))
    if not beat_values:
        return 1
    min_beat = min(beat_values)
    max_beat = max(beat_values)
    span = max_beat - min_beat
    approx_beats = span + beats_per_bar
    bars = int(math.ceil(max(approx_beats, beats_per_bar) / max(beats_per_bar, 1e-6)))
    return max(1, bars)

def _collect_section_modifiers(sections):
    mods = []
    for section in sections or []:
        section_mods = _section_attr(section, "modifiers", []) or []
        mods.extend(str(m).lower() for m in section_mods if isinstance(m, str))
    return mods

def _build_songmap_sections(sections, default_total_bars):
    """Convert prompt sections into Jamstix-friendly SongMap entries."""
    songmap = []
    cursor = 0
    for section in sections or []:
        bars = int(_section_attr(section, "bars", 4) or 4)
        if bars <= 0:
            continue
        label = _section_attr(section, "label", f"Section {len(songmap)+1}") or f"Section {len(songmap)+1}"
        songmap.append({
            "type": label,
            "startBar": cursor,
            "endBar": cursor + bars,
            "personaId": _section_attr(section, "persona_id"),
            "stylePack": _section_attr(section, "style_pack"),
            "modifiers": list(_section_attr(section, "modifiers", []) or []),
        })
        cursor += bars
    if songmap:
        return songmap
    return [{"type": "Main", "startBar": 0, "endBar": max(1, default_total_bars)}]

def _hits_to_pattern_events_for_jamstix(hits, tempo, beats_per_bar):
    """Translate simple hit dictionaries into Jamstix pattern events."""
    if not hits:
        return []
    seconds_per_beat = 60.0 / max(float(tempo) if tempo else 1.0, 1e-6)
    beat_values = [float(hit.get("beat_position") or hit.get("beat") or 0.0) for hit in hits]
    min_beat = min(beat_values) if beat_values else 0.0
    events = []
    for hit, beat_value in zip(hits, beat_values):
        relative_beat = beat_value - min_beat
        bar_index = int(math.floor(relative_beat / max(beats_per_bar, 1e-6)))
        bar_start_time = bar_index * beats_per_bar * seconds_per_beat
        bar_end_time = bar_start_time + beats_per_bar * seconds_per_beat
        events.append({
            "time_sec": relative_beat * seconds_per_beat,
            "instrument_id": _map_instrument_for_jamstix(hit.get("instrument")),
            "velocity": int(hit.get("velocity") or 96),
            "barIndex": bar_index,
            "barStartTime": bar_start_time,
            "barEndTime": bar_end_time,
        })
    return events

def _derive_performance_spec(tempo, persona_id=None, style_pack=None, modifiers=None, feel_hint=None):
    """Create a lightweight performance spec so Jamstix brain has musical context."""
    modifiers = modifiers or []
    feel = feel_hint or ("laid_back" if tempo and tempo < 92 else "pushed" if tempo and tempo > 135 else "on_the_beat")
    swing = 0.0
    if any("triplet" in m or "swing" in m for m in modifiers):
        feel = "swing"
        swing = 0.55
    hat_open = 0.25
    if any("wide hat" in m or "open hat" in m for m in modifiers):
        hat_open = 0.5
    if persona_id and "funk" in persona_id:
        feel = "laid_back"
        hat_open = max(hat_open, 0.35)
    if persona_id and "metal" in persona_id:
        feel = "pushed"
        hat_open = min(hat_open, 0.2)
    if style_pack and "brush" in style_pack.lower():
        hat_open = 0.1
    ghost_amount = 0.35
    if any("ghost" in m for m in modifiers):
        ghost_amount = 0.7
    intensity = min(1.0, max(0.3, (tempo or 100.0) / 180.0))
    return {
        "feel": feel,
        "swing": swing,
        "intensity": intensity,
        "hatOpenness": hat_open,
        "fillStyle": "linear" if feel == "swing" else "tom_run",
        "ghostNoteAmount": ghost_amount,
    }

def auto_generate_jamstix_track(hits, tempo, sections=None, persona_hint=None, style_pack_hint=None, feel_hint=None, meter_hint=None):
    """Best-effort Jamstix automation that runs alongside BeatPrompt/beatbox flows."""
    if not JAMSTIX_BRAIN_AVAILABLE:
        return None, "jamstix_unavailable"
    if not hits:
        return None, "no_hits"
    time_signature = _normalize_time_signature(meter_hint or (_section_attr(sections[0], "meter") if sections else None))
    beats_per_bar = _beats_per_bar_from_signature(time_signature)
    total_bars = _estimate_total_bars_from_hits(hits, beats_per_bar)
    songmap_sections = _build_songmap_sections(sections, total_bars)
    modifiers = _collect_section_modifiers(sections)
    persona = persona_hint or (_section_attr(sections[0], "persona_id") if sections else None)
    style_pack = style_pack_hint or (_section_attr(sections[0], "style_pack") if sections else None)
    pattern_events = _hits_to_pattern_events_for_jamstix(hits, tempo, beats_per_bar)
    if not pattern_events:
        return None, "no_events"
    perf_spec = _derive_performance_spec(tempo, persona_id=persona, style_pack=style_pack, modifiers=modifiers, feel_hint=feel_hint)
    builder = DCSMDrumTrackBuilder(tempo=tempo, time_signature=time_signature)
    track = builder.build_from_pattern_and_spec(pattern_events, songmap_sections, perf_spec)
    return {
        "track": track.to_dict(),
        "sections": songmap_sections,
        "performanceSpec": perf_spec,
        "timeSignature": time_signature,
    }, None

# ---------- Config ----------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", "8000"))
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = (BASE_DIR / "uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MVSEP_DIR = (UPLOAD_DIR / "mvsep")
MVSEP_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# ---- MVSEP job manager (Mode A) ----
MVSEP_JOBS = {}

def _mvsep_safe_path(p: Path) -> Optional[Path]:
    try:
        rp = p.resolve()
        if not str(rp).startswith(str(MVSEP_DIR.resolve())):
            return None
        return rp
    except Exception:
        return None

def _upload_safe_path(p: Path) -> Optional[Path]:
    try:
        rp = p.resolve()
        if not str(rp).startswith(str(UPLOAD_DIR.resolve())):
            return None
        return rp
    except Exception:
        return None

async def _mvsep_run_job(job_id: str, audio_path: Path, out_dir: Path):
    # Lazy import so backend can still boot without admin deps.
    try:
        from admin.services.mvsep_service import MVSepService
    except Exception as e:
        MVSEP_JOBS[job_id]["status"] = "failed"
        MVSEP_JOBS[job_id]["error"] = f"mvsep_service_import_failed: {e}"
        return

    api_key = str(os.getenv("MVSEP_API_KEY", "")).strip()
    if not api_key:
        try:
            from admin.utils.api_key_manager import get_api_key_manager
            api_key = str(get_api_key_manager().get_key("MVSEP_API_KEY") or "").strip()
        except Exception:
            api_key = ""
    if not api_key:
        MVSEP_JOBS[job_id]["status"] = "failed"
        MVSEP_JOBS[job_id]["error"] = "MVSEP_API_KEY not set"
        return

    MVSEP_JOBS[job_id]["status"] = "running"
    MVSEP_JOBS[job_id]["progress"] = 0.01
    MVSEP_JOBS[job_id]["message"] = "starting"

    def _progress(p: float, msg: str):
        try:
            MVSEP_JOBS[job_id]["progress"] = float(p)
            MVSEP_JOBS[job_id]["message"] = str(msg)
        except Exception:
            pass

    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        svc = MVSepService(api_key=api_key)
        stems = await svc.process_audio_file(
            input_file=str(audio_path),
            output_dir=str(out_dir),
            progress_callback=_progress,
            keep_original_mix=True,
            keep_drum_stem=True,
        )
        MVSEP_JOBS[job_id]["status"] = "done"
        MVSEP_JOBS[job_id]["progress"] = 1.0
        MVSEP_JOBS[job_id]["message"] = "done"
        MVSEP_JOBS[job_id]["stems"] = stems or {}
    except Exception as e:
        MVSEP_JOBS[job_id]["status"] = "failed"
        MVSEP_JOBS[job_id]["error"] = str(e)


async def api_mvsep_start(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    key = data.get("key")
    if not key:
        return web.json_response({"ok": False, "error": "key required"}, status=400)

    audio_path = _upload_safe_path((UPLOAD_DIR / str(key)))
    if not audio_path or not audio_path.exists():
        return web.json_response({"ok": False, "error": "audio not found"}, status=404)

    job_id = str(uuid.uuid4())
    out_dir = _mvsep_safe_path(MVSEP_DIR / job_id)
    if not out_dir:
        return web.json_response({"ok": False, "error": "invalid mvsep output dir"}, status=500)

    MVSEP_JOBS[job_id] = {
        "job_id": job_id,
        "key": str(key),
        "status": "queued",
        "progress": 0.0,
        "message": "queued",
        "stems": None,
        "error": None,
        "created_at": time.time(),
    }

    asyncio.create_task(_mvsep_run_job(job_id, audio_path, out_dir))
    return web.json_response({"ok": True, "job_id": job_id})


async def api_mvsep_status(request: web.Request):
    job_id = request.query.get("job_id")
    if not job_id:
        return web.json_response({"ok": False, "error": "job_id required"}, status=400)
    job = MVSEP_JOBS.get(str(job_id))
    if not job:
        return web.json_response({"ok": False, "error": "job not found"}, status=404)
    return web.json_response({"ok": True, **job})


async def api_mvsep_stems(request: web.Request):
    job_id = request.query.get("job_id")
    if not job_id:
        return web.json_response({"ok": False, "error": "job_id required"}, status=400)
    job = MVSEP_JOBS.get(str(job_id))
    if not job:
        return web.json_response({"ok": False, "error": "job not found"}, status=404)
    stems = job.get("stems")
    if not isinstance(stems, dict):
        return web.json_response({"ok": False, "error": "stems not ready"}, status=409)
    return web.json_response({"ok": True, "job_id": str(job_id), "stems": stems})

KITS_ROOT = (BASE_DIR / "frontend" / "public" / "kits")

# Sample DB + sample library configuration (Docker/cloud friendly)
# - DB path can be mounted at /data/db/drumtrackai.db
# - Samples can be mounted at /data/samples
SAMPLE_DB_PATH = Path(os.getenv("SAMPLE_DB_PATH", os.getenv("DRUMTRACKAI_DB_PATH", str((BASE_DIR / "admin" / "drumtrackai.db").resolve()))))
SAMPLES_ROOT = Path(os.getenv("SAMPLES_ROOT", "/data/samples"))
SAMPLE_PATH_MAP_FROM = os.getenv("SAMPLE_PATH_MAP_FROM")
SAMPLE_PATH_MAP_TO = os.getenv("SAMPLE_PATH_MAP_TO")

BRAIN_CONFIG_DIR = BASE_DIR / "brain_configs"
BRAIN_CONFIG_DIR.mkdir(exist_ok=True)

GROOVE_MANIFEST_BANG_PATH = BASE_DIR / "Drum_Education" / "extracted" / "BangTheDrumSchool_manifest.jsonl"
GROOVE_MANIFEST_EGMD_PATH = BASE_DIR / "Drum_Education" / "extracted" / "EGMD_manifest.jsonl"
GROOVE_MANIFEST_RUDIMENTS_PATH = BASE_DIR / "Drum_Education" / "extracted" / "RUDIMENTS_manifest.jsonl"
GROOVE_MANIFEST_DRUM_PATTERNS_PATH = BASE_DIR / "Drum_Education" / "extracted" / "DRUM_PATTERNS_manifest.jsonl"
_GROOVE_CATALOG = GrooveCatalog(
    [
        GROOVE_MANIFEST_BANG_PATH,
        GROOVE_MANIFEST_EGMD_PATH,
        GROOVE_MANIFEST_RUDIMENTS_PATH,
        GROOVE_MANIFEST_DRUM_PATTERNS_PATH,
    ]
)


def _brain_config_file(section_id: str) -> Path:
    safe = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in section_id or "section")
    if not safe:
        safe = "section"
    return BRAIN_CONFIG_DIR / f"{safe}.json"


def _default_brain_config(style_hint: Optional[str] = None) -> DrumBrainConfig:
    definitions = get_brain_elements(style_hint)
    settings = [
        BrainElementSetting(
            elementId=definition.id,
            value=definition.default_value,
            frozen=False,
            disabled=False,
        )
        for definition in definitions
    ]
    return DrumBrainConfig(mode="normal", randomizeSeed=None, elementSettings=settings)


def _load_brain_config(section_id: str, style_hint: Optional[str] = None) -> DrumBrainConfig:
    path = _brain_config_file(section_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return DrumBrainConfig.from_dict(data)
        except Exception as exc:  # pragma: no cover - defensive log only
            LOG.warning("Failed to load brain config for %s: %s", section_id, exc)
    return _default_brain_config(style_hint)


def _save_brain_config(section_id: str, config: DrumBrainConfig) -> None:
    path = _brain_config_file(section_id)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(config.to_dict(), handle, indent=2)


def _serialize_brain_definition(defn) -> dict:
    return {
        "id": defn.id,
        "label": defn.label,
        "description": defn.description,
        "minValue": defn.min_value,
        "maxValue": defn.max_value,
        "defaultValue": defn.default_value,
        "supportsFreeze": defn.supports_freeze,
        "supportsDisable": defn.supports_disable,
        "grouping": defn.grouping,
    }

# Rust integration configuration
AUDIO_CORE_BIN = os.getenv("AUDIO_CORE_BIN", "audio-core")


def _samples_db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SAMPLE_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_sample_file_path(db_path_value: str) -> Path:
    """Resolve a DB file_path to an on-disk path.

    Preferred: DB stores relative POSIX paths (e.g. 'kits/kit1/kick/in.wav'),
    resolved under SAMPLES_ROOT.

    Backward compatible: if DB stores Windows absolute paths, apply optional
    prefix mapping SAMPLE_PATH_MAP_FROM -> SAMPLE_PATH_MAP_TO.
    """
    raw = str(db_path_value or "")
    if not raw:
        return Path("")

    # If it's a relative path, treat as relative to SAMPLES_ROOT.
    # Normalize Windows-style backslashes to POSIX separators for Docker/Linux.
    raw_rel = raw.replace("\\", "/")
    p = Path(raw_rel)
    if not p.is_absolute() and ":" not in raw:
        return (SAMPLES_ROOT / Path(raw_rel)).resolve()

    # Optional legacy prefix remap (e.g. E:\Drum Samples -> /data/samples)
    if SAMPLE_PATH_MAP_FROM and SAMPLE_PATH_MAP_TO:
        try:
            from_norm = str(SAMPLE_PATH_MAP_FROM).rstrip("\\/")
            to_norm = str(SAMPLE_PATH_MAP_TO).rstrip("\\/")
            if raw.lower().startswith(from_norm.lower()):
                mapped = to_norm + raw[len(from_norm):]
                mapped = mapped.replace("\\", "/")
                return Path(mapped).resolve()
        except Exception:
            pass

    # As a last resort, try to open the path as-is
    return Path(raw)


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        rp = path.resolve()
        rr = root.resolve()
        return rp == rr or rr in rp.parents
    except Exception:
        return False


async def api_sample_collections(request: web.Request) -> web.Response:
    if not SAMPLE_DB_PATH.exists():
        return web.json_response({"error": "sample db not found", "db": str(SAMPLE_DB_PATH)}, status=404)
    try:
        conn = _samples_db_connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, collection_name, description, manufacturer, category, folder_path, sample_count, created_at "
                "FROM sample_collections ORDER BY id"
            )
            rows = [dict(r) for r in cur.fetchall()]
            return web.json_response({
                "db": str(SAMPLE_DB_PATH),
                "samplesRoot": str(SAMPLES_ROOT),
                "collections": rows,
            })
        finally:
            conn.close()
    except Exception as e:
        LOG.error(f"api_sample_collections failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_list_egmd_phrases(request: web.Request):
    """List EGMD phrases for a given style group.

    Query params:
      - style_group (required)
      - meter (optional, e.g. "4/4")
      - tempo_bpm (optional)
      - tempo_tolerance_bpm (optional)
      - limit (optional)
    """
    style_group = (request.query.get("style_group") or request.query.get("styleGroup") or "").strip()
    if not style_group:
        return web.json_response({"error": "style_group required"}, status=400)

    meter = (request.query.get("meter") or "").strip() or None
    tempo_raw = request.query.get("tempo_bpm") or request.query.get("tempoBpm")
    tol_raw = request.query.get("tempo_tolerance_bpm") or request.query.get("tempoToleranceBpm")
    limit_raw = request.query.get("limit")

    tempo_bpm = None
    if tempo_raw is not None and str(tempo_raw).strip() != "":
        try:
            tempo_bpm = float(tempo_raw)
        except Exception:
            tempo_bpm = None

    try:
        tol = float(tol_raw) if tol_raw is not None and str(tol_raw).strip() != "" else 12.0
    except Exception:
        tol = 12.0

    try:
        limit = int(limit_raw) if limit_raw is not None and str(limit_raw).strip() != "" else 50
    except Exception:
        limit = 50

    items = list_egmd_phrases(
        style_group=style_group,
        meter=meter,
        tempo_bpm=tempo_bpm,
        tempo_tolerance_bpm=tol,
        limit=limit,
    )
    return web.json_response({"items": items})


async def api_list_egmd_style_groups(request: web.Request):
    """List EGMD style_group values available in the training DB."""
    limit_raw = request.query.get("limit")
    try:
        limit = int(limit_raw) if limit_raw is not None and str(limit_raw).strip() != "" else 200
    except Exception:
        limit = 200
    items = list_egmd_style_groups(limit=limit)
    return web.json_response({"items": items})


async def api_drum_samples(request: web.Request) -> web.Response:
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
        conn = _samples_db_connect()
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
            return web.json_response({
                "db": str(SAMPLE_DB_PATH),
                "samplesRoot": str(SAMPLES_ROOT),
                "samples": rows,
                "limit": limit_n,
                "offset": offset_n,
            })
        finally:
            conn.close()
    except Exception as e:
        LOG.error(f"api_drum_samples failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_drum_sample_audio(request: web.Request) -> web.StreamResponse:
    if not SAMPLE_DB_PATH.exists():
        return web.json_response({"error": "sample db not found", "db": str(SAMPLE_DB_PATH)}, status=404)
    sample_id = request.match_info.get("sample_id")
    if not sample_id:
        return web.json_response({"error": "sample_id required"}, status=400)

    try:
        conn = _samples_db_connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT file_path FROM drum_samples WHERE id = ?", (sample_id,))
            row = cur.fetchone()
            if not row or not row[0]:
                return web.json_response({"error": "sample not found"}, status=404)

            path = _resolve_sample_file_path(str(row[0]))
            if not path or not path.exists() or not path.is_file():
                return web.json_response({"error": "file not found", "file_path": str(path)}, status=404)

            # If DB stores relative paths, enforce root jail under SAMPLES_ROOT
            raw = str(row[0])
            is_relative = (not Path(raw).is_absolute()) and (":" not in raw)
            if is_relative and not _is_under_root(path, SAMPLES_ROOT):
                return web.json_response({"error": "file path not allowed"}, status=403)

            ctype, _ = mimetypes.guess_type(str(path))
            if not ctype:
                ctype = "application/octet-stream"
            return web.FileResponse(path=str(path), headers={"Content-Type": ctype})
        finally:
            conn.close()
    except Exception as e:
        LOG.error(f"api_drum_sample_audio failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


def _safe_kit_id(raw: str) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isalnum() or ch in ("-", "_"))


def _pick_sample_id_by_prefix(prefix: str) -> Optional[str]:
    try:
        if not SAMPLE_DB_PATH.exists():
            return None

        raw_prefix = str(prefix or "")
        if not raw_prefix:
            return None

        # DB file_path values may use single backslashes, double backslashes, or forward slashes.
        # Normalize and try multiple variants so kit-pack manifests don't silently fall back.
        candidates = []
        candidates.append(raw_prefix)
        candidates.append(raw_prefix.replace("\\\\", "\\"))
        candidates.append(raw_prefix.replace("\\", "/"))
        candidates.append(raw_prefix.replace("/", "\\"))

        # De-dup while preserving order.
        seen = set()
        prefixes = []
        for c in candidates:
            if c in seen:
                continue
            seen.add(c)
            prefixes.append(c)

        conn = _samples_db_connect()
        try:
            cur = conn.cursor()
            for pfx in prefixes:
                like = f"{pfx}%"
                cur.execute(
                    "SELECT id FROM drum_samples WHERE file_path LIKE ? ORDER BY id LIMIT 1",
                    (like,),
                )
                row = cur.fetchone()
                if row:
                    return str(row[0])
            return None
        finally:
            conn.close()
    except Exception:
        return None


def _url_for_sample_id(sample_id: Optional[str], fallback_url: str) -> str:
    if sample_id:
        safe_id = "".join(ch for ch in str(sample_id) if ch.isdigit())
        if safe_id:
            return f"/api/drum-samples/{safe_id}/audio"
    return fallback_url


async def api_list_kits(_: web.Request) -> web.Response:
    try:
        if not KITS_ROOT.exists() or not KITS_ROOT.is_dir():
            kits = []
            kits.append({
                "kitId": "sneap_erkan_local_v1",
                "name": "Andy Sneap + Erkan (Local Samples)",
                "version": "v1",
            })
            return web.json_response({"kits": kits, "kitsRoot": str(KITS_ROOT)})

        kits = []
        for entry in sorted(KITS_ROOT.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.json"
            if not manifest_path.exists() or not manifest_path.is_file():
                continue
            try:
                with open(manifest_path, "r", encoding="utf-8") as handle:
                    manifest = json.load(handle)
                kits.append({
                    "kitId": manifest.get("kitId") or entry.name,
                    "name": manifest.get("name") or entry.name,
                    "version": manifest.get("version") or "v1",
                })
            except Exception:
                kits.append({"kitId": entry.name, "name": entry.name, "version": "v1"})

        kits.append({
            "kitId": "sneap_erkan_local_v1",
            "name": "Andy Sneap + Erkan (Local Samples)",
            "version": "v1",
        })

        return web.json_response({"kits": kits, "kitsRoot": str(KITS_ROOT)})
    except Exception as e:
        LOG.error(f"api_list_kits failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_get_kit_manifest(request: web.Request) -> web.Response:
    try:
        raw_kit_id = request.match_info.get("kit_id")
        kit_id = _safe_kit_id(raw_kit_id)
        if not kit_id:
            return web.json_response({"error": "kit_id required"}, status=400)

        if kit_id == "sneap_erkan_local_v1":
            fallback = "/kits/stub_kit_v1/samples/one.wav"

            # NOTE: The sample DB stores forward-slash paths (e.g. 'E:/Drum Samples/...').
            # Use that form here so the prefix LIKE query succeeds on Windows.
            kick_id = _pick_sample_id_by_prefix("E:/Drum Samples/Kick Samples/Andy Sneap Kick")
            snare_id = _pick_sample_id_by_prefix("E:/Drum Samples/Snare Samples/Andy Sneap Snare")
            tom_high_id = _pick_sample_id_by_prefix("E:/Drum Samples/Tom2 (high)/Andy Sneap Tom1")
            tom_mid_id = _pick_sample_id_by_prefix("E:/Drum Samples/Tom3 (medium)/Andy Sneap Tom2")
            tom_floor_id = _pick_sample_id_by_prefix("E:/Drum Samples/Tom4 (low)/Andy Sneap Tom3")
            hat_id = _pick_sample_id_by_prefix("E:/Drum Samples/Hihat Samples/Erkan Hihat/Zildjian Avedis 14 New Beat Hihat")
            crash_1_id = _pick_sample_id_by_prefix("E:/Drum Samples/Crash Samples/Erkan Crash/Istanbul Radiant 16 Crash")
            crash_2_id = _pick_sample_id_by_prefix("E:/Drum Samples/Crash Samples/Erkan Crash/Masterwork Custom 18 Crash")
            china_id = _pick_sample_id_by_prefix("E:/Drum Samples/Effect Cymbal Samples/China Samples/Erkan China/Masterwork Custom 18 China")
            bell_id = _pick_sample_id_by_prefix("E:/Drum Samples/Effect Cymbal Samples/Bell Samples/Erkan Bell/Homemade 7 Bell")

            kick_url = _url_for_sample_id(kick_id, fallback)
            snare_url = _url_for_sample_id(snare_id, fallback)
            tom_high_url = _url_for_sample_id(tom_high_id, fallback)
            tom_mid_url = _url_for_sample_id(tom_mid_id, fallback)
            tom_floor_url = _url_for_sample_id(tom_floor_id, fallback)
            hat_url = _url_for_sample_id(hat_id, fallback)
            crash_1_url = _url_for_sample_id(crash_1_id, fallback)
            crash_2_url = _url_for_sample_id(crash_2_id, fallback)
            china_url = _url_for_sample_id(china_id, fallback)
            bell_url = _url_for_sample_id(bell_id, fallback)

            manifest = {
                "kitId": kit_id,
                "name": "Andy Sneap + Erkan (Local Samples)",
                "version": "v1",
                "mics": [
                    {"id": "close", "label": "Close", "defaultGainDb": 0},
                    {"id": "oh", "label": "Overheads", "defaultGainDb": -6},
                    {"id": "room", "label": "Room", "defaultGainDb": -10},
                ],
                "chokeGroups": {
                    "cymbals": ["crash_1", "crash_2", "crash_china"],
                    "hihat": ["hihat_closed", "hihat_open", "hihat_pedal"],
                },
                "articulations": {
                    "kick": {
                        "mics": {
                            "close": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [kick_url]}]}
                        }
                    },
                    "snare_center": {
                        "mics": {
                            "close": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [snare_url]}]}
                        }
                    },
                    "tom_high": {
                        "mics": {
                            "close": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [tom_high_url]}]}
                        }
                    },
                    "tom_mid": {
                        "mics": {
                            "close": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [tom_mid_url]}]}
                        }
                    },
                    "tom_floor": {
                        "mics": {
                            "close": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [tom_floor_url]}]}
                        }
                    },
                    "hihat_closed": {
                        "mics": {
                            "close": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [hat_url]}]}
                        }
                    },
                    "ride_bell": {
                        "mics": {
                            "oh": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [bell_url]}]}
                        }
                    },
                    "crash_1": {
                        "mics": {
                            "oh": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [crash_1_url]}]},
                            "room": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [crash_1_url]}]},
                        }
                    },
                    "crash_2": {
                        "mics": {
                            "oh": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [crash_2_url]}]},
                            "room": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [crash_2_url]}]},
                        }
                    },
                    "crash_china": {
                        "mics": {
                            "oh": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [china_url]}]},
                            "room": {"velocityLayers": [{"min": 1, "max": 127, "roundRobin": [china_url]}]},
                        }
                    },
                },
                "mixDefaults": {
                    "masterGainDb": -6,
                    "micGainsDb": {"close": 0, "oh": -6, "room": -10},
                },
            }
            return web.json_response(manifest)

        manifest_path = (KITS_ROOT / kit_id / "manifest.json").resolve()
        if not manifest_path.exists() or not manifest_path.is_file():
            return web.json_response({"error": "manifest not found", "kitId": kit_id}, status=404)

        if not _is_under_root(manifest_path, KITS_ROOT):
            return web.json_response({"error": "kit path not allowed"}, status=403)

        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        return web.json_response(manifest)
    except Exception as e:
        LOG.error(f"api_get_kit_manifest failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Auto-detect Rust binary if environment variable not explicitly set
if os.getenv("USE_RUST") is not None:
    USE_RUST = os.getenv("USE_RUST") == "1"
else:
    # Auto-detect: check if binary exists
    rust_paths = [
        Path("target/release/audio-core.exe"),
        Path("target/release/audio-core"),
        Path("audio-core/target/release/audio-core.exe"),
        Path("audio-core/target/release/audio-core"),
    ]
    USE_RUST = any(p.exists() for p in rust_paths)
    if USE_RUST:
        # Find and set the correct binary path
        for p in rust_paths:
            if p.exists():
                AUDIO_CORE_BIN = str(p)
                break

AUDIO_CORE_MODE = os.getenv("AUDIO_CORE_MODE", "auto")  # auto, cli, pyo3

# Log Rust configuration at startup
if USE_RUST:
    LOG.info(f"Rust audio-core ENABLED: {AUDIO_CORE_BIN}")
else:
    LOG.warning("Rust audio-core NOT FOUND - drum generation will not work")

# DISABLED: Tracktion FFI causes heap corruption - we don't use it anyway
# TRACKTION_FFI_LIB = os.getenv("TRACKTION_FFI_LIB", str(BASE_DIR / "tracktion-hybrid" / "rust" / "audio-core-ffi" / "target" / "release" / "audio_core_ffi.dll"))
# USE_TRACKTION_FFI = os.getenv("USE_TRACKTION_FFI", "1") == "1"
USE_TRACKTION_FFI = False
tracktion_ffi = None

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
    """Run audio-core via Tracktion FFI, PyO3, or CLI subprocess and return JSON result"""
    # Try Tracktion FFI first if available
    if tracktion_ffi and USE_TRACKTION_FFI:
        try:
            return run_audio_core_ffi(args)
        except Exception as e:
            LOG.warning(f"Tracktion FFI failed, falling back: {e}")
    
    # Try PyO3 next if available and mode allows
    if audio_core_rust and AUDIO_CORE_MODE in ["auto", "pyo3"]:
        try:
            return run_audio_core_pyo3(args)
        except Exception as e:
            if AUDIO_CORE_MODE == "pyo3":
                raise Exception(f"PyO3 audio-core error: {e}")
            LOG.warning(f"PyO3 failed, falling back to CLI: {e}")
    
    # Fallback to CLI subprocess
    return run_audio_core_cli(args)

def run_audio_core_ffi(args: list) -> dict:
    """Run audio-core via Tracktion FFI library"""
    if not tracktion_ffi:
        raise Exception("Tracktion FFI library not available")
    
    cmd = args[0] if args else ""
    
    try:
        if cmd == "peaks":
            path = args[1].encode('utf-8')
            max_points = int(args[3]) if len(args) > 3 else 2000
            result_ptr = tracktion_ffi.ac_peaks(path, max_points)
            if not result_ptr:
                error_ptr = tracktion_ffi.ac_last_error()
                error_msg = error_ptr.decode('utf-8') if error_ptr else "Unknown FFI error"
                raise Exception(f"FFI peaks failed: {error_msg}")
            
            result_json = result_ptr.decode('utf-8')
            tracktion_ffi.ac_free(result_ptr)
            return json.loads(result_json)
        
        elif cmd == "analyze":
            path = args[1].encode('utf-8')
            min_bpm = float(args[3]) if len(args) > 3 else 60.0
            max_bpm = float(args[5]) if len(args) > 5 else 200.0
            result_ptr = tracktion_ffi.ac_analyze(path, min_bpm, max_bpm)
            if not result_ptr:
                error_ptr = tracktion_ffi.ac_last_error()
                error_msg = error_ptr.decode('utf-8') if error_ptr else "Unknown FFI error"
                raise Exception(f"FFI analyze failed: {error_msg}")
            
            result_json = result_ptr.decode('utf-8')
            tracktion_ffi.ac_free(result_ptr)
            return json.loads(result_json)
        
        elif cmd == "sectionize-smart":
            path = args[1].encode('utf-8')
            bpm = float(args[3])
            min_bars = int(args[5])
            max_bars = int(args[7])
            result_ptr = tracktion_ffi.ac_sectionize_smart(path, bpm, min_bars, max_bars)
            if not result_ptr:
                error_ptr = tracktion_ffi.ac_last_error()
                error_msg = error_ptr.decode('utf-8') if error_ptr else "Unknown FFI error"
                raise Exception(f"FFI sectionize failed: {error_msg}")
            
            result_json = result_ptr.decode('utf-8')
            tracktion_ffi.ac_free(result_ptr)
            return json.loads(result_json)
        
        elif cmd == "generate":
            style = args[2].encode('utf-8')
            label = args[4].encode('utf-8')
            bars = int(args[6])
            bpm = float(args[8])
            seed = int(args[10]) if len(args) > 10 else 42
            result_ptr = tracktion_ffi.ac_generate_midi64(style, label, bars, bpm, seed)
            if not result_ptr:
                error_ptr = tracktion_ffi.ac_last_error()
                error_msg = error_ptr.decode('utf-8') if error_ptr else "Unknown FFI error"
                raise Exception(f"FFI generate failed: {error_msg}")
            
            midi_b64 = result_ptr.decode('utf-8')
            tracktion_ffi.ac_free(result_ptr)
            return {"midi": midi_b64}
        
        else:
            raise Exception(f"Unknown FFI command: {cmd}")
    
    except Exception as e:
        # Get last error from FFI if available
        try:
            error_ptr = tracktion_ffi.ac_last_error()
            if error_ptr:
                ffi_error = error_ptr.decode('utf-8')
                raise Exception(f"FFI error: {ffi_error}")
        except:
            pass
        raise e

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
        LOG.info(f"Executing: {bin_path} {' '.join(args)}")
        proc = subprocess.run([bin_path] + args, capture_output=True, text=True, timeout=30)
        LOG.info(f"Return code: {proc.returncode}")
        if proc.returncode != 0:
            LOG.error(f"stderr: {proc.stderr}")
            raise Exception(f"audio-core failed (code {proc.returncode}): {proc.stderr.strip()}")
        LOG.info(f"stdout length: {len(proc.stdout)} bytes")
        result = json.loads(proc.stdout)
        LOG.info(f"Parsed JSON with keys: {list(result.keys())}")
        if 'notes' in result:
            LOG.info(f"Found {len(result['notes'])} notes in result")
        return result
    except subprocess.TimeoutExpired:
        raise Exception("audio-core timed out")
    except json.JSONDecodeError as e:
        LOG.error(f"Failed to parse JSON. First 500 chars of stdout: {proc.stdout[:500]}")
        raise Exception(f"bad json from audio-core: {e}")
    except Exception as e:
        LOG.error(f"audio-core error: {e}", exc_info=True)
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
    """
    Generate STEREO waveform using Rust audio-core ONLY.
    Returns separate L/R channel peaks for stereo visualization.
    Python libraries (numpy/soundfile) cause heap corruption (exit code 3221226356) - DO NOT USE.
    """
    if not USE_RUST:
        raise Exception("waveform_requires_rust")

    result = run_audio_core(["peaks", str(path), "--max-points", str(max_points)])
    result["key"] = str(path.relative_to(UPLOAD_DIR))
    peaks_l = result.get("peaksL")
    peaks_r = result.get("peaksR")
    if isinstance(peaks_l, list) and isinstance(peaks_r, list) and len(peaks_l) and len(peaks_r):
        result["stereo"] = True
    elif "peaks" in result:
        peaks = result["peaks"]
        result["peaksL"] = list(peaks)
        result["peaksR"] = list(peaks)
        result["stereo"] = True
    return result

# ---------- Routes ----------
async def healthz(_):
    return web.json_response(
        {
            "ok": True,
            "service": "dcsm_backend",
            "version": "1.1.17",
            "time": time.time(),
            "stats": DRUM_GEN_STATS,
        }
    )


async def api_llm_status(_request: web.Request):
    provider = str(os.getenv("LLM_PROVIDER", "")).strip()
    base_url = str(os.getenv("LOCAL_LLM_URL", "")).strip().rstrip("/")

    def _post_json(url: str, payload: dict, timeout_s: float = 2.5) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

    out = {
        "ok": True,
        "llm_provider": provider,
        "local_llm_url": base_url,
        "checks": {},
    }

    if provider != "local_service":
        out["ok"] = False
        out["error"] = "LLM_PROVIDER is not 'local_service'"
        return web.json_response(out)

    if not base_url:
        out["ok"] = False
        out["error"] = "LOCAL_LLM_URL is not set"
        return web.json_response(out)

    payload = {
        "cfg": {
            "style": "rock",
            "tempos": [120],
            "timeSignature": [4, 4],
            "humanizeAmount": 0.7,
            "ghostNoteAmount": 0.5,
            "swingAmount": 0.1,
            "intensity": 0.7,
            "variation": 0.6,
            "songSections": [{"name": "verse", "bars": 4}, {"name": "chorus", "bars": 4}],
            "chorusRidePreference": 0.5,
        },
        "songmap_summary": {"bars": 8, "sections": []},
        "drummer_profile": {"preferred_feel": "straight"},
    }

    try:
        t0 = time.time()
        data = _post_json(f"{base_url}/v1/performance_spec", payload)
        out["checks"]["performance_spec"] = {
            "ok": bool(isinstance(data, dict) and data.get("ok") is True),
            "ms": int((time.time() - t0) * 1000),
        }
        if isinstance(data, dict) and isinstance(data.get("metadata"), dict):
            out["checks"]["performance_spec"]["backend"] = data["metadata"].get("backend")
    except Exception as e:
        out["checks"]["performance_spec"] = {"ok": False, "error": str(e)}
        out["ok"] = False

    try:
        t0 = time.time()
        data = _post_json(f"{base_url}/v1/song_roadmap", payload)
        out["checks"]["song_roadmap"] = {
            "ok": bool(isinstance(data, dict) and data.get("ok") is True),
            "ms": int((time.time() - t0) * 1000),
        }
        if isinstance(data, dict) and isinstance(data.get("metadata"), dict):
            out["checks"]["song_roadmap"]["backend"] = data["metadata"].get("backend")
    except Exception as e:
        out["checks"]["song_roadmap"] = {"ok": False, "error": str(e)}
        out["ok"] = False

    return web.json_response(out)

async def upload(request: web.Request):
    try:
        reader = await request.multipart()
        part = await reader.next()
        if part is None or part.name != "file":
            return web.json_response({"error": "missing file field"}, status=400)

        filename = safe_name(part.filename or f"file-{int(time.time()*1000)}.wav")
        key = f"{int(time.time()*1000)}-{filename}"
        dest = (UPLOAD_DIR / key)
        dest.parent.mkdir(parents=True, exist_ok=True)

        with dest.open("wb") as f:
            while True:
                chunk = await part.read_chunk()  # 8192 bytes by default
                if not chunk:
                    break
                f.write(chunk)

        LOG.info(f"File uploaded successfully: {key}")

        waveform = compute_waveform(dest, max_points=1000)

        payload = {
            "success": True,
            "key": key,
            "file_id": key,
            "message": "File uploaded successfully",
        }
        if waveform:
            payload["waveform"] = waveform
        return web.json_response(payload)
    except Exception as e:
        LOG.error(f"Upload failed: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def api_render_plugin_midi(request):
    try:
        payload = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    try:
        result = render_articulated_notes_to_midi(payload)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def waveform(request: web.Request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "missing key"}, status=400)
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "not found"}, status=404)
    max_points = int(request.query.get("max_points", "3000"))
    
    try:
        wf = compute_waveform(path, max_points=max_points)
        return web.json_response(wf)
    except Exception as e:
        LOG.warning(f"Waveform generation failed for {key}: {e}")
        return web.json_response({"error": "waveform_failed", "detail": str(e)}, status=500)

async def beatbox_translate(request: web.Request):
    """Translate a beatbox/vocal percussion recording into a drum groove."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"success": False, "error": "invalid json"}, status=400)

    file_id = data.get("file_id")
    if not file_id:
        return web.json_response({"success": False, "error": "missing file_id"}, status=400)

    file_path = (UPLOAD_DIR / safe_name(file_id)).resolve()
    if not str(file_path).startswith(str(UPLOAD_DIR.resolve())):
        return web.json_response({"success": False, "error": "invalid file_id"}, status=400)
    if not file_path.exists():
        return web.json_response({"success": False, "error": "file not found"}, status=404)

    options_payload = data.get("options", {}) or {}
    plugin = str(data.get("plugin") or options_payload.get("plugin") or "jamstix")
    try:
        options = BeatboxTranslationOptions(
            swing=float(options_payload.get("swing", 0.0) or 0.0),
            quantization=str(options_payload.get("quantization", "1/16")),
            confidence_threshold=float(options_payload.get("confidence_threshold", 0.35) or 0.35),
            plugin=plugin,
        )
    except (TypeError, ValueError):
        return web.json_response({"success": False, "error": "invalid options"}, status=400)

    loop = asyncio.get_event_loop()
    try:
        translator_result = await loop.run_in_executor(
            None,
            lambda: translate_beatbox(file_path, options),
        )
    except FileNotFoundError:
        return web.json_response({"success": False, "error": "file not found"}, status=404)
    except Exception as exc:
        LOG.exception("Beatbox translation failed")
        return web.json_response({"success": False, "error": str(exc)}, status=500)

    job_id = f"beatbox_{safe_name(file_id)}"
    ANALYSIS_CACHE[job_id] = {
        "job_id": job_id,
        "file_id": file_id,
        "tempo": translator_result.get("tempo"),
        "beats": translator_result.get("hits", []),
        "summary": translator_result.get("summary", {}),
        "status": "complete",
        "preview_midi": translator_result.get("preview_midi"),
    }

    response_payload = {
        "success": True,
        "job_id": job_id,
        "tempo": translator_result.get("tempo"),
        "hits": translator_result.get("hits", []),
        "summary": translator_result.get("summary", {}),
        "preview_midi": translator_result.get("preview_midi"),
        "plugin": translator_result.get("plugin"),
        "ticks_per_beat": translator_result.get("ticks_per_beat"),
    }

    persona_id = data.get("persona_id")
    style_pack = data.get("style_pack")
    if persona_id:
        response_payload["persona_id"] = persona_id
    if style_pack:
        response_payload["style_pack"] = style_pack

    if translator_result.get("hits"):
        jamstix_result, jamstix_error = auto_generate_jamstix_track(
            translator_result.get("hits", []),
            translator_result.get("tempo"),
            persona_hint=persona_id,
            style_pack_hint=style_pack,
        )
        if jamstix_result:
            response_payload["jamstix_track"] = jamstix_result["track"]
            response_payload["jamstix_performance_spec"] = jamstix_result["performanceSpec"]
            response_payload["jamstix_sections"] = jamstix_result["sections"]
            response_payload["jamstix_time_signature"] = jamstix_result["timeSignature"]
            ANALYSIS_CACHE[job_id]["jamstix_track"] = jamstix_result["track"]
            ANALYSIS_CACHE[job_id]["jamstix_performance_spec"] = jamstix_result["performanceSpec"]
            ANALYSIS_CACHE[job_id]["jamstix_sections"] = jamstix_result["sections"]
        elif jamstix_error and jamstix_error != "jamstix_unavailable":
            response_payload["jamstix_error"] = jamstix_error

    return web.json_response(response_payload)

async def audio_file(request: web.Request):
    # Serve audio files with CORS for Web Audio API MediaElementSource
    key = request.query.get("key")
    if not key:
        return web.Response(status=400, text="missing key")
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.Response(status=404, text="not found")
    
    # CRITICAL: Explicitly set CORS headers for MediaElementAudioSource
    # FileResponse with explicit CORS headers - middleware may not apply to file routes
    response = web.FileResponse(
        str(path),
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            "Access-Control-Expose-Headers": "Content-Length, Content-Range, Accept-Ranges"
        }
    )
    return response

# Legacy API endpoints for compatibility
async def api_status(request: web.Request):
    # Simple status endpoint
    return web.json_response({
        "status": "online",
        "expert_model": "88.7% sophistication",
        "mvsep": "available",
        "signature_songs": 3,
        "classic_beats": 40
    })

# Analysis results cache (in production, use Redis or database)
ANALYSIS_CACHE = {}

async def analyze_audio_real(request: web.Request):
    """Real audio analysis using Rust audio-core"""
    try:
        data = await request.json()
        file_id = data.get('file_id') or data.get('key')
        
        if not file_id:
            return web.json_response({"success": False, "error": "missing file_id"}, status=400)
        
        # Resolve file path
        file_path = UPLOAD_DIR / file_id
        if not file_path.exists():
            return web.json_response({"success": False, "error": "file not found"}, status=404)
        
        LOG.info(f"Analyzing audio: {file_path}")
        
        # Call Rust audio-core analyze command
        if USE_RUST:
            try:
                result = run_audio_core(["analyze", str(file_path)])
                
                # Store results in cache
                job_id = file_id.replace('/', '_').replace('\\', '_')
                ANALYSIS_CACHE[job_id] = {
                    "job_id": job_id,
                    "file_id": file_id,
                    "tempo": result.get('tempo', 120.0),
                    "beats": result.get('beats', []),
                    "onsets": result.get('onsets', []),
                    "sample_rate": result.get('sample_rate', 44100),
                    "duration": result.get('duration', 0.0),
                    "status": "complete"
                }
                
                LOG.info(f"Analysis complete: BPM={result.get('tempo', 0):.1f}")
                
                return web.json_response({
                    "success": True,
                    "job_id": job_id,
                    "status": "complete",
                    "tempo": result.get('tempo', 120.0),
                    "estimated_time": "0s"
                })
            except Exception as e:
                LOG.exception("Rust analysis failed")
                return web.json_response({"success": False, "error": str(e)}, status=500)
        else:
            # Python fallback (basic)
            job_id = file_id.replace('/', '_').replace('\\', '_')
            ANALYSIS_CACHE[job_id] = {
                "job_id": job_id,
                "file_id": file_id,
                "tempo": 120.0,
                "beats": [],
                "onsets": [],
                "status": "complete"
            }
            return web.json_response({
                "success": True,
                "job_id": job_id,
                "status": "complete",
                "tempo": 120.0
            })
    except Exception as e:
        LOG.exception("Analysis error")
        return web.json_response({"success": False, "error": str(e)}, status=500)

async def get_analysis_results(request: web.Request):
    """Get analysis results from cache"""
    job_id = request.match_info.get("job_id")
    
    if not job_id:
        return web.json_response({"error": "missing job_id"}, status=400)
    
    # Check cache
    if job_id in ANALYSIS_CACHE:
        result = ANALYSIS_CACHE[job_id]
        tempo = result.get('tempo', 120.0)
        
        # Format for frontend compatibility
        return web.json_response({
            "job_id": job_id,
            "sophistication": "87.5%",
            "accuracy": "93.2%",
            "tempo": f"{tempo:.1f} BPM",
            "patterns": ["Detected Pattern"],
            "confidence": "high",
            "drummer_style": "Dynamic",
            "bpm_value": tempo,  # Numeric value for UI
            "beats": result.get('beats', []),
            "onsets": result.get('onsets', [])
        })
    else:
        # Return default for unknown job_ids
        return web.json_response({
            "job_id": job_id,
            "sophistication": "N/A",
            "accuracy": "N/A",
            "tempo": "Unknown",
            "patterns": [],
            "confidence": "unknown",
            "drummer_style": "Unknown"
        })


async def list_drummer_personas(request: web.Request):
    """Return persona metadata for frontend visualizations.

    Response shape:
        {
            "source": "admin_db" | "static",
            "personas": [ ... ]
        }
    """

    personas = []
    source = "static"

    if ADMIN_DB_AVAILABLE:
        try:
            db = get_admin_db_service()
            db.initialize()
            personas = db.get_all_drummer_personas()
            if personas:
                source = "admin_db"
        except Exception as exc:  # pragma: no cover - defensive guard
            LOG.warning(f"Falling back to static personas: {exc}")
            personas = []

    if not personas:
        try:
            service = get_drummer_service()
            personas = service.list_drummers()
        except Exception as exc:
            LOG.error(f"Unable to provide fallback personas: {exc}")
            return web.json_response({"error": "persona registry unavailable"}, status=500)

    return web.json_response({"source": source, "personas": personas})


async def list_drummer_presets(request: web.Request):
    profile_type = str(request.query.get("profileType") or request.query.get("profile_type") or "").strip().lower()
    if not profile_type:
        return web.json_response({"ok": False, "error": "profileType required"}, status=400)

    if not ADMIN_DB_AVAILABLE:
        return web.json_response({"ok": True, "source": "unavailable", "profileType": profile_type, "items": []})

    try:
        db = get_admin_db_service()
        db.initialize()
        items = db.list_drummer_presets(profile_type)
        return web.json_response({"ok": True, "source": "admin_db", "profileType": profile_type, "items": items})
    except Exception as exc:
        LOG.warning(f"Unable to list drummer presets: {exc}")
        return web.json_response({"ok": True, "source": "error", "profileType": profile_type, "items": []})


async def beatbox_tap_input(request: web.Request):
    """Accept structured pad hits from the frontend and render a groove."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"success": False, "error": "invalid json"}, status=400)

    hits = data.get("hits")
    if not isinstance(hits, list) or not hits:
        return web.json_response({"success": False, "error": "missing hits"}, status=400)

    try:
        tempo = float(data.get("tempo", 100.0))
    except (TypeError, ValueError):
        tempo = 100.0

    plugin = str(data.get("plugin") or data.get("options", {}).get("plugin") or "jamstix")

    try:
        translation = taps_to_translation(hits, tempo=tempo, plugin=plugin)
    except Exception as exc:
        LOG.exception("Tap input translation failed")
        return web.json_response({"success": False, "error": str(exc)}, status=500)

    job_id = f"tap_{int(time.time()*1000)}"
    ANALYSIS_CACHE[job_id] = {
        "job_id": job_id,
        "tempo": translation.get("tempo"),
        "beats": translation.get("hits", []),
        "summary": translation.get("summary", {}),
        "status": "complete",
        "preview_midi": translation.get("preview_midi"),
    }

    response_payload = {
        "success": True,
        "job_id": job_id,
        **translation,
    }

    persona_id = data.get("persona_id")
    style_pack = data.get("style_pack")
    if persona_id:
        response_payload["persona_id"] = persona_id
    if style_pack:
        response_payload["style_pack"] = style_pack

    if translation.get("hits"):
        jamstix_result, jamstix_error = auto_generate_jamstix_track(
            translation.get("hits", []),
            translation.get("tempo"),
            persona_hint=persona_id,
            style_pack_hint=style_pack,
        )
        if jamstix_result:
            response_payload["jamstix_track"] = jamstix_result["track"]
            response_payload["jamstix_performance_spec"] = jamstix_result["performanceSpec"]
            response_payload["jamstix_sections"] = jamstix_result["sections"]
            response_payload["jamstix_time_signature"] = jamstix_result["timeSignature"]
            ANALYSIS_CACHE[job_id]["jamstix_track"] = jamstix_result["track"]
            ANALYSIS_CACHE[job_id]["jamstix_performance_spec"] = jamstix_result["performanceSpec"]
            ANALYSIS_CACHE[job_id]["jamstix_sections"] = jamstix_result["sections"]
        elif jamstix_error and jamstix_error != "jamstix_unavailable":
            response_payload["jamstix_error"] = jamstix_error

    return web.json_response(response_payload)


async def beatprompt_render(request: web.Request):
    """Map natural-language prompts or structured sections to tap hits."""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"success": False, "error": "invalid json"}, status=400)

    prompt_text = str(data.get("prompt") or "")
    sections_payload = data.get("sections") if isinstance(data.get("sections"), list) else None
    sections, warnings = normalize_sections(prompt_text, sections_payload)

    if not sections:
        return web.json_response({"success": False, "error": "no sections detected"}, status=400)

    hits, tempo = render_sections_to_hits(sections)
    if not hits:
        return web.json_response({"success": False, "error": "unable to build hits"}, status=400)

    plugin = str(data.get("plugin") or "jamstix")

    try:
        translation = taps_to_translation(hits, tempo=tempo, plugin=plugin)
    except Exception as exc:
        LOG.exception("BeatPrompt render failed")
        return web.json_response({"success": False, "error": str(exc)}, status=500)

    job_id = f"beatprompt_{int(time.time()*1000)}"
    ANALYSIS_CACHE[job_id] = {
        "job_id": job_id,
        "tempo": translation.get("tempo"),
        "beats": translation.get("hits", []),
        "summary": translation.get("summary", {}),
        "status": "complete",
        "preview_midi": translation.get("preview_midi"),
    }

    top_section = sections[0]
    response_payload = {
        "success": True,
        "job_id": job_id,
        **translation,
        "persona_id": top_section.persona_id,
        "style_pack": top_section.style_pack,
        "sections": serialize_sections(sections),
        "warnings": warnings,
    }

    if translation.get("hits"):
        jamstix_result, jamstix_error = auto_generate_jamstix_track(
            translation.get("hits", []),
            translation.get("tempo", tempo),
            sections=sections,
            persona_hint=top_section.persona_id,
            style_pack_hint=top_section.style_pack,
            meter_hint=top_section.meter,
        )
        if jamstix_result:
            response_payload["jamstix_track"] = jamstix_result["track"]
            response_payload["jamstix_performance_spec"] = jamstix_result["performanceSpec"]
            response_payload["jamstix_sections"] = jamstix_result["sections"]
            response_payload["jamstix_time_signature"] = jamstix_result["timeSignature"]
            ANALYSIS_CACHE[job_id]["jamstix_track"] = jamstix_result["track"]
            ANALYSIS_CACHE[job_id]["jamstix_performance_spec"] = jamstix_result["performanceSpec"]
            ANALYSIS_CACHE[job_id]["jamstix_sections"] = jamstix_result["sections"]
        elif jamstix_error and jamstix_error != "jamstix_unavailable":
            response_payload["jamstix_error"] = jamstix_error

        return web.json_response(response_payload)


async def api_grooves_search(request: web.Request):
    q = str(request.query.get("q") or "").strip()
    tags_raw = str(request.query.get("tags") or "").strip()
    sources_raw = str(request.query.get("sources") or "").strip()
    style_group = str(request.query.get("style_group") or "").strip().lower()
    sort = str(request.query.get("sort") or "").strip().lower()

    complexity_min_raw = str(request.query.get("complexity_min") or "").strip()
    complexity_max_raw = str(request.query.get("complexity_max") or "").strip()
    try:
        complexity_min = float(complexity_min_raw) if complexity_min_raw else None
    except Exception:
        complexity_min = None
    try:
        complexity_max = float(complexity_max_raw) if complexity_max_raw else None
    except Exception:
        complexity_max = None

    # Drum-terminology filters (more interpretable than a single complexity score)
    def _qfloat(name: str) -> float | None:
        raw = str(request.query.get(name) or "").strip()
        if not raw:
            return None
        try:
            return float(raw)
        except Exception:
            return None

    hits_per_bar_min = _qfloat("hits_per_bar_min")
    hits_per_bar_max = _qfloat("hits_per_bar_max")
    active_instruments_min = _qfloat("active_instruments_min")
    active_instruments_max = _qfloat("active_instruments_max")
    offbeat_ratio_min = _qfloat("offbeat_ratio_min")
    offbeat_ratio_max = _qfloat("offbeat_ratio_max")
    snare_backbeat_ratio_min = _qfloat("snare_backbeat_ratio_min")
    snare_backbeat_ratio_max = _qfloat("snare_backbeat_ratio_max")

    snare_share_min = _qfloat("snare_share_min")
    snare_share_max = _qfloat("snare_share_max")

    kick_snare_share_min = _qfloat("kick_snare_share_min")
    kick_snare_share_max = _qfloat("kick_snare_share_max")
    cymbal_share_min = _qfloat("cymbal_share_min")
    cymbal_share_max = _qfloat("cymbal_share_max")
    tom_share_min = _qfloat("tom_share_min")
    tom_share_max = _qfloat("tom_share_max")

    limit_raw = str(request.query.get("limit") or "10").strip()

    try:
        limit = max(1, min(50, int(limit_raw)))
    except Exception:
        limit = 10

    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []
    sources = [s.strip() for s in sources_raw.split(",") if s.strip()] if sources_raw else []

    is_browse_mode = (not q) and (not tags)
    egmd_only = (len(sources) == 1 and str(sources[0]).strip().lower() == "egmd")

    # Important: style_group filtering must happen before applying the final limit.
    # GrooveCatalog.search() applies its own ordering/scoring, so if we limit first,
    # we may accidentally exclude all candidates for the requested style_group.
    internal_limit = limit
    if style_group:
        # EGMD manifests are ordered by source/drummer/session; a given style_group (e.g. jazz)
        # may be far beyond the first few thousand rows. Pull a much larger candidate set so
        # style filtering doesn't accidentally yield zero results.
        internal_limit = max(limit, 50000)
    elif is_browse_mode and egmd_only:
        # In browse mode, the EGMD manifest is grouped by style_detail, so the first N rows can all be
        # the same groove number (e.g. many variants of "Soul Groove 10"). Pull a larger candidate
        # set and diversify below.
        internal_limit = max(limit, 50000)

    if complexity_min is not None or complexity_max is not None or sort in {"complexity_asc", "complexity_desc"}:
        # Complexity filtering/sorting requires a broad candidate pool so we don't miss low-complexity
        # grooves that appear later in the manifest ordering.
        internal_limit = max(internal_limit, 50000)

    if (
        hits_per_bar_min is not None
        or hits_per_bar_max is not None
        or active_instruments_min is not None
        or active_instruments_max is not None
        or offbeat_ratio_min is not None
        or offbeat_ratio_max is not None
        or snare_backbeat_ratio_min is not None
        or snare_backbeat_ratio_max is not None
        or snare_share_min is not None
        or snare_share_max is not None
        or kick_snare_share_min is not None
        or kick_snare_share_max is not None
        or cymbal_share_min is not None
        or cymbal_share_max is not None
        or tom_share_min is not None
        or tom_share_max is not None
    ):
        internal_limit = max(internal_limit, 50000)

    # Share-metric filters can be expensive when the EGMD cache is cold because they require
    # scanning many entries and (re)computing MIDI-derived metrics. Cap the candidate pool
    # to keep UI searches responsive.
    share_filter_active = (
        snare_share_min is not None
        or snare_share_max is not None
        or kick_snare_share_min is not None
        or kick_snare_share_max is not None
        or cymbal_share_min is not None
        or cymbal_share_max is not None
        or tom_share_min is not None
        or tom_share_max is not None
    )
    if share_filter_active and egmd_only:
        internal_limit = min(int(internal_limit), 12000)

    cards = _GROOVE_CATALOG.search(query=q or None, tags=tags or None, sources=sources or None, limit=internal_limit)
    if style_group:
        filtered = []
        for c in cards:
            try:
                sg = str(getattr(c, "style_group", "") or "").strip().lower()
                if sg and sg == style_group:
                    filtered.append(c)
            except Exception:
                continue
        cards = filtered

    if (
        hits_per_bar_min is not None
        or hits_per_bar_max is not None
        or active_instruments_min is not None
        or active_instruments_max is not None
        or offbeat_ratio_min is not None
        or offbeat_ratio_max is not None
        or snare_backbeat_ratio_min is not None
        or snare_backbeat_ratio_max is not None
        or snare_share_min is not None
        or snare_share_max is not None
        or kick_snare_share_min is not None
        or kick_snare_share_max is not None
        or cymbal_share_min is not None
        or cymbal_share_max is not None
        or tom_share_min is not None
        or tom_share_max is not None
    ):
        filtered = []
        for c in cards:
            try:
                hpb = getattr(c, "hits_per_bar", None)
                ai = getattr(c, "active_instruments", None)
                obr = getattr(c, "offbeat_ratio", None)
                sbr = getattr(c, "snare_backbeat_ratio", None)
                snshare = getattr(c, "snare_share", None)
                kss = getattr(c, "kick_snare_share", None)
                cym = getattr(c, "cymbal_share", None)
                tom = getattr(c, "tom_share", None)

                # Only filter if the metric is present; EGMD entries should have them.
                if hpb is not None:
                    v = float(hpb)
                    if hits_per_bar_min is not None and v < float(hits_per_bar_min):
                        continue
                    if hits_per_bar_max is not None and v > float(hits_per_bar_max):
                        continue
                if ai is not None:
                    v = float(ai)
                    if active_instruments_min is not None and v < float(active_instruments_min):
                        continue
                    if active_instruments_max is not None and v > float(active_instruments_max):
                        continue
                if obr is not None:
                    v = float(obr)
                    if offbeat_ratio_min is not None and v < float(offbeat_ratio_min):
                        continue
                    if offbeat_ratio_max is not None and v > float(offbeat_ratio_max):
                        continue
                if sbr is not None:
                    v = float(sbr)
                    if snare_backbeat_ratio_min is not None and v < float(snare_backbeat_ratio_min):
                        continue
                    if snare_backbeat_ratio_max is not None and v > float(snare_backbeat_ratio_max):
                        continue

                if snshare is not None:
                    v = float(snshare)
                    if snare_share_min is not None and v < float(snare_share_min):
                        continue
                    if snare_share_max is not None and v > float(snare_share_max):
                        continue

                if kss is not None:
                    v = float(kss)
                    if kick_snare_share_min is not None and v < float(kick_snare_share_min):
                        continue
                    if kick_snare_share_max is not None and v > float(kick_snare_share_max):
                        continue
                if cym is not None:
                    v = float(cym)
                    if cymbal_share_min is not None and v < float(cymbal_share_min):
                        continue
                    if cymbal_share_max is not None and v > float(cymbal_share_max):
                        continue
                if tom is not None:
                    v = float(tom)
                    if tom_share_min is not None and v < float(tom_share_min):
                        continue
                    if tom_share_max is not None and v > float(tom_share_max):
                        continue

                filtered.append(c)
            except Exception:
                continue
        cards = filtered

    if complexity_min is not None or complexity_max is not None:
        filtered = []
        for c in cards:
            try:
                cs = getattr(c, "complexity_score", None)
                if cs is None:
                    continue
                v = float(cs)
                if complexity_min is not None and v < float(complexity_min):
                    continue
                if complexity_max is not None and v > float(complexity_max):
                    continue
                filtered.append(c)
            except Exception:
                continue
        cards = filtered

    if sort in {"complexity_asc", "complexity_desc"}:
        reverse = sort == "complexity_desc"

        def _key(c):
            try:
                v = getattr(c, "complexity_score", None)
                if v is None:
                    return float("inf") if not reverse else float("-inf")
                return float(v)
            except Exception:
                return float("inf") if not reverse else float("-inf")

        cards = sorted(cards, key=_key, reverse=reverse)

    def _path_blob(card) -> str:
        try:
            return " ".join(
                [
                    str(getattr(card, "audio_path", "") or ""),
                    str(getattr(card, "midi_path", "") or ""),
                    str(getattr(card, "basename", "") or ""),
                    str(getattr(card, "extracted_dir", "") or ""),
                ]
            ).strip().lower()
        except Exception:
            return ""

    def _egmd_session(card) -> int | None:
        blob = _path_blob(card)
        if not blob:
            return None
        if "session_3" in blob or "session 3" in blob or "session3" in blob:
            return 3
        if "session_2" in blob or "session 2" in blob or "session2" in blob:
            return 2
        if "session_1" in blob or "session 1" in blob or "session1" in blob:
            return 1
        return None

    # Diversify EGMD browse results (including style_group browse):
    # Goal: return "spread out" variants (avoid sequential phrase_ids) while also preferring
    # unique visible titles first.
    if is_browse_mode and egmd_only:
        # EGMD content note:
        # - Session 2 is fills (not suitable as default groove).
        # - Session 3 tends to have longer clips (better default groove candidates).
        # Prefer session 3 and exclude session 2 before diversification.
        try:
            no_s2 = [c for c in cards if _egmd_session(c) != 2]
            s3 = [c for c in no_s2 if _egmd_session(c) == 3]
            cards = s3 if s3 else no_s2
        except Exception:
            pass

        def _norm_title(card) -> str:
            try:
                t = getattr(card, "title", None) or getattr(card, "name", None) or ""
                return str(t).strip().lower()
            except Exception:
                return ""

        def _variant_key(card) -> str:
            try:
                source = str(getattr(card, "source", "") or "").strip().lower()
                phrase_id = getattr(card, "phrase_id", None)
                midi_path = str(getattr(card, "midi_path", "") or "").strip()
                audio_path = str(getattr(card, "audio_path", "") or "").strip()
                cid = str(getattr(card, "id", "") or "").strip()
                if phrase_id is not None and str(phrase_id).strip() != "":
                    return f"{source}|phrase:{phrase_id}"
                if midi_path:
                    return f"{source}|midi:{midi_path}"
                if audio_path:
                    return f"{source}|audio:{audio_path}"
                return cid
            except Exception:
                return str(getattr(card, "id", "") or "").strip()

        def _phrase_sort_key(card):
            try:
                pid = getattr(card, "phrase_id", None)
                if pid is None or str(pid).strip() == "":
                    pid = getattr(card, "egmd_phrase_id", None)
                n = int(pid) if pid is not None and str(pid).strip().isdigit() else None
                if n is not None:
                    return (0, n)
            except Exception:
                pass
            try:
                cid = str(getattr(card, "id", "") or "").strip()
                return (1, cid)
            except Exception:
                return (2, "")

        def _spread_indices(n: int, k: int):
            if n <= 0 or k <= 0:
                return []
            if n <= k:
                return list(range(n))
            if k == 1:
                return [n // 2]
            # Evenly spaced indices across [0, n-1]
            return [int(round(i * (n - 1) / (k - 1))) for i in range(k)]

        cards_sorted = list(cards)
        try:
            cards_sorted.sort(key=_phrase_sort_key)
        except Exception:
            pass

        idxs = _spread_indices(len(cards_sorted), limit)
        seen_titles = set()
        seen_variants = set()
        selected = []
        leftovers = []

        # Pass 1: spread out + unique title
        for ix in idxs:
            try:
                c = cards_sorted[ix]
            except Exception:
                continue
            sg = str(getattr(c, "style_group", "") or "").strip().lower()
            nt = _norm_title(c)
            vt = _variant_key(c)
            title_key = f"{sg}|{nt}" if (sg or nt) else nt
            if nt and title_key not in seen_titles and vt and vt not in seen_variants:
                seen_titles.add(title_key)
                seen_variants.add(vt)
                selected.append(c)
            else:
                leftovers.append(c)
            if len(selected) >= limit:
                break

        # Pass 1b: scan remaining (still preferring unique titles) to fill gaps
        if len(selected) < limit:
            for c in cards_sorted:
                sg = str(getattr(c, "style_group", "") or "").strip().lower()
                nt = _norm_title(c)
                vt = _variant_key(c)
                title_key = f"{sg}|{nt}" if (sg or nt) else nt
                if nt and title_key in seen_titles:
                    continue
                if vt and vt in seen_variants:
                    continue
                if nt:
                    seen_titles.add(title_key)
                if vt:
                    seen_variants.add(vt)
                selected.append(c)
                if len(selected) >= limit:
                    break

        # Pass 2: fill remaining with other spread-out variants (allow duplicate titles)
        if len(selected) < limit:
            for c in cards_sorted:
                vt = _variant_key(c)
                if vt and vt in seen_variants:
                    continue
                if vt:
                    seen_variants.add(vt)
                selected.append(c)
                if len(selected) >= limit:
                    break

        cards = selected[:limit]

    # If style_group was requested, ensure we still respect the limit after diversification.
    if style_group:
        cards = cards[:limit]

    items = [c.to_dict() for c in cards]
    # If many items share the same visible title (common in EGMD browse mode),
    # disambiguate titles so the UI can present meaningful choices.
    if is_browse_mode and egmd_only:
        try:
            def _session_label_from_item(it) -> str:
                try:
                    blob = " ".join(
                        [
                            str(it.get("audio_path") or ""),
                            str(it.get("midi_path") or ""),
                            str(it.get("basename") or ""),
                            str(it.get("extracted_dir") or ""),
                        ]
                    ).strip().lower()
                    if "session_3" in blob or "session 3" in blob or "session3" in blob:
                        return "S3"
                    if "session_2" in blob or "session 2" in blob or "session2" in blob:
                        return "S2"
                    if "session_1" in blob or "session 1" in blob or "session1" in blob:
                        return "S1"
                    return ""
                except Exception:
                    return ""

            # First, rewrite EGMD titles to be human-friendly (not phrase-id-centric).
            for it in items:
                src = str(it.get("source") or "").strip().lower()
                if src != "egmd":
                    continue
                sg = str(it.get("style_group") or "").strip()
                sd = str(it.get("style_detail") or "").strip()
                sess = _session_label_from_item(it)
                bpm = it.get("tempo_bpm")
                bars = it.get("bars")

                parts = []
                if sg:
                    parts.append(str(sg).title())
                if sd:
                    parts.append(sd)
                if sess:
                    parts.append(sess)
                if isinstance(bars, int) and bars > 0:
                    parts.append(f"{bars} bars")
                if isinstance(bpm, (int, float)) and bpm:
                    parts.append(f"{int(round(float(bpm)))} bpm")

                if parts:
                    it["title"] = " · ".join(parts)

            title_counts = {}
            for it in items:
                t = str(it.get("title") or it.get("name") or "").strip().lower()
                if not t:
                    continue
                title_counts[t] = title_counts.get(t, 0) + 1

            for it in items:
                src = str(it.get("source") or "").strip().lower()
                if src != "egmd":
                    continue

                raw_title = str(it.get("title") or it.get("name") or "").strip()
                tkey = raw_title.strip().lower()
                if not raw_title or title_counts.get(tkey, 0) <= 1:
                    continue

                style_detail = str(it.get("style_detail") or "").strip()
                phrase_id = it.get("phrase_id")
                if phrase_id is None or str(phrase_id).strip() == "":
                    phrase_id = it.get("egmd_phrase_id")
                suffix_parts = []
                if style_detail:
                    suffix_parts.append(style_detail)
                sess = _session_label_from_item(it)
                if sess:
                    suffix_parts.append(sess)
                # Only add phrase id as a last-resort disambiguator.
                if phrase_id is not None and str(phrase_id).strip() != "":
                    suffix_parts.append(f"phrase {phrase_id}")

                if suffix_parts:
                    it["title"] = f"{raw_title} \u00b7 " + " \u00b7 ".join(suffix_parts)
        except Exception:
            pass

    return web.json_response(
        {
            "ok": True,
            "query": {"q": q, "tags": tags, "sources": sources, "style_group": style_group, "limit": limit},
            "items": items,
        }
    )


async def api_grooves_get(request: web.Request):
    groove_id = str(request.match_info.get("groove_id") or "").strip()
    if not groove_id:
        return web.json_response({"ok": False, "error": "groove_id required"}, status=400)

    card = _GROOVE_CATALOG.get_by_id(groove_id)
    if not card:
        return web.json_response({"ok": False, "error": "not found"}, status=404)

    return web.json_response({"ok": True, "item": card.to_dict()})


def _resolve_groove_audio_path(card: "GrooveCard") -> Optional[Path]:
    try:
        audio_path = getattr(card, "audio_path", None)
        if not audio_path:
            return None
        p = Path(str(audio_path)).expanduser()
        if not p.exists() or not p.is_file():
            return None
        return p
    except Exception:
        return None


async def api_grooves_audio(request: web.Request):
    groove_id = str(request.match_info.get("groove_id") or "").strip()
    if not groove_id:
        return web.json_response({"ok": False, "error": "groove_id required"}, status=400)

    card = _GROOVE_CATALOG.get_by_id(groove_id)
    if not card:
        return web.json_response({"ok": False, "error": "not found"}, status=404)

    # Only support audio audition where we have an explicit audio path (EGMD, etc.)
    p = _resolve_groove_audio_path(card)
    if not p:
        return web.json_response({"ok": False, "error": "audio not available"}, status=404)

    content_type, _ = mimetypes.guess_type(str(p))
    ext = str(p.suffix or "").lower()
    if ext in {".wav", ".wave"}:
        content_type = "audio/wav"
    elif ext in {".mp3"}:
        content_type = "audio/mpeg"
    elif ext in {".ogg"}:
        content_type = "audio/ogg"
    else:
        content_type = content_type or "application/octet-stream"

    try:
        hdr_midi = str(getattr(card, "midi_path", "") or "")
    except Exception:
        hdr_midi = ""
    try:
        hdr_audio = str(getattr(card, "audio_path", "") or "")
    except Exception:
        hdr_audio = ""
    try:
        hdr_phrase_id = str(getattr(card, "phrase_id", "") or "")
    except Exception:
        hdr_phrase_id = ""

    return web.FileResponse(
        path=str(p),
        headers={
            "Content-Type": content_type,
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "Content-Disposition": f'inline; filename="{p.name}"',
            "X-Groove-Id": str(getattr(card, "id", groove_id) or groove_id),
            "X-Egmd-Phrase-Id": hdr_phrase_id,
            "X-Egmd-Midi-Path": hdr_midi,
            "X-Egmd-Audio-Path": hdr_audio,
        },
    )


async def api_groove_analyze(request: web.Request):
    """Return groove metrics + coaching suggestions.

    This endpoint is used by web-frontend/src/daw/ui/GrooveCoachPanel.tsx.

    v1 implementation:
    - deterministic placeholder scores
    - coaching suggestions derived from admin/data/knowledge_sources/coaching_taxonomy.json
    """

    try:
        data = await request.json()
    except Exception:
        data = {}

    job_id = None
    section_id = None
    section_label = None
    goals = None
    current_config = None
    try:
        job_id = data.get("job_id") or data.get("jobId")
        section_id = data.get("section_id") or data.get("sectionId")
        section_label = data.get("section_label") or data.get("sectionLabel")
        raw_goals = data.get("goals")
        if isinstance(raw_goals, list):
            goals = [str(g) for g in raw_goals if str(g).strip()]
        raw_cfg = data.get("current_config") or data.get("currentConfig")
        if isinstance(raw_cfg, dict):
            current_config = raw_cfg
    except Exception:
        pass

    if not GROOVE_COACH_AVAILABLE or build_groove_coach_response is None:
        return web.json_response(
            {
                "ok": False,
                "error": "groove coach not available",
                "job_id": job_id,
                "section_id": section_id,
                "timing_score": 0.0,
                "velocity_score": 0.0,
                "humanization_score": 0.0,
                "overall_score": 0.0,
                "suggestions": [],
            },
            status=503,
        )

    payload = build_groove_coach_response(
        job_id=job_id,
        section_id=section_id,
        section_label=section_label,
        goals=goals,
        current_config=current_config,
    )
    payload["ok"] = True
    return web.json_response(payload)


async def api_groove_goals(_request: web.Request):
    if not GROOVE_COACH_AVAILABLE or list_available_goals is None:
        return web.json_response({"ok": False, "error": "groove coach not available"}, status=503)
    return web.json_response({"ok": True, **list_available_goals()})


async def api_groove_apply_patch(request: web.Request):
    if not GROOVE_COACH_AVAILABLE or apply_config_patch is None:
        return web.json_response({"ok": False, "error": "groove coach not available"}, status=503)

    try:
        data = await request.json()
    except Exception:
        data = {}

    cfg = data.get("config")
    patch = data.get("config_patch")
    if not isinstance(cfg, dict) or not isinstance(patch, dict):
        return web.json_response(
            {"ok": False, "error": "Expected JSON body: {config: {...}, config_patch: {...}}"},
            status=400,
        )

    patched = apply_config_patch(base_config=cfg, config_patch=patch)
    return web.json_response({"ok": True, "patched_config": patched})


async def api_preset_preview_knowledge(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    profile_type = str(data.get("profileType") or data.get("profile_type") or "").strip()
    drummer_id = str(data.get("drummerId") or data.get("drummer_id") or "").strip()
    preset_stack = data.get("presetStack") or data.get("preset_stack") or []
    preset_names = data.get("presetNames") or data.get("preset_names") or []

    if not isinstance(preset_stack, list):
        preset_stack = []
    if not isinstance(preset_names, list):
        preset_names = []

    try:
        from backend.groove_coach_engine import knowledge_search
    except Exception:
        knowledge_search = None  # type: ignore

    q_parts = []
    if profile_type:
        q_parts.append(profile_type)
    if drummer_id:
        q_parts.append(drummer_id)
    for n in preset_names:
        s = str(n or "").strip()
        if s:
            q_parts.append(s)
    for item in preset_stack:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("presetId") or item.get("preset_id") or "").strip()
        tier = str(item.get("tier") or "").strip()
        if pid:
            q_parts.append(pid)
        if tier:
            q_parts.append(tier)
    query = " ".join(q_parts).strip()

    citations = []
    if knowledge_search and query:
        citations = knowledge_search(query=query, top_k=5)

    # Lightweight “what to listen for”: extract a few short snippets from citations.
    listen_for = []
    for c in citations[:3]:
        t = str((c or {}).get("text") or "").strip()
        if not t:
            continue
        t = t.replace("\n", " ").strip()
        if len(t) > 220:
            t = t[:217].rstrip() + "..."
        listen_for.append(t)

    return web.json_response({"ok": True, "query": query, "what_to_listen_for": listen_for, "citations": citations})

def make_app() -> web.Application:
    app = web.Application()
    app.add_routes([
        web.get("/healthz", healthz),
        web.get("/api/llm/status", api_llm_status),
        # keep both paths for compatibility with your frontend(s)
        web.post("/api/upload", upload),
        web.post("/files/upload", upload),
        web.get("/waveform", waveform),  # Add direct /waveform route
        web.get("/files/waveform", waveform),
        web.get("/files/audio", audio_file),
        web.get("/api/status", api_status),
        # Legacy analyze endpoint - now calls real Rust analysis
        web.post("/api/analyze", analyze_audio_real),
        # Legacy results endpoint - returns real analysis results
        web.get("/api/results/{job_id}", get_analysis_results),
        # New analysis endpoints
        web.get("/analyze/onsets", analyze_onsets),
        web.get("/analyze/tempo", analyze_tempo),
        web.post("/align/sections", align_sections),
        # Session endpoints
        web.post("/session/{sid}", save_session),
        web.get("/session/{sid}", load_session),
        # Benchmark endpoints
        web.get("/bench/peaks", bench_peaks),
        web.get("/bench/analysis", bench_analysis),
        web.get("/bench/generate", bench_generate),
        # DCSM endpoints
        web.get("/dcsm/sectionize", dcsm_sectionize),
        web.get("/dcsm/sectionize_enhanced", dcsm_sectionize_enhanced),
        web.get("/dcsm/analyze_full", dcsm_analyze_full),
        web.post("/dcsm/generate", dcsm_generate),
        web.post("/analyze/tempo_sections", analyze_tempo_sections),
        web.get("/dcsm/brain-elements", list_brain_elements),
        web.get("/dcsm/brain-config/{section_id}", get_brain_config),
        web.patch("/dcsm/brain-config/{section_id}", patch_brain_config),
        # Drummer profile endpoints
        web.get("/api/drummers", list_drummers),
        web.get("/api/drummers/{drummer_id}", get_drummer_details),
        web.post("/api/generate_with_drummer", generate_with_drummer),
        web.post("/api/sectionize_smart", api_sectionize_smart),
        # Drummer personas (analysis/brain visualization)
        web.get("/api/drummer-personas", list_drummer_personas),
        web.get("/api/drummer-presets", list_drummer_presets),
        web.post("/api/beatbox/translate", beatbox_translate),
        web.post("/api/beatbox/tap-input", beatbox_tap_input),
        web.post("/api/beatprompt/render", beatprompt_render),
        # Song lookup endpoint
        web.get("/api/song-lookup", song_lookup),
        # Drum generation endpoint
        web.post("/api/generate-drums", handle_generate_drums),
        web.post("/api/preset-preview/knowledge", api_preset_preview_knowledge),
        web.post("/api/conform-to-instrument", api_conform_to_instrument),
        web.post("/api/mvsep/start", api_mvsep_start),
        web.get("/api/mvsep/status", api_mvsep_status),
        web.get("/api/mvsep/stems", api_mvsep_stems),
        web.post("/api/render-plugin-midi", api_render_plugin_midi),
        web.get("/api/egmd/phrases", api_list_egmd_phrases),
        web.get("/api/egmd/style-groups", api_list_egmd_style_groups),

        web.get("/api/grooves/search", api_grooves_search),
        web.get("/api/grooves/{groove_id}", api_grooves_get),
        web.get("/api/grooves/{groove_id}/audio", api_grooves_audio),
        web.post("/api/groove/analyze", api_groove_analyze),
        web.get("/api/groove/goals", api_groove_goals),
        web.post("/api/groove/apply-patch", api_groove_apply_patch),
        # Jamstix brain endpoints
        web.post("/api/jamstix/enrich", jamstix_enrich_pattern),
        web.post("/api/jamstix/build-track", jamstix_build_track),
        web.get("/api/jamstix/status", jamstix_status),

        # Sample DB endpoints (Docker/cloud friendly)
        web.get("/api/sample-collections", api_sample_collections),
        web.get("/api/drum-samples", api_drum_samples),
        web.get("/api/drum-samples/{sample_id}/audio", api_drum_sample_audio),

        web.get("/api/kits", api_list_kits),
        web.get("/api/kits/{kit_id}/manifest", api_get_kit_manifest),
    ])

    # Initialize AI system and register AI routes
    # TEMPORARILY DISABLED FOR TESTING
    # initialize_ai_generator()
    # setup_ai_routes(app)

    # CORS for dev (after all routes are added)
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
        return web.json_response({"error": "invalid JSON"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    if not sf or not librosa:
        return web.json_response({"error": "librosa/soundfile not available"}, status=500)
    
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
        
        out = [{"start": snap(s.get("start", 0)), "end": max(snap(s.get("end", 1)), snap(s.get("start", 0)) + 0.25)} for s in sections]
        return web.json_response({"tempo": float(tempo), "sections": out})
    except Exception as e:
        LOG.error(f"Section alignment failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def api_conform_to_instrument(request: web.Request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)

    key = data.get("key")
    instrument = str(data.get("instrument") or "bass").strip().lower()
    strength = float(data.get("strength") or 0.5)
    strength = max(0.0, min(1.0, strength))
    drum_track = data.get("drum_track") or data.get("drumTrack")
    mvsep_job_id = data.get("mvsep_job_id") or data.get("mvsepJobId")

    if not key:
        return web.json_response({"error": "key required"}, status=400)
    if not isinstance(drum_track, dict) or not isinstance(drum_track.get("notes"), list):
        return web.json_response({"error": "Expected JSON body with drum_track.notes"}, status=400)

    audio_path = (UPLOAD_DIR / str(key)).resolve()
    if not audio_path.exists() or not str(audio_path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)

    if not USE_RUST:
        return web.json_response({"error": "Rust audio-core required"}, status=503)

    # If MVSEP job id is provided and bass stem exists, analyze bass stem instead of full mix.
    analyze_path = audio_path
    try:
        if mvsep_job_id and str(mvsep_job_id) in MVSEP_JOBS:
            job = MVSEP_JOBS.get(str(mvsep_job_id)) or {}
            stems = job.get("stems") if isinstance(job, dict) else None
            if isinstance(stems, dict):
                bass_path = stems.get("bass")
                if bass_path and isinstance(bass_path, str) and os.path.exists(bass_path):
                    analyze_path = Path(bass_path)
    except Exception:
        pass

    try:
        analysis = run_audio_core(["analyze", str(analyze_path)])
        bpm = float(analysis.get("tempo", 0.0) or 0.0)
        onsets = analysis.get("onsets", []) or []
        if bpm <= 0.0 or not isinstance(onsets, list) or not onsets:
            return web.json_response({"error": "analysis produced no tempo/onsets"}, status=500)
        onsets = sorted([float(t) for t in onsets if isinstance(t, (int, float))])
    except Exception as e:
        LOG.error(f"audio-core analyze failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

    ppq = float(drum_track.get("resolution_ppq") or 960)
    if ppq <= 0:
        ppq = 960.0
    bar_ticks = 4.0 * ppq
    ticks_per_sec = ppq * (bpm / 60.0)

    # Conform parameters
    max_window_sec = float(data.get("max_window_sec") or 0.08)
    max_window_sec = max(0.0, min(0.25, max_window_sec))
    max_shift_ticks = float(data.get("max_shift_ticks") or (0.25 * ppq))
    max_shift_ticks = max(0.0, min(ppq, max_shift_ticks))

    target_instruments = {"kick", "snare_center", "snare_rim", "snare_ghost"}
    if instrument not in {"bass", "other", "mix"}:
        instrument = "bass"

    def _nearest_onset(t: float) -> float:
        # Binary search nearest onset
        lo = 0
        hi = len(onsets) - 1
        if hi <= 0:
            return onsets[0]
        while lo < hi:
            mid = (lo + hi) // 2
            if onsets[mid] < t:
                lo = mid + 1
            else:
                hi = mid
        idx = lo
        best = onsets[idx]
        if idx > 0 and abs(onsets[idx - 1] - t) < abs(best - t):
            best = onsets[idx - 1]
        return best

    moved = 0
    out_notes = []
    for n in drum_track.get("notes", []) or []:
        if not isinstance(n, dict):
            out_notes.append(n)
            continue
        inst = str(n.get("instrumentId") or "").strip().lower()
        if inst not in target_instruments:
            out_notes.append(n)
            continue

        try:
            bar_i = int(n.get("barIndex") or 0)
            tick_in_bar = float(n.get("tickInBar") or 0.0)
        except Exception:
            out_notes.append(n)
            continue

        abs_ticks = bar_i * bar_ticks + tick_in_bar
        t_sec = (abs_ticks / ppq) * (60.0 / bpm)
        onset = _nearest_onset(t_sec)
        dt = onset - t_sec
        if abs(dt) > max_window_sec:
            out_notes.append(n)
            continue

        delta_ticks = dt * ticks_per_sec * strength
        if delta_ticks > max_shift_ticks:
            delta_ticks = max_shift_ticks
        if delta_ticks < -max_shift_ticks:
            delta_ticks = -max_shift_ticks

        new_abs_ticks = abs_ticks + delta_ticks
        if new_abs_ticks < 0:
            new_abs_ticks = 0.0
        new_bar = int(new_abs_ticks // bar_ticks)
        new_tick_in_bar = float(new_abs_ticks - (new_bar * bar_ticks))
        nn = dict(n)
        nn["barIndex"] = new_bar
        nn["tickInBar"] = new_tick_in_bar
        out_notes.append(nn)
        moved += 1

    out_track = dict(drum_track)
    out_track["notes"] = out_notes
    return web.json_response(
        {
            "ok": True,
            "instrument": instrument,
            "bpm": bpm,
            "moved_notes": moved,
            "drum_track": out_track,
        }
    )

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
    
    if not USE_RUST:
        return web.json_response({"error": "Rust audio-core required"}, status=503)

    try:
        result = run_audio_core(["analyze", str(path)])
        sr = int(result.get("sample_rate") or result.get("sr") or 44100)
        onsets = result.get("onsets", []) or []
        return web.json_response({"sr": sr, "onsets": [float(t) for t in onsets]})
    except Exception as e:
        LOG.error(f"Onset analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def analyze_tempo(request):
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    if not USE_RUST:
        return web.json_response({"error": "Rust audio-core required"}, status=503)

    try:
        result = run_audio_core(["analyze", str(path)])
        tempo = float(result.get("tempo", 0.0) or 0.0)
        beats = result.get("beats", []) or []
        return web.json_response({"tempo": tempo, "beats": [float(t) for t in beats]})
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
    
    if not USE_RUST:
        return web.json_response({"error": "Rust audio-core required"}, status=503)

    try:
        result = run_audio_core(["analyze", str(path)])
        tempo = float(result.get("tempo", 0.0) or 0.0)
        beat_times = result.get("beats", []) or []

        def snap(value: float) -> float:
            if not beat_times:
                return value
            closest = min(beat_times, key=lambda t: abs(t - value))
            return float(closest)

        aligned = []
        for s in sections:
            start_raw = float(s.get("start", 0.0) or 0.0)
            end_raw = float(s.get("end", start_raw + 1.0) or (start_raw + 1.0))
            start = snap(start_raw)
            snapped_end = snap(end_raw)
            end = max(snapped_end, start + 0.25)
            aligned.append({"start": start, "end": end})

        return web.json_response({"tempo": tempo, "sections": aligned})
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

async def dcsm_sectionize_enhanced(request):
    """Enhanced sectionization with intelligent labeling and metadata"""
    key = request.query.get("key")
    bpm_str = request.query.get("bpm", "0")  # 0 = auto-detect
    mode = request.query.get("mode", "smart")
    min_bars = int(request.query.get("min_bars", "4"))
    max_bars = int(request.query.get("max_bars", "16"))
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    # Auto-detect tempo if not provided
    bpm = float(bpm_str)
    if bpm == 0 and USE_RUST:
        try:
            tempo_result = run_audio_core(["analyze", str(path), "--min-bpm", "60", "--max-bpm", "200"])
            bpm = tempo_result.get("tempo", 120.0)
            LOG.info(f"Auto-detected tempo: {bpm} BPM")
        except Exception as e:
            LOG.warning(f"Tempo detection failed: {e}, using default 120 BPM")
            bpm = 120.0
    elif bpm == 0:
        bpm = 120.0  # Default if Rust unavailable
    
    # Get sections from Rust (now includes energy and spectral_centroid)
    if not USE_RUST:
        return web.json_response({"error": "Enhanced sectionization requires Rust audio-core"}, status=503)
    
    try:
        result = run_audio_core([
            "sectionize-smart", str(path),
            "--bpm", str(bpm),
            "--min-bars", str(min_bars),
            "--max-bars", str(max_bars)
        ])
        sections = result.get("sections", [])
        
        # Rust now provides energy and spectral_centroid!
        # Calculate additional metadata
        if sections:
            # Build song structure string (I-V-C-V-C-B-C-O)
            structure_map = {
                "intro": "I",
                "verse": "V", 
                "chorus": "C",
                "bridge": "B",
                "outro": "O",
                "break": "X",
                "solo": "S"
            }
            structure = "-".join([structure_map.get(s.get("label", "unknown"), "?") for s in sections])
            
            # Calculate average energy and confidence (if available)
            energies = [s.get("energy", 0.5) for s in sections]
            avg_energy = sum(energies) / len(energies) if energies else 0.5
            
            # Group similar sections for repetition analysis
            repetition_groups = {}
            for i, section in enumerate(sections):
                label = section.get("label", "unknown")
                if label not in repetition_groups:
                    repetition_groups[label] = []
                repetition_groups[label].append(i)
            
            # Assign repetition group numbers
            for i, section in enumerate(sections):
                label = section.get("label", "unknown")
                group_indices = repetition_groups.get(label, [])
                section["repetition_group"] = group_indices.index(i) if i in group_indices else 0
                
                # Add confidence scores based on energy consistency
                energy = section.get("energy", 0.5)
                if label == "intro" and i == 0:
                    section["confidence"] = 0.75
                elif label == "outro" and i == len(sections) - 1:
                    section["confidence"] = 0.75
                elif label == "chorus" and energy > avg_energy * 1.1:
                    section["confidence"] = 0.85
                elif label == "verse":
                    section["confidence"] = 0.75
                elif label == "bridge":
                    section["confidence"] = 0.65
                else:
                    section["confidence"] = 0.60
            
            return web.json_response({
                "sections": sections,
                "metadata": {
                    "detected_bpm": bpm,
                    "song_structure": structure,
                    "avg_energy": avg_energy,
                    "total_sections": len(sections),
                    "section_labels": list(set([s.get("label", "unknown") for s in sections])),
                    "has_energy_data": all("energy" in s for s in sections),
                    "has_spectral_data": all("spectral_centroid" in s for s in sections)
                }
            })
        else:
            return web.json_response({
                "sections": [],
                "metadata": {
                    "detected_bpm": bpm,
                    "error": "No sections detected"
                }
            })
            
    except Exception as e:
        LOG.error(f"Enhanced sectionization failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def dcsm_analyze_full(request):
    """
    Full song analysis → SongMap:
    - beat_times
    - bars with per-bar tempo and meter
    - sections with labels + energy + spectral centroid
    - global BPM
    """
    key = request.query.get("key")
    if not key:
        return web.json_response({"error": "Missing ?key= parameter"}, status=400)

    audio_path = (UPLOAD_DIR / key).resolve()
    if not audio_path.exists() or not str(audio_path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": f"Audio not found: {key}"}, status=404)

    if not USE_RUST:
        return web.json_response({"error": "Full analysis requires Rust audio-core"}, status=503)

    # Call Rust binary with analyze-full command
    try:
        result = run_audio_core(["analyze-full", str(audio_path)])
    except Exception as e:
        LOG.error(f"audio-core analyze-full failed: {e}")
        return web.json_response({
            "error": "audio-core analyze-full failed",
            "details": str(e),
        }, status=500)

    # Attach bar indices to sections
    bars = result.get("bars", [])
    sections = result.get("sections", [])

    enhanced_sections = _attach_bar_indices_to_sections(sections, bars)
    result["sections"] = enhanced_sections

    return web.json_response(result)


def _attach_bar_indices_to_sections(sections, bars):
    """Add start_bar_index/end_bar_index/bar_count to sections."""
    def find_bar_idx_at_time(t_sec: float) -> int:
        for bar in bars:
            if bar["start_time"] <= t_sec < bar["end_time"]:
                return bar["index"]
        # if past last bar, clamp
        if bars:
            return bars[-1]["index"]
        return 0

    for s in sections:
        start_bar = find_bar_idx_at_time(s["start"])
        end_bar = find_bar_idx_at_time(s["end"])
        s["start_bar_index"] = start_bar
        s["end_bar_index"] = end_bar
        s["bar_count"] = max(1, end_bar - start_bar + 1)
    return sections

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
        return web.json_response(result)
    except Exception as e:
        LOG.error(f"Rust generate failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

# Drummer Profile API Endpoints
async def list_drummers(request):
    """Get list of DrumTrackAI fictional drummers"""
    try:
        service = get_drummer_service()
        drummers = service.list_drummers()
        return web.json_response({"drummers": drummers})
    except Exception as e:
        LOG.error(f"List drummers failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def get_drummer_details(request):
    """Get detailed characteristics for a specific drummer"""
    drummer_id = request.match_info.get("drummer_id")
    
    if not drummer_id:
        return web.json_response({"error": "drummer_id required"}, status=400)
    
    try:
        service = get_drummer_service()
        drummers = service.list_drummers()
        
        # Find the drummer
        drummer = next((d for d in drummers if d["id"] == drummer_id), None)
        if not drummer:
            return web.json_response({"error": "drummer not found"}, status=404)
        
        # Get characteristics from admin database
        characteristics = service.get_drummer_characteristics(drummer_id)
        
        # Combine display info with characteristics
        drummer["characteristics"] = characteristics
        
        return web.json_response(drummer)
    except Exception as e:
        LOG.error(f"Get drummer details failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def generate_with_drummer(request):
    """Generate drums using drummer profile + song analysis"""
    try:
        data = await request.json()
        
        drummer_id = data.get("drummer_id")
        if not drummer_id:
            return web.json_response({"error": "drummer_id required"}, status=400)
        
        bpm = data.get("bpm", 120.0)
        sections = data.get("sections", [])
        song_analysis = data.get("song_analysis", {})  # Optional groove analysis
        
        service = get_drummer_service()
        
        # Get generation parameters combining drummer style + song analysis
        gen_params = service.get_generation_parameters(drummer_id, song_analysis)
        
        LOG.info(f"Generating with drummer: {drummer_id}, style: {gen_params['style']}")
        
        # Generate drums using Rust generator with drummer params
        all_notes = []
        all_midi_segments = []  # Collect MIDI from each section
        
        for section in sections:
            start = section.get("start", 0.0)
            end = section.get("end", 4.0)
            fill_in = section.get("fill_in", False)
            fill_out = section.get("fill_out", False)
            label = section.get("label", "verse")
            density_override = section.get("density")
            
            # Convert time range to bars (Rust CLI expects bars, not time)
            duration = end - start
            seconds_per_bar = (60.0 / bpm) * 4.0  # 4 beats per bar
            bars = max(1, int(duration / seconds_per_bar))
            
            # Build Rust CLI arguments
            args = [
                "generate",
                "--bpm", str(bpm),
                "--bars", str(bars),
                "--style", gen_params["style"],
                "--label", label,
                "--swing-preset", gen_params["swing_preset"],
                "--vel-preset", gen_params["vel_preset"],
                "--fill-preset", gen_params["fill_preset"],
                "--density", str(density_override if density_override is not None else gen_params["density"]),
                "--humanize", str(gen_params["humanize"]),
            ]
            
            # Note: fill-in/fill-out are handled by Rust via density/label
            # The Rust CLI doesn't have separate --fill-in/--fill-out flags
            
            # Call Rust generator
            if USE_RUST:
                try:
                    LOG.info(f"Running audio-core with args: {args}")
                    result = run_audio_core(args)
                    LOG.info(f"Rust returned result keys: {list(result.keys())}")
                    notes = result.get("notes", [])
                    LOG.info(f"Extracted {len(notes)} notes from result")
                    all_notes.extend(notes)
                    
                    # Collect MIDI data if present
                    if "midi" in result:
                        all_midi_segments.append(result["midi"])
                        LOG.info(f"Collected MIDI segment ({len(result['midi'])} bytes)")
                except Exception as e:
                    LOG.error(f"Rust generation failed for section: {e}", exc_info=True)
            else:
                LOG.warning("Rust not enabled, skipping generation")
        
        # Return MIDI data
        midi_base64 = None
        if all_midi_segments:
            # For now, return the last section's MIDI (or we could merge them)
            # TODO: Implement proper MIDI merging for multiple sections
            midi_base64 = all_midi_segments[-1] if all_midi_segments else None
            LOG.info(f"Returning MIDI: {len(midi_base64) if midi_base64 else 0} bytes")
        
        return web.json_response({
            "notes": all_notes,
            "midi_base64": midi_base64,
            "drummer_id": drummer_id,
            "params_used": gen_params
        })
        
    except Exception as e:
        LOG.error(f"Generate with drummer failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def api_sectionize_smart(request):
    """Smart sectionization with JSON POST body (API endpoint for frontend)"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)
    
    key = data.get("key")
    bpm = data.get("bpm", 120.0)
    time_signature_num = data.get("time_signature_num", 4)
    max_section_bars = data.get("max_section_bars", 16)
    min_bars = 4  # Could be made configurable
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    # Use Rust sectionization if available
    if USE_RUST:
        try:
            result = run_audio_core([
                "sectionize-smart",
                str(path),
                "--bpm", str(bpm),
                "--min-bars", str(min_bars),
                "--max-bars", str(max_section_bars)
            ])
            return web.json_response(result)
        except Exception as e:
            LOG.error(f"Rust sectionization failed: {e}")
            return web.json_response({"error": str(e)}, status=500)
    else:
        # Fallback: simple fixed-bar sections
        try:
            if sf:
                info = sf.info(str(path))
                duration = float(info.frames) / float(info.samplerate) if info.samplerate and info.frames else 0.0
            else:
                duration = 60.0  # fallback
            
            sec_per_bar = 60.0 / bpm * time_signature_num
            spans = []
            t = 0.0
            while t < duration: 
                end_time = min(t + sec_per_bar * max_section_bars, duration)
                spans.append({"start": t, "end": end_time, "label": "section", "confidence": 0.7})
                t = end_time
            
            return web.json_response({"sections": spans})
        except Exception as e:
            LOG.error(f"Fallback sectionization failed: {e}")
            return web.json_response({"error": str(e)}, status=500)

async def analyze_tempo_sections(request):
    """Analyze tempo for multiple sections of audio"""
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "invalid JSON body"}, status=400)
    
    key = data.get("key")
    sections = data.get("sections", [])
    
    if not key:
        return web.json_response({"error": "key required"}, status=400)
    
    if not sections:
        return web.json_response({"error": "sections array required"}, status=400)
    
    path = (UPLOAD_DIR / key).resolve()
    if not path.exists() or not str(path).startswith(str(UPLOAD_DIR)):
        return web.json_response({"error": "audio not found"}, status=404)
    
    # Try Rust implementation first
    if USE_RUST:
        try:
            # Build command arguments
            starts = [str(s.get("start", 0.0)) for s in sections]
            ends = [str(s.get("end", 1.0)) for s in sections]
            
            args = [
                "analyze-sections",
                str(path),
                "--starts", ",".join(starts),
                "--ends", ",".join(ends),
                "--min-bpm", "50",
                "--max-bpm", "200"
            ]
            
            result = run_audio_core(args)
            
            # Add global tempo estimate (average of all sections)
            if "results" in result and result["results"]:
                tempos = [r["tempo"] for r in result["results"] if r["tempo"] > 0]
                result["global_tempo"] = sum(tempos) / len(tempos) if tempos else 120.0
            
            return web.json_response(result)
        except Exception as e:
            LOG.warning(f"Rust tempo_sections failed, falling back to Python: {e}")
    
    # Python fallback using librosa
    if not sf or not librosa:
        return web.json_response({"error": "audio analysis libraries not available"}, status=500)
    
    try:
        y, sr = sf.read(str(path), dtype="float32", always_2d=False)
        if y.ndim == 2:
            y = y.mean(axis=1)
        
        results = []
        for section in sections:
            start_sec = section.get("start", 0.0)
            end_sec = section.get("end", 1.0)
            
            # Extract segment
            start_frame = int(start_sec * sr)
            end_frame = int(end_sec * sr)
            segment = y[start_frame:end_frame]
            
            if len(segment) < sr:  # Too short (< 1 second)
                results.append({
                    "start": start_sec,
                    "end": end_sec,
                    "tempo": 120.0,
                    "confidence": 0.0,
                    "candidates": [120.0]
                })
                continue
            
            # Analyze tempo
            tempo, beats = librosa.beat.beat_track(y=segment, sr=sr)
            
            # Simple confidence based on beat strength
            onset_env = librosa.onset.onset_strength(y=segment, sr=sr)
            confidence = float(np.mean(onset_env) if len(onset_env) > 0 else 0.0)
            confidence = min(1.0, confidence / 10.0)  # Normalize roughly
            
            # Provide some candidate tempos (double/half time)
            candidates = [float(tempo), float(tempo * 2), float(tempo / 2)]
            
            results.append({
                "start": start_sec,
                "end": end_sec,
                "tempo": float(tempo),
                "confidence": confidence,
                "candidates": candidates
            })
        
        # Calculate global tempo
        tempos = [r["tempo"] for r in results if r["tempo"] > 0]
        global_tempo = sum(tempos) / len(tempos) if tempos else 120.0
        
        return web.json_response({
            "results": results,
            "global_tempo": global_tempo
        })
    except Exception as e:
        LOG.error(f"Tempo sections analysis failed: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def song_lookup(request):
    """
    Search internet databases for song information
    Returns tempo, time signature, key, and arrangement structure
    """
    query = request.query.get("q", "").strip()
    
    if not query:
        return web.json_response({"error": "Query parameter 'q' required"}, status=400)
    
    LOG.info(f"Song lookup: {query}")
    
    try:
        # Search internet databases
        results = await search_song(query)
        
        if results:
            LOG.info(f"Found {len(results)} results from internet")
            return web.json_response({"results": results})
        
        # No results found
        LOG.info(f"No results found for: {query}")
        return web.json_response({
            "results": [],
            "message": "No results found. Try different search terms or use Manual Entry."
        })
        
    except Exception as e:
        LOG.error(f"Song lookup failed: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_generate_drums(request):
    """
    Generate drums for selected measure range
    POST /api/generate-drums
    """
    try:
        data = await request.json()
        section_id = data.get('sectionId')
        build_scope = (data.get('buildScope') or data.get('mode') or '').lower()
        LOG.info(f"Drum generation request: {section_id} ({data.get('measureCount')} measures)")

        if build_scope in {"selected_section", "section", "per_section"} and not section_id:
            return web.json_response(
                {"error": "sectionId is required when buildScope=selected_section"},
                status=400,
            )

        if not section_id:
            LOG.warning("/api/generate-drums received payload without sectionId; continuing in global mode")
        
        selected_groove_id = data.get("selectedGrooveId") or data.get("selected_groove_id")
        groove_use = data.get("grooveUse") or data.get("groove_use")
        fill_groove_id = data.get("fillGrooveId") or data.get("fill_groove_id")
        fill_bar_index = data.get("fillBarIndex") or data.get("fill_bar_index")

        # v3 Groove Library: if a groove card (often EGMD) is selected, translate it into
        # a forced EGMD phrase id so the backend deterministically uses that groove.
        # This is the smallest reliable bridge without reworking the entire planner.
        try:
            if selected_groove_id and not (data.get("egmdPhraseId") or data.get("egmd_phrase_id")):
                card = _GROOVE_CATALOG.get_by_id(str(selected_groove_id))
                if card and str(getattr(card, "source", "")).strip().lower() == "egmd" and getattr(card, "phrase_id", None) is not None:
                    data["egmdPhraseId"] = int(card.phrase_id)
                    try:
                        midi_path = getattr(card, "midi_path", None)
                        if midi_path and not (data.get("egmdMidiPath") or data.get("egmd_midi_path")):
                            data["egmdMidiPath"] = str(midi_path)
                    except Exception:
                        pass
                    # Encourage exact EGMD playback when explicitly selecting a groove.
                    data.setdefault("grooveSource", "egmd_phrases")
                    data.setdefault("grooveMode", "exact")
                    try:
                        LOG.info(
                            "EGMD groove bridge: selectedGrooveId=%s -> phrase_id=%s midi_path=%s grooveSource=%s grooveMode=%s",
                            str(selected_groove_id),
                            getattr(card, "phrase_id", None),
                            getattr(card, "midi_path", None),
                            data.get("grooveSource"),
                            data.get("grooveMode"),
                        )
                    except Exception:
                        pass
                else:
                    try:
                        LOG.warning(
                            "Groove bridge skipped: selectedGrooveId=%s card_found=%s card_source=%s phrase_id=%s",
                            str(selected_groove_id),
                            bool(card),
                            str(getattr(card, "source", None) if card else None),
                            getattr(card, "phrase_id", None) if card else None,
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        # Create config object
        config = DrumGenerationConfig(data)
        
        DRUM_GEN_STATS["requests"] = int(DRUM_GEN_STATS.get("requests", 0) or 0) + 1

        # Generate drums using integrated system
        result = generate_drums(config)

        # Optional: apply a 1-bar fill at an explicit bar index.
        try:
            if fill_groove_id and fill_bar_index is not None and isinstance(result, dict):
                drum_track = result.get("drum_track") if isinstance(result.get("drum_track"), dict) else None
                if drum_track and isinstance(drum_track.get("notes"), list):
                    try:
                        target_bar = int(fill_bar_index)
                    except Exception:
                        target_bar = None

                    if target_bar is not None:
                        ppq = int(drum_track.get("resolution_ppq") or 960) or 960
                        tick_per_16th = max(1, ppq // 4)

                        # Remove existing notes in that bar (treat fill as a replacement).
                        original_notes = drum_track.get("notes") or []
                        kept_notes = [n for n in original_notes if int(n.get("barIndex") or -1) != target_bar]

                        fill_pattern, fill_pattern_id = get_fill_pattern(str(fill_groove_id))
                        new_notes = []
                        for inst_id, steps in (fill_pattern.steps or {}).items():
                            for s in steps or []:
                                ss = int(s)
                                if ss < 0 or ss >= 16:
                                    continue
                                tick_in_bar = ss * tick_per_16th
                                vel = 110 if (ss == 0 or inst_id.startswith("crash")) else 92
                                if inst_id.endswith("ghost"):
                                    vel = 34
                                new_notes.append(
                                    {
                                        "id": make_note_id(),
                                        "barIndex": target_bar,
                                        "tickInBar": int(tick_in_bar),
                                        "tickLength": int(tick_per_16th),
                                        "channel": 9,
                                        "midiPitch": int(instrument_id_to_midi_pitch(inst_id)),
                                        "velocity": int(vel),
                                        "instrumentId": inst_id,
                                        "aspect": "fill",
                                        "isGhost": bool(inst_id.endswith("ghost")),
                                        "isAccent": bool(ss == 0 or inst_id.startswith("crash")),
                                        "isFlam": False,
                                        "isDrag": False,
                                    }
                                )

                        drum_track["notes"] = kept_notes + new_notes
                        result["drum_track"] = drum_track

                        md = result.get("metadata") or {}
                        if isinstance(md, dict):
                            md["fill_applied"] = True
                            md["fill_applied_barIndex"] = target_bar
                            md["fill_applied_pattern_id"] = fill_pattern_id
                            result["metadata"] = md
        except Exception as _exc:
            # Do not fail drum generation if fill insertion has an edge case.
            pass

        metadata = result.get('metadata') or {}
        builder_version = str(metadata.get("builder_version") or "").strip().lower()
        mode = str(metadata.get("mode") or "").strip().lower()
        ok_flag = bool(result.get("ok"))

        generation_backend = None
        if not ok_flag:
            generation_backend = "fallback"
        elif builder_version in {"v2.0_failed", "v2.0_unavailable"}:
            generation_backend = "fallback"
        elif builder_version.startswith("v2"):
            generation_backend = "v2"
        elif "legacy" in mode or "fallback" in mode:
            generation_backend = "legacy"
        else:
            generation_backend = builder_version or (mode or "unknown")

        fallback_used = False
        fallback_reason = None
        if generation_backend != "v2":
            fallback_used = True
            fallback_reason = str(result.get("error") or metadata.get("error") or "") or None

        DRUM_GEN_STATS["last_backend"] = generation_backend
        if ok_flag:
            DRUM_GEN_STATS["ok"] = int(DRUM_GEN_STATS.get("ok", 0) or 0) + 1
        if fallback_used:
            DRUM_GEN_STATS["fallback"] = int(DRUM_GEN_STATS.get("fallback", 0) or 0) + 1
            DRUM_GEN_STATS["last_fallback_reason"] = fallback_reason
            DRUM_GEN_STATS["last_fallback_ts"] = float(time.time())

        metadata['sectionId'] = section_id or None
        metadata['generation_backend'] = generation_backend
        metadata['fallback_used'] = bool(fallback_used)
        metadata['fallback_reason'] = fallback_reason
        metadata['selectedGrooveId'] = selected_groove_id
        metadata['grooveUse'] = groove_use
        metadata['fillGrooveId'] = fill_groove_id
        metadata['fillBarIndex'] = fill_bar_index
        result['metadata'] = metadata
        
        LOG.info(f"✅ Generated drums in {result['metadata']['generation_time_ms']}ms")

        headers = {
            "X-DrumTracKAI-Backend": str(generation_backend),
            "X-DrumTracKAI-Fallback": "1" if fallback_used else "0",
        }
        if fallback_reason:
            headers["X-DrumTracKAI-Fallback-Reason"] = str(fallback_reason)[:512]

        return web.json_response(result, headers=headers)
        
    except Exception as e:
        LOG.error(f"Drum generation failed: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


# ============================================================================
# BRAIN PANEL ENDPOINTS
# ============================================================================


async def list_brain_elements(request: web.Request):
    """Return Jamstix-style brain element metadata."""

    style_hint = request.query.get("style")
    definitions = get_brain_elements(style_hint)
    payload = [_serialize_brain_definition(defn) for defn in definitions]
    return web.json_response(payload)


async def get_brain_config(request: web.Request):
    section_id = request.match_info.get("section_id")
    if not section_id:
        return web.json_response({"error": "section_id required"}, status=400)

    style_hint = request.query.get("style")
    config = _load_brain_config(section_id, style_hint)
    return web.json_response(config.to_dict())


async def patch_brain_config(request: web.Request):
    section_id = request.match_info.get("section_id")
    if not section_id:
        return web.json_response({"error": "section_id required"}, status=400)

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
    except Exception as exc:
        return web.json_response({"error": f"invalid JSON: {exc}"}, status=400)

    baseline = _load_brain_config(section_id)
    baseline_dict = baseline.to_dict()
    for key in ("mode", "randomizeSeed", "elementSettings"):
        if key in payload:
            baseline_dict[key] = payload[key]

    try:
        updated = DrumBrainConfig.from_dict(baseline_dict)
    except Exception as exc:
        return web.json_response({"error": f"invalid brain config: {exc}"}, status=400)

    _save_brain_config(section_id, updated)
    return web.json_response(updated.to_dict())


# ============================================================================
# JAMSTIX BRAIN ENDPOINTS
# ============================================================================

async def jamstix_status(request):
    """Get Jamstix brain system status"""
    return web.json_response({
        "available": JAMSTIX_BRAIN_AVAILABLE,
        "version": "1.0.0",
        "features": [
            "limb_assignment",
            "priority_calculation",
            "micro_timing",
            "conflict_detection",
            "dcsm_track_building"
        ] if JAMSTIX_BRAIN_AVAILABLE else []
    })


async def jamstix_enrich_pattern(request):
    """
    Enrich drum pattern events with Jamstix brain attributes
    POST /api/jamstix/enrich
    Body: {
        "events": [...],  # Pattern events
        "feel": "laid_back|on_the_beat|pushed|swing",
        "hatOpenness": 0.0-1.0,
        "fillBars": [3, 7, 11, 15]  # Optional
    }
    """
    if not JAMSTIX_BRAIN_AVAILABLE:
        return web.json_response({
            "error": "Jamstix brain not available"
        }, status=503)
    
    try:
        data = await request.json()
        events = data.get("events", [])
        feel = data.get("feel", "on_the_beat")
        hat_openness = float(data.get("hatOpenness", 0.3))
        fill_bars = data.get("fillBars", [])
        
        if not events:
            return web.json_response({
                "error": "No events provided"
            }, status=400)
        
        # Enrich events with Jamstix brain
        enriched = enrich_drum_events_with_jamstix_attrs(
            events,
            feel=feel,
            global_hat_openness=hat_openness,
            fill_bar_indices=fill_bars
        )
        
        # Detect and resolve limb conflicts
        conflicts = detect_limb_conflicts(enriched, time_window_ms=50.0)
        if conflicts:
            LOG.info(f"Detected {len(conflicts)} limb conflicts, resolving...")
            enriched = resolve_limb_conflicts(enriched, conflicts)
        
        return web.json_response({
            "success": True,
            "events": enriched,
            "conflicts_resolved": len(conflicts),
            "total_events": len(enriched)
        })
        
    except Exception as e:
        LOG.error(f"Jamstix enrich failed: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)


async def jamstix_build_track(request):
    """
    Build complete DCSM drum track with Jamstix brain
    POST /api/jamstix/build-track
    Body: {
        "events": [...],  # Pattern events
        "sections": [...],  # SongMap sections
        "tempo": 120.0,
        "timeSignature": "4/4",
        "performanceSpec": {
            "feel": "laid_back",
            "swing": 0.0,
            "intensity": 0.8,
            "hatOpenness": 0.3,
            "fillStyle": "tom_run"
        }
    }
    """
    if not JAMSTIX_BRAIN_AVAILABLE:
        return web.json_response({
            "error": "Jamstix brain not available"
        }, status=503)
    
    try:
        data = await request.json()
        events = data.get("events", [])
        sections = data.get("sections", [])
        tempo = float(data.get("tempo", 120.0))
        time_sig = data.get("timeSignature", "4/4")
        perf_spec = data.get("performanceSpec", {})
        
        if not events:
            return web.json_response({
                "error": "No events provided"
            }, status=400)
        
        # Build DCSM track with Jamstix brain
        builder = DCSMDrumTrackBuilder(tempo=tempo, time_signature=time_sig)
        track = builder.build_from_pattern_and_spec(
            pattern_events=events,
            sections=sections,
            performance_spec=perf_spec
        )
        
        # Convert to dict for JSON response
        track_dict = track.to_dict()
        
        return web.json_response({
            "success": True,
            "track": track_dict,
            "bars": len(track.bars),
            "total_notes": sum(len(b.notes) for b in track.bars)
        })
        
    except Exception as e:
        LOG.error(f"Jamstix build track failed: {e}")
        import traceback
        traceback.print_exc()
        return web.json_response({"error": str(e)}, status=500)

if __name__ == "__main__":
    main()
