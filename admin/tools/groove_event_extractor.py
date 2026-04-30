from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any

import numpy as np
import soundfile as sf

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class GrooveConfig:
    """Configuration for the groove analyzer.

    This is intentionally self-contained so it can be used both from
    ad-hoc CLI tools and from admin analysis scripts.
    """

    bpm: float
    time_signature: Tuple[int, int] = (4, 4)  # (numerator, denominator)
    subdivisions_per_beat: int = 4  # 4=16ths, 3=triplet 8ths, 2=8ths, etc.
    sr_target: int = 44100

    # Instrument label set used by classifier
    instrument_labels: Optional[List[str]] = None

    # Onset detection parameters
    onset_backtrack: bool = True
    onset_pre_max: int = 3
    onset_post_max: int = 3
    onset_pre_avg: int = 5
    onset_post_avg: int = 5
    onset_delta: float = 0.1
    onset_wait: int = 2

    # Hit snippet window (seconds, relative to onset)
    snippet_pre_sec: float = 0.03
    snippet_post_sec: float = 0.20

    # CNN input spectrogram parameters
    n_mels: int = 64
    fmin: float = 30.0
    fmax: float = 16000.0
    hop_length: int = 256
    win_length: int = 1024

    # Velocity range mapping (0–127)
    velocity_min_db: float = -40.0
    velocity_max_db: float = 0.0

    def __post_init__(self) -> None:
        if self.instrument_labels is None:
            self.instrument_labels = [
                "kick",
                "snare",
                "hat_closed",
                "hat_open",
                "ride",
                "crash",
                "tom1",
                "tom2",
                "tom3",
                "perc_other",
            ]


@dataclass
class GrooveEvent:
    """Per-hit symbolic representation of a drum event."""

    time_sec: float

    bar: int
    beat: int
    subdivision: int  # 0..(subdivisions_per_beat-1) within the beat

    timing_offset_ms: float  # positive = late, negative = early

    instrument: str
    velocity: int  # 0–127

    # Optional / future fields
    limb: Optional[str] = None

    # Raw / debug
    extra: Optional[Dict[str, Any]] = None


class DrumHitCNN(nn.Module):
    """Simple CNN for classifying individual drum hits from log-mel spectrograms.

    Input: (B, 1, n_mels, T)
    Output: (B, n_classes)
    """

    def __init__(self, n_mels: int, n_classes: int) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(1, 16, kernel_size=(3, 3), padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=(3, 3), padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=(3, 3), padding=1)
        self.bn3 = nn.BatchNorm2d(64)

        self.pool = nn.MaxPool2d((2, 2))

        # We'll infer temporal dimension at runtime via adaptive pooling
        self.fc1 = nn.Linear(64 * (n_mels // 8) * 8, 128)
        self.fc2 = nn.Linear(128, n_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
        # x: (B, 1, n_mels, T)
        x = self.pool(F.relu(self.bn1(self.conv1(x))))  # (B,16,n_mels/2,T/2)
        x = self.pool(F.relu(self.bn2(self.conv2(x))))  # (B,32,n_mels/4,T/4)
        x = self.pool(F.relu(self.bn3(self.conv3(x))))  # (B,64,n_mels/8,T/8)

        # If temporal dimension is not 8, adapt:
        b, c, f, t = x.shape
        if t != 8:
            x = F.adaptive_max_pool2d(x, (f, 8))  # (B,64,n_mels/8,8)

        x = x.reshape(b, -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


class DrumClassifier:
    """Wraps a CNN-based classifier with a DSP heuristic fallback.

    If model_checkpoint is provided and loadable, uses the CNN.
    Otherwise, falls back to a simple spectral heuristic.
    """

    def __init__(
        self,
        config: GrooveConfig,
        model_checkpoint: Optional[str] = None,
        device: str = "cpu",
    ) -> None:
        self.config = config
        self.device = device
        self.labels = config.instrument_labels

        self.model: Optional[nn.Module] = None
        self.uses_cnn = False

        if model_checkpoint is not None:
            try:
                state = torch.load(model_checkpoint, map_location=device)
                n_classes = len(self.labels)
                self.model = DrumHitCNN(config.n_mels, n_classes)
                self.model.load_state_dict(state["model_state_dict"])
                self.model.to(device)
                self.model.eval()
                self.uses_cnn = True
                print(f"[DrumClassifier] Loaded CNN checkpoint from {model_checkpoint}")
            except Exception as e:  # pragma: no cover - defensive
                print(f"[DrumClassifier] Failed to load checkpoint: {e}")
                print("[DrumClassifier] Falling back to DSP heuristic.")
                self.model = None
                self.uses_cnn = False

    def classify_snippet(
        self, snippet: np.ndarray, sr: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Classify a single hit snippet.

        Returns (instrument_label, extra_info).
        """
        if self.uses_cnn and self.model is not None:
            return self._classify_with_cnn(snippet, sr)
        else:
            return self._classify_with_heuristic(snippet, sr)

    # --- CNN path -----------------------------------------------------

    def _snippet_to_logmel_tensor(self, snippet: np.ndarray, sr: int) -> torch.Tensor:
        cfg = self.config

        S = librosa.feature.melspectrogram(
            y=snippet,
            sr=sr,
            n_fft=cfg.win_length,
            hop_length=cfg.hop_length,
            n_mels=cfg.n_mels,
            fmin=cfg.fmin,
            fmax=cfg.fmax,
            power=2.0,
        )
        S_db = librosa.power_to_db(S, ref=np.max)

        S_norm = (S_db - np.mean(S_db)) / (np.std(S_db) + 1e-8)

        x = torch.tensor(S_norm, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        return x.to(self.device)

    def _classify_with_cnn(
        self, snippet: np.ndarray, sr: int
    ) -> Tuple[str, Dict[str, Any]]:
        x = self._snippet_to_logmel_tensor(snippet, sr)
        with torch.no_grad():
            logits = self.model(x)  # type: ignore[arg-type]
            probs = F.softmax(logits, dim=-1).cpu().numpy()[0]

        idx = int(np.argmax(probs))
        label = self.labels[idx]
        extra = {"probs": probs.tolist(), "cnn_index": idx}
        return label, extra

    # --- DSP heuristic path ------------------------------------------

    def _classify_with_heuristic(
        self, snippet: np.ndarray, sr: int
    ) -> Tuple[str, Dict[str, Any]]:
        """Crude but surprisingly effective spectral heuristic classifier.

        Separates kick/snare/hats/cymbals/toms based on centroid and band energy.
        """
        n_fft = 2048
        win = np.hanning(min(len(snippet), n_fft))
        if len(snippet) < n_fft:
            padded = np.zeros(n_fft)
            padded[: len(snippet)] = snippet * win[: len(snippet)]
        else:
            padded = snippet[:n_fft] * win

        spectrum = np.fft.rfft(padded)
        mag = np.abs(spectrum) + 1e-10

        freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)

        centroid = float(np.sum(freqs * mag) / np.sum(mag))

        def band_energy(f_lo: float, f_hi: float) -> float:
            mask = (freqs >= f_lo) & (freqs < f_hi)
            return float(np.sum(mag[mask]))

        low = band_energy(20, 150)
        low_mid = band_energy(150, 500)
        mid = band_energy(500, 3000)
        high = band_energy(3000, 12000)

        total = low + low_mid + mid + high + 1e-10
        low_r = low / total
        low_mid_r = low_mid / total
        mid_r = mid / total
        high_r = high / total

        if low_r > 0.45 and centroid < 200:
            label = "kick"
        elif high_r > 0.45 and centroid > 5000:
            label = "hat_closed" if low_mid_r < 0.15 else "crash"
        elif mid_r > 0.35 and centroid < 2500:
            label = "snare"
        elif low_mid_r > 0.35 and centroid < 800:
            label = "tom1"
        else:
            label = "hat_closed" if high_r > 0.3 else "perc_other"

        extra = {
            "centroid_hz": centroid,
            "band_ratios": {
                "low": low_r,
                "low_mid": low_mid_r,
                "mid": mid_r,
                "high": high_r,
            },
        }
        return label, extra


class GrooveAnalyzer:
    """End-to-end event extractor: audio -> list[GrooveEvent]."""

    def __init__(
        self,
        config: GrooveConfig,
        model_checkpoint: Optional[str] = None,
        device: str = "cpu",
    ) -> None:
        self.config = config
        self.classifier = DrumClassifier(config, model_checkpoint, device=device)

    def process_audio(self, path: str) -> List[GrooveEvent]:
        """High level entry point: audio file -> list of events."""
        y, sr = self._load_audio(path)
        onset_times = self._detect_onsets(y, sr)

        events: List[GrooveEvent] = []
        for t_onset in onset_times:
            snippet = self._extract_snippet(y, sr, t_onset)
            velocity = self._estimate_velocity(snippet)
            instrument, extra_cls = self.classifier.classify_snippet(snippet, sr)
            bar, beat, sub, offset_ms = self._quantize_time(t_onset)

            events.append(
                GrooveEvent(
                    time_sec=float(t_onset),
                    bar=bar,
                    beat=beat,
                    subdivision=sub,
                    timing_offset_ms=float(offset_ms),
                    instrument=instrument,
                    velocity=int(velocity),
                    limb=None,
                    extra={"cls": extra_cls},
                )
            )

        return events

    # --- Audio loading & onset detection ------------------------------

    def _load_audio(self, path: str):
        """Load audio file as mono float32 numpy array using soundfile only.

        This avoids librosa/numba/soxr dependency issues by relying on
        soundfile + numpy directly. We do not resample; if the input sample
        rate differs from the configured rate we log a warning and proceed.
        """
        import soundfile as sf

        # always_2d=True -> shape (n_samples, n_channels)
        y, sr = sf.read(path, always_2d=True)
        y = y.astype("float32")

        # Convert to mono by averaging channels
        if y.ndim == 2 and y.shape[1] > 1:
            y = np.mean(y, axis=1)
        else:
            y = y.reshape(-1)

        # Use a safe default target rate if config has no sample_rate field
        target_sr = getattr(self.config, "sample_rate", sr)
        if sr != target_sr:
            print(
                f"WARNING: sample rate {sr} != target {target_sr}; proceeding without resample"
            )

        peak = np.max(np.abs(y)) + 1e-10
        y = (y / peak).astype(np.float32)
        return y, sr

    def _detect_onsets(self, y: np.ndarray, sr: int) -> np.ndarray:
        """Very simple onset detector using amplitude envelope.

        This deliberately avoids librosa to keep dependencies light and
        compatible with the current environment.
        """
        cfg = self.config

        # Rectified, smoothed energy envelope
        frame_size = int(0.01 * sr)  # 10ms
        if frame_size <= 0:
            frame_size = 1

        # Compute moving average of absolute signal
        abs_y = np.abs(y)
        kernel = np.ones(frame_size, dtype=np.float32) / frame_size
        env = np.convolve(abs_y, kernel, mode="same")

        # First-order difference of the envelope
        diff = np.diff(env, prepend=env[0])

        # Threshold: mean + N * std of positive diffs
        pos_diff = diff[diff > 0]
        if len(pos_diff) == 0:
            return np.zeros(0, dtype=np.float32)

        thresh = float(np.mean(pos_diff) + 2.0 * np.std(pos_diff))
        candidate_idx = np.where(diff > thresh)[0]

        # Non-maximum suppression within a small window to avoid duplicates
        if len(candidate_idx) == 0:
            return np.zeros(0, dtype=np.float32)

        window = int(0.03 * sr)  # 30ms
        if window <= 0:
            window = 1

        onsets = []
        last_onset = -window
        for idx in candidate_idx:
            if idx - last_onset < window:
                # Too close to previous onset; keep the stronger one
                if env[idx] > env[last_onset]:
                    if onsets:
                        onsets[-1] = idx
                continue
            onsets.append(idx)
            last_onset = idx

        onset_times = np.array(onsets, dtype=np.float32) / float(sr)
        return onset_times

    # --- Per-hit processing -------------------------------------------

    def _extract_snippet(self, y: np.ndarray, sr: int, t_onset: float) -> np.ndarray:
        cfg = self.config
        pre = int(cfg.snippet_pre_sec * sr)
        post = int(cfg.snippet_post_sec * sr)

        center = int(t_onset * sr)
        start = max(center - pre, 0)
        end = min(center + post, len(y))

        return y[start:end].copy()

    def _estimate_velocity(self, snippet: np.ndarray) -> int:
        cfg = self.config

        peak = np.max(np.abs(snippet)) + 1e-10
        db = 20 * np.log10(peak)
        db = float(np.clip(db, cfg.velocity_min_db, cfg.velocity_max_db))

        norm = (db - cfg.velocity_min_db) / (cfg.velocity_max_db - cfg.velocity_min_db)
        vel = int(round(norm * 127))
        return int(np.clip(vel, 1, 127))

    # --- Quantization & microtiming ----------------------------------

    def _quantize_time(self, t: float) -> Tuple[int, int, int, float]:
        """Quantize time (sec) to bar/beat/subdivision based on BPM & meter."""
        cfg = self.config
        beats_per_bar = cfg.time_signature[0]
        tick_dur = 60.0 / (cfg.bpm * cfg.subdivisions_per_beat)

        tick_index = int(round(t / tick_dur))
        t_grid = tick_index * tick_dur
        offset_ms = (t - t_grid) * 1000.0

        ticks_per_bar = beats_per_bar * cfg.subdivisions_per_beat

        bar_index = tick_index // ticks_per_bar
        tick_in_bar = tick_index % ticks_per_bar

        beat_index = tick_in_bar // cfg.subdivisions_per_beat
        sub_index = tick_in_bar % cfg.subdivisions_per_beat

        bar = bar_index + 1
        beat = beat_index + 1
        subdivision = sub_index

        return bar, beat, subdivision, offset_ms


if __name__ == "__main__":  # pragma: no cover - manual CLI usage
    import argparse
    from pprint import pprint

    parser = argparse.ArgumentParser(description="Extract drum events from an isolated drum audio file.")
    parser.add_argument("audio_path", type=str, help="Path to audio file")
    parser.add_argument("--bpm", type=float, required=True, help="Approx BPM")
    parser.add_argument("--time_sig", type=str, default="4/4", help="Time signature, e.g. 4/4")
    parser.add_argument(
        "--subdivisions_per_beat",
        type=int,
        default=4,
        help="Subdivisions per beat (4=16ths, 3=triplets, 2=8ths, etc.)",
    )
    parser.add_argument("--checkpoint", type=str, default=None, help="Optional DrumHitCNN checkpoint path")
    args = parser.parse_args()

    num, den = args.time_sig.split("/")
    time_sig = (int(num), int(den))

    cfg = GrooveConfig(
        bpm=args.bpm,
        time_signature=time_sig,
        subdivisions_per_beat=args.subdivisions_per_beat,
    )
    analyzer = GrooveAnalyzer(cfg, model_checkpoint=args.checkpoint)
    evts = analyzer.process_audio(args.audio_path)

    print(f"Extracted {len(evts)} events.")
    for e in evts[:32]:
        pprint(e)
