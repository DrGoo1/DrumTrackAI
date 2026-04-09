import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from backend.drummerbrain.phrase_event_loader_sentient import build_phrase_event_pattern
except Exception:  # pragma: no cover - optional additive patch
    build_phrase_event_pattern = None
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except Exception:
    torch = None
    nn = None
    TORCH_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except Exception:
    ort = None
    ONNX_AVAILABLE = False

try:
    import onnx  # noqa: F401
    ONNX_EXPORT_AVAILABLE = True
except Exception:
    onnx = None
    ONNX_EXPORT_AVAILABLE = False

# ------------------------------------------------------------
# Version & configuration
# ------------------------------------------------------------

API_VERSION = "1.1.0"

# INFERENCE_BACKEND: "auto" | "torch" | "onnx"
INFERENCE_BACKEND = str(os.getenv("INFERENCE_BACKEND", "auto")).strip().lower()

# Caching bins (for UI dragging; tune as needed)
CACHE_ENABLED = str(os.getenv("HUMANIZE_CACHE_ENABLED", "1")).strip() not in {"0", "false", "no"}
CACHE_TEMPO_BIN = float(os.getenv("HUMANIZE_CACHE_TEMPO_BIN", "1.0"))          # bpm bin size
CACHE_COMPLEXITY_BIN = float(os.getenv("HUMANIZE_CACHE_COMPLEXITY_BIN", "0.02"))  # 0..1 bin size

# Structured logging
LOG_LEVEL = str(os.getenv("LOG_LEVEL", "INFO")).upper()
SERVICE_NAME = str(os.getenv("SERVICE_NAME", "drumtracai-humanize")).strip()

# ------------------------------------------------------------
# Logging setup (Step 4: structured logging)
# ------------------------------------------------------------

logger = logging.getLogger(SERVICE_NAME)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(LOG_LEVEL)

def log_event(event: str, **fields: Any) -> None:
    payload = {"ts": time.time(), "service": SERVICE_NAME, "event": event, **fields}
    try:
        logger.info(json.dumps(payload, separators=(",", ":"), default=str))
    except Exception:
        # Last resort: avoid crashing on logging
        logger.info(f"{event} {fields}")

# ------------------------------------------------------------
# Defaults & constants
# ------------------------------------------------------------

DEFAULT_HUMANIZATION_PARAMS: Dict[str, float] = {
    "timing_variance": 0.06,
    "timing_drift": 0.03,
    "groove_consistency": 0.75,
    "swing_factor": 0.08,
    "velocity_variance": 0.22,
    "ghost_note_frequency": 0.22,
    "velocity_humanization": 0.55,
    "hihat_variation": 0.45,
    "kick_snare_relationship": 0.55,
}

PARAM_KEYS: List[str] = [
    "timing_variance",
    "timing_drift",
    "groove_consistency",
    "swing_factor",
    "velocity_variance",
    "ghost_note_frequency",
    "velocity_humanization",
    "hihat_variation",
    "kick_snare_relationship",
]

_STYLE_TO_INT = {
    "rock": 0,
    "funk": 1,
    "jazz": 2,
    "latin": 3,
    "metal": 4,
    "pop": 5,
    "live_recording": 6,
    "shuffle": 7,
    "blues": 8,
}

def _style_to_int(style: Optional[str]) -> int:
    return int(_STYLE_TO_INT.get(str(style or "rock").strip().lower(), 0))

# ------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------

class HumanizationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    tempo_bpm: float = Field(default=120.0, ge=30.0, le=320.0)
    style: Optional[str] = Field(default="rock")
    pattern_complexity: float = Field(default=0.7, ge=0.0, le=1.0)

class HumanizationResponse(BaseModel):
    ok: bool
    params: Dict[str, float]
    metadata: Optional[Dict[str, Any]] = None

class HumanizationBatchRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    items: List[HumanizationRequest] = Field(default_factory=list, min_length=1, max_length=512)

class HumanizationBatchResponse(BaseModel):
    ok: bool
    items: List[HumanizationResponse]
    metadata: Optional[Dict[str, Any]] = None

class PerformanceSpecRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cfg: Dict[str, Any] = Field(default_factory=dict)
    songmap_summary: Dict[str, Any] = Field(default_factory=dict)
    drummer_profile: Dict[str, Any] = Field(default_factory=dict)

class PerformanceSpecResponse(BaseModel):
    ok: bool
    spec: Dict[str, Any]
    metadata: Dict[str, Any]


class SongRoadmapRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cfg: Dict[str, Any] = Field(default_factory=dict)
    songmap_summary: Dict[str, Any] = Field(default_factory=dict)
    drummer_profile: Dict[str, Any] = Field(default_factory=dict)


class SongRoadmapResponse(BaseModel):
    ok: bool
    roadmap: Dict[str, Any]
    metadata: Dict[str, Any]

# ------------------------------------------------------------
# Model definition (Torch)
# ------------------------------------------------------------
if TORCH_AVAILABLE and nn is not None:
    class DrumHumanizationModel(nn.Module):
        def __init__(self, input_size: int = 3, hidden_size: int = 64, output_size: int = 9):
            super().__init__()
            self.encoder = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(hidden_size, hidden_size * 2),
                nn.ReLU(),
                nn.Dropout(0.2),
            )
            self.predictor = nn.Sequential(
                nn.Linear(hidden_size * 2, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, output_size),
                nn.Sigmoid(),
            )

        def forward(self, x):
            return self.predictor(self.encoder(x))
else:
    DrumHumanizationModel = None  # type: ignore

# ------------------------------------------------------------
# Model path resolution & loading
# ------------------------------------------------------------

def _resolve_active_model_path() -> Path:
    explicit = os.getenv("ACTIVE_MODEL_PATH")
    if explicit:
        return Path(explicit)

    active_json = os.getenv("ACTIVE_MODEL_JSON", "/models/production/active_model.json")
    p = Path(active_json)
    if p.exists():
        data = json.loads(p.read_text(encoding="utf-8"))

        candidates = data.get("candidates")
        if isinstance(candidates, list) and candidates:
            for entry in candidates:
                if not isinstance(entry, str):
                    continue
                entry = entry.strip()
                if not entry:
                    continue
                resolved = Path(entry)
                if not resolved.is_absolute():
                    resolved = (p.parent / resolved).resolve()
                if resolved.exists():
                    return resolved

        model_path = data.get("path")
        if isinstance(model_path, str) and model_path.strip():
            resolved = Path(model_path.strip())
            if not resolved.is_absolute():
                resolved = (p.parent / resolved).resolve()
            return resolved

    return Path("/models/checkpoints/best_model.pth")

def _resolve_onnx_model_path(checkpoint_path: Optional[Path]) -> Optional[Path]:
    explicit = os.getenv("ONNX_MODEL_PATH")
    if explicit:
        p = Path(explicit)
        return p if p.exists() else p

    if checkpoint_path is None:
        return None

    # If checkpoint is foo.pth, try foo.onnx in same directory
    try:
        candidate = checkpoint_path.with_suffix(".onnx")
        if candidate.exists():
            return candidate
    except Exception:
        pass

    # Fallback default
    p = Path("/models/checkpoints/best_model.onnx")
    return p if p.exists() else p

def _load_torch_model(model_path: Path) -> Tuple["DrumHumanizationModel", str]:
    if not TORCH_AVAILABLE or torch is None or DrumHumanizationModel is None:
        raise RuntimeError("Torch not available")
    if not model_path.exists():
        raise FileNotFoundError(str(model_path))

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DrumHumanizationModel(input_size=3, output_size=len(PARAM_KEYS)).to(device)
    checkpoint = torch.load(model_path, map_location=device)

    state = checkpoint.get("model_state_dict") if isinstance(checkpoint, dict) else None
    if state is None and isinstance(checkpoint, dict):
        state = checkpoint.get("state_dict")
    if state is None and isinstance(checkpoint, dict) and all(isinstance(k, str) for k in checkpoint.keys()):
        state = checkpoint

    if not isinstance(state, dict):
        raise RuntimeError("Unsupported checkpoint format")

    model.load_state_dict(state, strict=False)
    model.eval()
    return model, device

def _load_onnx_session(onnx_path: Path):
    if not ONNX_AVAILABLE or ort is None:
        raise RuntimeError("onnxruntime not available")
    # Providers: prefer CUDA when available, else CPU
    providers = None
    try:
        providers = ort.get_available_providers()
    except Exception:
        providers = None

    # Choose provider order conservatively
    preferred = []
    if providers and "CUDAExecutionProvider" in providers:
        preferred.append("CUDAExecutionProvider")
    preferred.append("CPUExecutionProvider")

    sess = ort.InferenceSession(onnx_path.as_posix(), providers=preferred)
    return sess

def _export_onnx_from_torch(model: "DrumHumanizationModel", device: str, onnx_path: Path) -> None:
    if not TORCH_AVAILABLE or torch is None:
        raise RuntimeError("Torch not available for ONNX export")
    if not ONNX_EXPORT_AVAILABLE:
        raise RuntimeError("onnx package not available for export")

    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = onnx_path.with_suffix(onnx_path.suffix + ".tmp")

    # Export on CPU for portability/stability; keep inference model on its original device.
    orig_device = "cpu"
    try:
        try:
            orig_device = str(next(model.parameters()).device)
        except Exception:
            orig_device = "cpu"

        model_cpu = model.to("cpu")
        model_cpu.eval()
        dummy = torch.zeros((1, 3), dtype=torch.float32, device="cpu")

        torch.onnx.export(
            model_cpu,
            dummy,
            tmp_path.as_posix(),
            input_names=["x"],
            output_names=["y"],
            opset_version=17,
            do_constant_folding=True,
            dynamic_axes={"x": {0: "batch"}, "y": {0: "batch"}},
        )

        if not tmp_path.exists():
            raise RuntimeError(f"ONNX export did not produce file: {tmp_path}")

        tmp_path.replace(onnx_path)
        if not onnx_path.exists():
            raise RuntimeError(f"ONNX export failed to finalize file: {onnx_path}")
    finally:
        try:
            if orig_device and orig_device != "cpu":
                model.to(orig_device)
            elif device and device != "cpu":
                model.to(device)
        except Exception:
            pass

# ------------------------------------------------------------
# Input normalization
# ------------------------------------------------------------

def _normalize_inputs(tempo_bpm: float, style_int: float, complexity: float) -> np.ndarray:
    tempo = float(np.clip(tempo_bpm, 30.0, 320.0))
    tempo_n = (np.log(tempo) - np.log(30.0)) / (np.log(320.0) - np.log(30.0))
    tempo_n = float(np.clip(tempo_n, 0.0, 1.0))

    style_max = max(_STYLE_TO_INT.values()) if _STYLE_TO_INT else 1
    style_n = float(np.clip(float(style_int) / float(max(style_max, 1)), 0.0, 1.0))

    comp_n = float(np.clip(complexity, 0.0, 1.0))
    return np.array([[tempo_n, style_n, comp_n]], dtype=np.float32)

def _normalize_batch(reqs: List[HumanizationRequest]) -> np.ndarray:
    xs = []
    for r in reqs:
        xs.append(_normalize_inputs(r.tempo_bpm, float(_style_to_int(r.style)), r.pattern_complexity)[0])
    return np.stack(xs, axis=0).astype(np.float32)

# ------------------------------------------------------------
# Cache (Step 3: caching)
# ------------------------------------------------------------

def _bin(v: float, bin_size: float) -> float:
    if bin_size <= 0:
        return float(v)
    return float(round(v / bin_size) * bin_size)

def _cache_key(req: HumanizationRequest) -> Tuple[float, int, float]:
    return (_bin(float(req.tempo_bpm), CACHE_TEMPO_BIN), int(_style_to_int(req.style)), _bin(float(req.pattern_complexity), CACHE_COMPLEXITY_BIN))

@lru_cache(maxsize=8192)
def _cached_infer(tempo_bpm: float, style_int: int, complexity: float) -> Dict[str, float]:
    # This function will be called only when CACHE_ENABLED is true.
    # It routes to backend inference for a single item.
    req = HumanizationRequest(tempo_bpm=tempo_bpm, style=str(style_int), pattern_complexity=complexity)  # style stored as int string here
    # We'll bypass style mapping and pass style_int directly by injecting via helper below.
    return _infer_single_with_styleint(tempo_bpm, style_int, complexity)

# ------------------------------------------------------------
# FastAPI app / global state
# ------------------------------------------------------------

app = FastAPI(title="DrumTracKAI Humanization Service", version=API_VERSION)

TORCH_MODEL = None
TORCH_DEVICE = "cpu"
TORCH_MODEL_PATH: Optional[Path] = None

ONNX_SESSION = None
ONNX_MODEL_PATH: Optional[Path] = None

MODEL_LOAD_ERROR: Optional[str] = None
ACTIVE_BACKEND: str = "fallback"

# ------------------------------------------------------------
# Backend selection & load (Step 2: ONNX optional inference)
# ------------------------------------------------------------

def _select_backend() -> str:
    if INFERENCE_BACKEND in {"torch", "onnx"}:
        return INFERENCE_BACKEND
    # auto
    if ONNX_AVAILABLE:
        return "onnx"
    if TORCH_AVAILABLE:
        return "torch"
    return "fallback"

def _startup_load():
    global TORCH_MODEL, TORCH_DEVICE, TORCH_MODEL_PATH, ONNX_SESSION, ONNX_MODEL_PATH, MODEL_LOAD_ERROR, ACTIVE_BACKEND

    backend = _select_backend()

    # Try ONNX if selected
    checkpoint_path = None
    try:
        checkpoint_path = _resolve_active_model_path()
    except Exception:
        checkpoint_path = None

    if backend == "onnx":
        try:
            ONNX_MODEL_PATH = _resolve_onnx_model_path(checkpoint_path)
            if ONNX_MODEL_PATH is None:
                raise RuntimeError("ONNX path not resolved")
            if not ONNX_MODEL_PATH.exists() and TORCH_AVAILABLE and torch is not None:
                # Generate ONNX from torch checkpoint when missing.
                if checkpoint_path is None:
                    checkpoint_path = _resolve_active_model_path()
                tmp_model, tmp_device = _load_torch_model(checkpoint_path)
                _export_onnx_from_torch(tmp_model, tmp_device, ONNX_MODEL_PATH)
            if not ONNX_MODEL_PATH.exists():
                raise FileNotFoundError(str(ONNX_MODEL_PATH))
            ONNX_SESSION = _load_onnx_session(ONNX_MODEL_PATH)
            ACTIVE_BACKEND = "onnx"
            log_event("startup", backend="onnx", onnx_model_path=str(ONNX_MODEL_PATH))
            return
        except Exception as e:
            MODEL_LOAD_ERROR = f"ONNX load failed: {e}"
            ONNX_SESSION = None
            log_event("startup", backend="onnx_failed", error=MODEL_LOAD_ERROR)
            # fall through to torch if auto; if explicitly onnx, remain fallback
            if INFERENCE_BACKEND == "onnx":
                ACTIVE_BACKEND = "fallback"
                log_event("startup", backend="fallback", error=MODEL_LOAD_ERROR)
                return
            backend = "torch"

    if backend == "torch":
        try:
            if checkpoint_path is None:
                checkpoint_path = _resolve_active_model_path()
            TORCH_MODEL_PATH = checkpoint_path
            TORCH_MODEL, TORCH_DEVICE = _load_torch_model(TORCH_MODEL_PATH)
            ACTIVE_BACKEND = "torch"

            # Best-effort: export/load ONNX sidecar so ONNX is available too.
            try:
                ONNX_MODEL_PATH = _resolve_onnx_model_path(TORCH_MODEL_PATH)
                if ONNX_MODEL_PATH is not None and not ONNX_MODEL_PATH.exists():
                    _export_onnx_from_torch(TORCH_MODEL, TORCH_DEVICE, ONNX_MODEL_PATH)
                if ONNX_MODEL_PATH is not None and ONNX_MODEL_PATH.exists():
                    ONNX_SESSION = _load_onnx_session(ONNX_MODEL_PATH)
            except Exception as e:
                MODEL_LOAD_ERROR = f"ONNX load failed: {e}"

            log_event("startup", backend="torch", device=TORCH_DEVICE, checkpoint=str(TORCH_MODEL_PATH))
            return
        except Exception as e:
            MODEL_LOAD_ERROR = f"Torch load failed: {e}"
            TORCH_MODEL = None
            TORCH_DEVICE = "cpu"
            if INFERENCE_BACKEND == "torch":
                ACTIVE_BACKEND = "fallback"
                log_event("startup", backend="fallback", error=MODEL_LOAD_ERROR)
                return
            ACTIVE_BACKEND = "fallback"
            log_event("startup", backend="fallback", error=MODEL_LOAD_ERROR)
            return

    ACTIVE_BACKEND = "fallback"
    log_event("startup", backend="fallback")

_startup_load()

# ------------------------------------------------------------
# Middleware: request latency logs (structured)
# ------------------------------------------------------------

@app.middleware("http")
async def latency_middleware(request: Request, call_next):
    t0 = time.perf_counter()
    try:
        resp = await call_next(request)
        return resp
    finally:
        dt_ms = (time.perf_counter() - t0) * 1000.0
        log_event(
            "request",
            method=request.method,
            path=request.url.path,
            status=getattr(locals().get("resp", None), "status_code", None),
            latency_ms=round(dt_ms, 3),
            backend=ACTIVE_BACKEND,
        )

# ------------------------------------------------------------
# Inference utilities
# ------------------------------------------------------------

def _fallback_response(metadata: Optional[Dict[str, Any]] = None) -> HumanizationResponse:
    return HumanizationResponse(ok=True, params=dict(DEFAULT_HUMANIZATION_PARAMS), metadata=metadata)

def _infer_single_with_styleint(tempo_bpm: float, style_int: int, complexity: float) -> Dict[str, float]:
    """
    Low-level inference for cache (style passed as int already).
    Returns params dict only.
    """
    if ACTIVE_BACKEND == "torch" and TORCH_MODEL is not None and TORCH_AVAILABLE and torch is not None:
        x = _normalize_inputs(tempo_bpm, float(style_int), complexity)
        with torch.no_grad():
            xt = torch.from_numpy(x).to(TORCH_DEVICE)
            y = TORCH_MODEL(xt).detach().cpu().numpy()[0]
        return {k: float(y[i]) for i, k in enumerate(PARAM_KEYS)}

    if ACTIVE_BACKEND == "onnx" and ONNX_SESSION is not None and ONNX_AVAILABLE and ort is not None:
        x = _normalize_inputs(tempo_bpm, float(style_int), complexity)
        y = ONNX_SESSION.run(None, {"x": x.astype(np.float32)})[0][0]
        return {k: float(y[i]) for i, k in enumerate(PARAM_KEYS)}

    return dict(DEFAULT_HUMANIZATION_PARAMS)

def _infer_many(reqs: List[HumanizationRequest]) -> List[HumanizationResponse]:
    """
    Batch inference (Step 1: batch endpoint).
    Uses caching per-item when enabled, and uses backend batch execution when available.
    """
    if not reqs:
        return []

    # If caching is enabled, resolve from cache first, and collect misses
    outputs: List[Optional[HumanizationResponse]] = [None] * len(reqs)
    misses_idx: List[int] = []
    misses: List[HumanizationRequest] = []

    if CACHE_ENABLED:
        for i, r in enumerate(reqs):
            tempo_b = _bin(float(r.tempo_bpm), CACHE_TEMPO_BIN)
            style_i = int(_style_to_int(r.style))
            comp_b = _bin(float(r.pattern_complexity), CACHE_COMPLEXITY_BIN)
            try:
                params = _cached_infer(tempo_b, style_i, comp_b)
                outputs[i] = HumanizationResponse(ok=True, params=dict(params), metadata={"backend": ACTIVE_BACKEND, "cached": True})
            except Exception:
                misses_idx.append(i)
                misses.append(r)
    else:
        misses_idx = list(range(len(reqs)))
        misses = reqs

    # If no misses, return all cached
    if not misses:
        return [o if o is not None else _fallback_response(metadata={"backend": ACTIVE_BACKEND}) for o in outputs]

    # Backend batch inference for misses
    start = time.perf_counter()
    if ACTIVE_BACKEND == "torch" and TORCH_MODEL is not None and TORCH_AVAILABLE and torch is not None:
        x = _normalize_batch(misses)
        with torch.no_grad():
            xt = torch.from_numpy(x).to(TORCH_DEVICE)
            yb = TORCH_MODEL(xt).detach().cpu().numpy()  # (B, 9)
        for j, outrow in enumerate(yb):
            params = {k: float(outrow[i]) for i, k in enumerate(PARAM_KEYS)}
            idx = misses_idx[j]
            outputs[idx] = HumanizationResponse(ok=True, params=params, metadata={"backend": "torch", "cached": False})
    elif ACTIVE_BACKEND == "onnx" and ONNX_SESSION is not None and ONNX_AVAILABLE and ort is not None:
        x = _normalize_batch(misses).astype(np.float32)
        yb = ONNX_SESSION.run(None, {"x": x})[0]  # (B, 9)
        for j, outrow in enumerate(yb):
            params = {k: float(outrow[i]) for i, k in enumerate(PARAM_KEYS)}
            idx = misses_idx[j]
            outputs[idx] = HumanizationResponse(ok=True, params=params, metadata={"backend": "onnx", "cached": False})
    else:
        for idx in misses_idx:
            outputs[idx] = _fallback_response(metadata={"backend": "fallback", "cached": False})

    dt_ms = (time.perf_counter() - start) * 1000.0
    log_event("humanize_batch", n=len(reqs), misses=len(misses), latency_ms=round(dt_ms, 3), backend=ACTIVE_BACKEND, cache=CACHE_ENABLED)

    return [o if o is not None else _fallback_response(metadata={"backend": ACTIVE_BACKEND}) for o in outputs]

def _infer_one(req: HumanizationRequest) -> HumanizationResponse:
    if CACHE_ENABLED:
        tempo_b, style_i, comp_b = _cache_key(req)
        try:
            params = _cached_infer(tempo_b, style_i, comp_b)
            return HumanizationResponse(ok=True, params=dict(params), metadata={"backend": ACTIVE_BACKEND, "cached": True})
        except Exception:
            pass
    # No cache or cache miss => use batch path for uniformity
    return _infer_many([req])[0]

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------

@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "version": API_VERSION,
        "backend": ACTIVE_BACKEND,
        "torch_available": TORCH_AVAILABLE,
        "onnx_available": ONNX_AVAILABLE,
        "cache_enabled": CACHE_ENABLED,
        "cache_bins": {"tempo_bpm": CACHE_TEMPO_BIN, "complexity": CACHE_COMPLEXITY_BIN},
        "torch": {
            "model_loaded": TORCH_MODEL is not None,
            "device": TORCH_DEVICE,
            "checkpoint": str(TORCH_MODEL_PATH) if TORCH_MODEL_PATH else None,
        },
        "onnx": {
            "session_loaded": ONNX_SESSION is not None,
            "model_path": str(ONNX_MODEL_PATH) if ONNX_MODEL_PATH else None,
        },
        "model_error": MODEL_LOAD_ERROR,
    }

@app.post("/v1/humanization_params", response_model=HumanizationResponse)
def humanization_params(req: HumanizationRequest):
    try:
        return _infer_one(req)
    except Exception as e:
        return _fallback_response(metadata={"reason": "inference_error", "error": str(e), "backend": ACTIVE_BACKEND})

@app.post("/v1/humanization_params_batch", response_model=HumanizationBatchResponse)
def humanization_params_batch(req: HumanizationBatchRequest):
    try:
        items = _infer_many(req.items)
        return HumanizationBatchResponse(ok=True, items=items, metadata={"backend": ACTIVE_BACKEND, "cache_enabled": CACHE_ENABLED})
    except Exception as e:
        # Return all fallback to avoid UI failure
        items = [_fallback_response(metadata={"reason": "batch_error", "error": str(e), "backend": ACTIVE_BACKEND}) for _ in req.items]
        return HumanizationBatchResponse(ok=True, items=items, metadata={"backend": ACTIVE_BACKEND, "error": str(e)})

# ------------------------------------------------------------
# /v1/performance_spec (unchanged core logic; uses humanization endpoint)
# ------------------------------------------------------------

@app.post("/v1/performance_spec", response_model=PerformanceSpecResponse)
def performance_spec(req: PerformanceSpecRequest):
    cfg = req.cfg or {}
    songmap_summary = req.songmap_summary or {}
    drummer_profile = req.drummer_profile or {}

    groove_controls = cfg.get("grooveControls")
    if not isinstance(groove_controls, dict):
        groove_controls = {}

    brain_config = cfg.get("brainConfig")
    if not isinstance(brain_config, dict):
        brain_config = {}

    def _brain_element_value(element_id: str) -> Optional[float]:
        elements = brain_config.get("elementSettings")
        if not isinstance(elements, list):
            return None
        for entry in elements:
            if not isinstance(entry, dict):
                continue
            if entry.get("elementId") != element_id:
                continue
            if entry.get("disabled") is True:
                return None
            try:
                return float(entry.get("value"))
            except Exception:
                return None
        return None

    tempos = cfg.get("tempos") or [cfg.get("tempo", 120.0)]
    if not isinstance(tempos, list) or not tempos:
        tempos = [120.0]

    avg_tempo = float(sum(float(t) for t in tempos) / max(len(tempos), 1))
    style = cfg.get("style")

    humanize_amount = float(cfg.get("humanizeAmount", 0.5))
    swing_amount_cfg = float(cfg.get("swingAmount", 0.0))
    ghost_amount_cfg = float(cfg.get("ghostNoteAmount", 0.2))
    intensity = float(cfg.get("intensity", 0.6))
    variation = float(cfg.get("variation", 0.5))

    try:
        gc_swing = float(groove_controls.get("swing", 0.0) or 0.0)
        swing_amount_cfg = max(0.0, min(1.0, swing_amount_cfg + gc_swing))
    except Exception:
        pass

    try:
        gc_ghost = float(groove_controls.get("ghost_note_density", 0.0) or 0.0)
        ghost_amount_cfg = max(0.0, min(1.0, ghost_amount_cfg + (gc_ghost - 0.3) * 0.5))
    except Exception:
        pass

    try:
        gc_humanize = float(groove_controls.get("humanize", 0.0) or 0.0)
        humanize_amount = max(0.0, min(1.0, humanize_amount + (gc_humanize - 0.5) * 0.5))
    except Exception:
        pass

    try:
        gc_fill = float(groove_controls.get("fill_density", 0.0) or 0.0)
        variation = max(0.0, min(1.0, variation + (gc_fill - 0.4) * 0.25))
    except Exception:
        pass

    try:
        gc_dyn = float(groove_controls.get("dynamic_range", 0.0) or 0.0)
        intensity = max(0.0, min(1.0, intensity + (gc_dyn - 0.5) * 0.25))
    except Exception:
        pass

    pattern_complexity = float(cfg.get("complexity", 0.7))

    params_resp = humanization_params(HumanizationRequest(
        tempo_bpm=avg_tempo,
        style=style,
        pattern_complexity=pattern_complexity,
    ))
    params = params_resp.params

    timing_tightness = drummer_profile.get("timing_tightness")
    if timing_tightness is None:
        timing_tightness = drummer_profile.get("timing_precision")
    try:
        timing_tightness = float(timing_tightness) if timing_tightness is not None else 0.8
    except Exception:
        timing_tightness = 0.8
    timing_tightness = max(0.0, min(1.0, timing_tightness))

    timing_override = _brain_element_value("timing")
    if timing_override is not None:
        timing_tightness = max(0.0, min(1.0, timing_tightness + (timing_override - 0.5) * 0.8))

    ghost_pref = drummer_profile.get("ghost_note_frequency")
    if ghost_pref is None:
        ghost_pref = drummer_profile.get("ghost_frequency")
    try:
        ghost_pref = float(ghost_pref) if ghost_pref is not None else 0.5
    except Exception:
        ghost_pref = 0.5
    ghost_pref = max(0.0, min(1.0, ghost_pref))

    preferred_feel = drummer_profile.get("preferred_feel") or drummer_profile.get("feel")
    preferred_feel = str(preferred_feel or "").strip().lower()

    signature_techniques = drummer_profile.get("signature_techniques")
    if not isinstance(signature_techniques, list):
        signature_techniques = []
    signature_text = " ".join(str(t).lower() for t in signature_techniques)

    swing_from_model = float(params.get("swing_factor", 0.0))
    swing_amount = max(0.0, min(1.0, (swing_amount_cfg + swing_from_model) * 0.5))

    timing_var = float(params.get("timing_variance", 0.0))
    timing_drift = float(params.get("timing_drift", 0.0))
    groove_consistency = float(params.get("groove_consistency", 0.8))

    max_ms = 10.0 * max(0.0, min(1.0, humanize_amount))
    var_ms = max(0.0, min(max_ms, timing_var * max_ms))
    drift_ms = max(-max_ms, min(max_ms, (timing_drift - 0.5) * 2.0 * (max_ms * 0.6)))
    tightness = max(0.0, min(1.0, groove_consistency))
    var_ms *= (0.4 + 0.6 * (1.0 - tightness))
    var_ms *= (0.4 + 0.6 * (1.0 - timing_tightness))

    laid_back = 0.0
    feel_map = {"rock": "straight", "funk": "laid_back", "jazz": "swing", "shuffle": "shuffle", "blues": "shuffle"}
    global_feel = feel_map.get(str(style or "").lower(), "straight")
    if preferred_feel in {"straight", "swing", "shuffle", "laid_back", "pushed"}:
        global_feel = preferred_feel
    if swing_amount > 0.55:
        global_feel = "swing"
    if global_feel == "laid_back":
        laid_back = 0.2
    if global_feel == "pushed":
        laid_back = -0.2

    if "laid" in signature_text or "dilla" in signature_text or "behind" in signature_text:
        laid_back = max(laid_back, 0.28)
        if global_feel == "straight":
            global_feel = "laid_back"
    if "pocket" in signature_text:
        var_ms *= 0.85
    if "tight" in signature_text or "precision" in signature_text:
        var_ms *= 0.7

    brain_mode = str(brain_config.get("mode") or "").strip().lower()
    if brain_mode == "easy":
        var_ms *= 0.85
    elif brain_mode == "pro":
        var_ms *= 1.05

    def _subdivision_offsets(scale: float) -> list:
        out = []
        for i in range(16):
            base = float(np.sin((i + 1) * 1.7)) * var_ms * scale
            if (i % 2) == 1:
                base += swing_amount * 8.0
            base += drift_ms
            out.append(float(max(-max_ms, min(max_ms, base))))
        return out

    base_velocity = int(60 + intensity * 50)
    base_velocity = max(1, min(127, base_velocity))
    model_ghost_pref = float(params.get("ghost_note_frequency", 0.15))
    ghost_density = float(max(0.0, min(1.0, ghost_amount_cfg * (0.6 * ghost_pref + 0.4 * model_ghost_pref))))

    def _profile(inst: str, timing_scale: float, vel_bias: int, accent_boost: int, ghost_reduction: float, rr: int):
        return {
            "instrumentId": inst,
            "microTiming": {"subdivisionOffsetsMs": _subdivision_offsets(timing_scale), "swingAmount": float(swing_amount), "laidBackAmount": float(laid_back)},
            "velocityProfile": {
                "base": int(max(1, min(127, base_velocity + vel_bias))),
                "accentBoost": int(max(0, min(40, accent_boost))),
                "ghostReduction": float(max(0.0, min(1.0, ghost_reduction))),
                "randomRange": int(max(0, min(20, rr))),
                "phraseShape": "swell" if variation > 0.6 else "flat",
            },
            "ghostDensity": float(ghost_density if inst.startswith("snare") else ghost_density * 0.4),
            "flamProbability": float(0.1 if humanize_amount > 0.6 and inst.startswith("snare") else 0.0),
            "dragProbability": float(0.05 if humanize_amount > 0.7 and inst.startswith("snare") else 0.0),
        }

    section_id = str(cfg.get("sectionId", "section"))
    start_measure = int(cfg.get("startMeasure", 1))
    end_measure = int(cfg.get("endMeasure", max(start_measure, start_measure)))

    sections = songmap_summary.get("sections")
    if not isinstance(sections, list) or not sections:
        sections = [{"label": section_id, "startBar": start_measure, "endBar": end_measure, "energy": 0.5}]

    phrases = []
    for idx, sec in enumerate(sections):
        if not isinstance(sec, dict):
            continue
        label = sec.get("label") or sec.get("type") or f"section_{idx}"

        bar_start = sec.get("startBar") if sec.get("startBar") is not None else sec.get("start")
        bar_end = sec.get("endBar") if sec.get("endBar") is not None else sec.get("end")

        try:
            bar_start = int(bar_start)
        except Exception:
            bar_start = start_measure
        try:
            bar_end = int(bar_end)
        except Exception:
            bar_end = end_measure
        if bar_end < bar_start:
            bar_end = bar_start

        energy = sec.get("energy")
        try:
            energy = float(energy) if energy is not None else 0.5
        except Exception:
            energy = 0.5
        energy = max(0.0, min(1.0, energy))

        energy_intensity = max(0.0, min(1.0, intensity * (0.75 + 0.5 * (energy - 0.5))))
        energy_vel = int(60 + energy_intensity * 50)
        energy_vel = max(1, min(127, energy_vel))

        local_base_velocity = energy_vel
        local_random = int(max(0.0, min(1.0, humanize_amount)) * 10)
        if "chorus" in str(label).lower() or "drop" in str(label).lower():
            local_random = min(20, int(local_random * 1.15))
        if "intro" in str(label).lower():
            local_random = int(local_random * 0.85)

        def _profile_local(inst: str, timing_scale: float, vel_bias: int, accent_boost: int, ghost_reduction: float, rr: int):
            profile = _profile(inst, timing_scale, vel_bias, accent_boost, ghost_reduction, rr)
            profile["velocityProfile"]["base"] = int(max(1, min(127, local_base_velocity + vel_bias)))
            profile["velocityProfile"]["randomRange"] = int(max(0, min(20, local_random)))
            return profile

        profiles = [
            _profile_local("kick", 0.5, 10, int(energy_intensity * 20), 0.7, int(humanize_amount * 8)),
            _profile_local("snare_center", 1.0, 0, int(15 + energy_intensity * 25), 0.4, int(humanize_amount * 10)),
            _profile_local("hihat_closed", 0.8, -10, int(8 + energy_intensity * 12), 0.6, int(humanize_amount * 6)),
            _profile_local("ride_bow", 0.7, -5, int(10 + energy_intensity * 15), 0.5, int(humanize_amount * 7)),
        ]

        phrase_assets = sec.get("phraseAssets") if isinstance(sec.get("phraseAssets"), dict) else {}
        phrase_selection = sec.get("phraseSelection") if isinstance(sec.get("phraseSelection"), dict) else {}
        phrase_event_pattern = None
        if build_phrase_event_pattern is not None:
            try:
                phrase_event_pattern = build_phrase_event_pattern(
                    phrase_assets=phrase_assets,
                    phrase_selection=phrase_selection,
                    bars=max(1, bar_end - bar_start + 1),
                )
            except Exception:
                phrase_event_pattern = None

        phrase_payload = {
            "phraseId": f"{section_id}_local_service_{idx}",
            "barStart": bar_start,
            "barEnd": bar_end,
            "profiles": profiles,
        }
        if phrase_selection:
            phrase_payload["phraseSelection"] = phrase_selection
        if phrase_assets:
            phrase_payload["phraseAssets"] = phrase_assets
        if phrase_event_pattern is not None:
            phrase_payload["phraseEventPattern"] = phrase_event_pattern

        phrases.append(phrase_payload)

    spec = {"styleId": style, "globalFeel": global_feel, "quantizationBase": "16th", "phrases": phrases}

    return PerformanceSpecResponse(
        ok=True,
        spec=spec,
        metadata={
            "version": API_VERSION,
            "backend": ACTIVE_BACKEND,
            "cache_enabled": CACHE_ENABLED,
            "torch_device": TORCH_DEVICE,
            "model_path": str(TORCH_MODEL_PATH) if TORCH_MODEL_PATH else None,
            "onnx_path": str(ONNX_MODEL_PATH) if ONNX_MODEL_PATH else None,
            "songmap_sections": len(songmap_summary.get("sections") or []),
            "drummer_profile_keys": len(drummer_profile.keys()),
        },
    )


# ------------------------------------------------------------
# /v1/song_roadmap (arrangement director layer)
# ------------------------------------------------------------


@app.post("/v1/song_roadmap", response_model=SongRoadmapResponse)
def song_roadmap(req: SongRoadmapRequest):
    cfg = req.cfg or {}
    drummer_profile = req.drummer_profile or {}
    song_sections = cfg.get("songSections")
    if not isinstance(song_sections, list):
        song_sections = []

    style_group = cfg.get("styleGroup") or cfg.get("style_group") or cfg.get("style") or "rock"
    style_group = str(style_group or "rock").strip().lower()

    tempos = cfg.get("tempos") or [cfg.get("tempo", 120.0)]
    if not isinstance(tempos, list) or not tempos:
        tempos = [120.0]
    try:
        avg_tempo = float(sum(float(t) for t in tempos) / max(len(tempos), 1))
    except Exception:
        avg_tempo = 120.0

    intensity = float(cfg.get("intensity", 0.65))
    variation = float(cfg.get("variation", 0.55))
    humanize_amount = float(cfg.get("humanizeAmount", 0.7))
    ghost_amount = float(cfg.get("ghostNoteAmount", 0.5))
    swing_amount = float(cfg.get("swingAmount", 0.0))
    chorus_ride_pref = float(cfg.get("chorusRidePreference", 0.0) or 0.0)

    preferred_feel = str(drummer_profile.get("preferred_feel") or drummer_profile.get("feel") or "").strip().lower()
    time_feel = preferred_feel if preferred_feel in {"straight", "swing", "shuffle", "laid_back", "pushed"} else "straight"
    if swing_amount >= 0.6 and time_feel == "straight":
        time_feel = "swing"

    def _section_key(name: str) -> str:
        raw = str(name or "").strip().lower()
        raw = "_".join(raw.split())
        raw = "".join(ch for ch in raw if (ch.isalnum() or ch == "_"))
        return raw.strip("_") or "section"

    def _energy_for_type(section_type: str) -> float:
        st = _section_key(section_type)
        base_map = {
            "intro": 0.45,
            "verse": 0.6,
            "pre": 0.72,
            "prechorus": 0.72,
            "chorus": 0.88,
            "bridge": 0.75,
            "solo": 0.78,
            "breakdown": 0.55,
            "outro": 0.5,
            "ending": 0.5,
        }
        base = base_map.get(st, 0.62)
        return max(0.0, min(1.0, (base * 0.7 + float(intensity) * 0.3)))

    global_fill_policy = {
        "defaultLength": "last_bar" if variation >= 0.55 else "last_2_beats",
        "frequency": "all_transitions" if variation >= 0.6 else "section_transitions",
        "transitionFills": True,
        "repetitionFills": bool(variation >= 0.7),
    }

    roadmap_sections: List[Dict[str, Any]] = []
    for idx, sec in enumerate(song_sections):
        if not isinstance(sec, dict):
            continue
        name = sec.get("name") or sec.get("label") or "section"
        bars = int(sec.get("bars") or 1)
        st = _section_key(name)
        energy = _energy_for_type(st)

        timekeeper = "hats"
        if st == "chorus" and (chorus_ride_pref >= 0.25 or energy >= 0.8):
            timekeeper = "ride"
        if st in {"bridge", "solo"} and energy >= 0.72:
            timekeeper = "mixed"

        fill_out_enabled = True
        if st == "intro":
            fill_out_enabled = False
        if st in {"outro", "ending"}:
            fill_out_enabled = True

        roadmap_sections.append(
            {
                "sectionIndex": idx,
                "sectionType": st,
                "bars": bars,
                "energy": energy,
                "orchestration": {
                    "timekeeper": timekeeper,
                    "hatOpenBias": max(0.0, min(1.0, 0.15 + energy * 0.35 + swing_amount * 0.15)),
                    "rideBellProbability": 0.1 if timekeeper in {"ride", "mixed"} else 0.02,
                    "crashDownbeatProbability": 0.65 if st in {"chorus", "bridge", "outro"} else 0.35,
                },
                "grooveIntent": {
                    "kickDensityTarget": max(0.0, min(1.0, 0.35 + energy * 0.45)),
                    "snareGhostTarget": max(0.0, min(1.0, ghost_amount * 0.8)),
                    "cymbalDensityTarget": max(0.0, min(1.0, 0.45 + energy * 0.4)),
                    "syncopation": max(0.0, min(1.0, 0.25 + variation * 0.5)),
                },
                "transitions": {
                    "fillOut": {
                        "enabled": bool(fill_out_enabled),
                        "length": global_fill_policy["defaultLength"],
                        "family": "auto",
                        "aggression": max(0.0, min(1.0, 0.35 + energy * 0.55)),
                    },
                    "pickupIntoNext": {
                        "enabled": bool(energy >= 0.72 and variation >= 0.55),
                        "type": "snare_pickup",
                    },
                },
                "timing": {
                    "timeFeel": time_feel,
                    "shuffleMode": "swing_8th" if time_feel in {"swing", "shuffle"} else "straight",
                    "humanizeAmount": max(0.0, min(1.0, humanize_amount)),
                },
            }
        )

    roadmap = {
        "version": API_VERSION,
        "styleGroup": style_group,
        "global": {
            "avgTempo": avg_tempo,
            "timeFeel": time_feel,
            "defaultSwing": max(0.0, min(1.0, swing_amount)),
            "crashPolicy": {"onSectionStart": True, "intensityThreshold": 0.55},
            "fillPolicy": global_fill_policy,
            "fillCrashPolicy": {"startCrashProb": 0.55, "endCrashProb": 0.35},
        },
        "sections": roadmap_sections,
    }

    return SongRoadmapResponse(
        ok=True,
        roadmap=roadmap,
        metadata={
            "backend": ACTIVE_BACKEND,
            "sections": len(roadmap_sections),
        },
    )

# ------------------------------------------------------------
# Debug explain endpoint
# ------------------------------------------------------------

@app.post("/v1/debug/explain")
def debug_explain(req: PerformanceSpecRequest):
    cfg = req.cfg or {}
    tempos = cfg.get("tempos") or [cfg.get("tempo", 120.0)]
    if not isinstance(tempos, list) or not tempos:
        tempos = [120.0]
    avg_tempo = float(sum(float(t) for t in tempos) / max(len(tempos), 1))
    style = cfg.get("style")
    complexity = float(cfg.get("complexity", 0.7))

    hreq = HumanizationRequest(tempo_bpm=avg_tempo, style=style, pattern_complexity=complexity)
    norm = _normalize_inputs(hreq.tempo_bpm, float(_style_to_int(hreq.style)), hreq.pattern_complexity)[0].tolist()
    hresp = humanization_params(hreq)

    return {
        "ok": True,
        "backend": ACTIVE_BACKEND,
        "cache_enabled": CACHE_ENABLED,
        "inputs": hreq.model_dump(),
        "normalized": {"tempo": norm[0], "style": norm[1], "complexity": norm[2]},
        "humanization": hresp.model_dump(),
        "torch_available": TORCH_AVAILABLE,
        "onnx_available": ONNX_AVAILABLE,
        "torch_loaded": TORCH_MODEL is not None,
        "onnx_loaded": ONNX_SESSION is not None,
        "device": TORCH_DEVICE,
    }
