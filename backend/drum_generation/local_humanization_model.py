import os
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except Exception:
    torch = None
    nn = None
    TORCH_AVAILABLE = False


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
        encoded = self.encoder(x)
        return self.predictor(encoded)


_STYLE_TO_INT = {
    "rock": 0,
    "funk": 1,
    "jazz": 2,
    "latin": 3,
    "metal": 4,
    "pop": 5,
    "live_recording": 6,
}


def _style_to_int(style: Optional[str]) -> int:
    key = str(style or "rock").strip().lower()
    return int(_STYLE_TO_INT.get(key, 0))


class LocalHumanizationModel:
    def __init__(self, model_path: Path, device: Optional[str] = None):
        if not TORCH_AVAILABLE:
            raise RuntimeError("torch is not available; cannot load local humanization model")

        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Local humanization model not found: {self.model_path}")

        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = DrumHumanizationModel(input_size=3, output_size=9).to(self.device)
        checkpoint = torch.load(self.model_path, map_location=self.device)
        state = checkpoint.get("model_state_dict") if isinstance(checkpoint, dict) else None
        if not isinstance(state, dict):
            raise RuntimeError(f"Unsupported checkpoint format in {self.model_path}")
        self.model.load_state_dict(state)
        self.model.eval()

    def predict_params(self, tempo_bpm: float, style: Optional[str], pattern_complexity: float) -> Dict[str, float]:
        x = np.array([[float(tempo_bpm), float(_style_to_int(style)), float(pattern_complexity)]], dtype=np.float32)
        with torch.no_grad():
            xt = torch.from_numpy(x).to(self.device)
            y = self.model(xt).detach().cpu().numpy()[0]

        keys = [
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
        return {k: float(y[i]) for i, k in enumerate(keys)}


_cached_model: Optional[LocalHumanizationModel] = None


def get_local_humanization_model() -> LocalHumanizationModel:
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    project_root = Path(__file__).resolve().parents[2]
    default_path = project_root / "admin" / "models" / "checkpoints" / "best_model.pth"
    model_path = Path(os.getenv("LOCAL_HUMANIZATION_MODEL_PATH", str(default_path)))
    device = os.getenv("LOCAL_HUMANIZATION_DEVICE")
    _cached_model = LocalHumanizationModel(model_path=model_path, device=device)
    return _cached_model
