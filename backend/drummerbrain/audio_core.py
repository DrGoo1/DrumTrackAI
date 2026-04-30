import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def resolve_audio_core_bin() -> str:
    p = os.getenv("AUDIO_CORE_BIN")
    if p:
        return p
    repo_root = Path(__file__).resolve().parents[2]
    exe = repo_root / "target" / "release" / "audio-core.exe"
    if exe.exists():
        return str(exe)
    return "audio-core"


def analyze_full(*, audio_path: str) -> Dict[str, Any]:
    cmd = [resolve_audio_core_bin(), "analyze-full", audio_path]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "audio-core failed").strip())
    return json.loads(res.stdout or "{}")


def analyze(*, audio_path: str, min_bpm: float = 50.0, max_bpm: float = 200.0) -> Dict[str, Any]:
    cmd = [
        resolve_audio_core_bin(),
        "analyze",
        audio_path,
        "--min-bpm",
        str(float(min_bpm)),
        "--max-bpm",
        str(float(max_bpm)),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError((res.stderr or res.stdout or "audio-core failed").strip())
    return json.loads(res.stdout or "{}")
