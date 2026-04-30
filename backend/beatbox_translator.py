from __future__ import annotations

import dataclasses
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import librosa
import numpy as np

from .render_to_plugin_midi import render_articulated_notes_to_midi


@dataclasses.dataclass(frozen=True)
class BeatboxTranslationOptions:
    swing: float = 0.0
    quantization: str = "1/16"
    confidence_threshold: float = 0.35
    plugin: str = "jamstix"


@dataclasses.dataclass(frozen=True)
class BeatHit:
    time: float
    beat_position: float
    instrument: str
    velocity: int
    confidence: float


_QUANTIZATION_DIVISIONS: Dict[str, int] = {
    "1/4": 1,
    "1/8": 2,
    "1/12": 3,
    "1/16": 4,
    "1/32": 8,
}

_INSTRUMENT_PITCHES: Dict[str, int] = {
    "kick": 36,
    "snare": 38,
    "hihat": 42,
    "perc": 39,
}


def translate_beatbox(
    audio_path: Path,
    options: BeatboxTranslationOptions | None = None,
) -> Dict[str, object]:
    """Translate a beatbox audio file into structured drum hits.

    The implementation favors robustness over perfection so that the endpoint
    can return useful data even before the Rust audio-core path is in place.
    """

    if options is None:
        options = BeatboxTranslationOptions()

    if not audio_path.exists():
        raise FileNotFoundError(audio_path)

    y, sr = librosa.load(audio_path, sr=44100)  # Standardize sample rate
    if not np.any(y):
        raise ValueError("Audio stream is empty")

    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    if not math.isfinite(tempo) or tempo <= 0:
        tempo = 100.0

    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, units="frames", backtrack=False)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    if onset_times.size == 0:
        return {
            "tempo": tempo,
            "hits": [],
            "summary": {},
            "preview_midi": None,
        }

    stft = np.abs(librosa.stft(y=y, n_fft=2048, hop_length=512))
    centroid = librosa.feature.spectral_centroid(S=stft, sr=sr)
    rms = librosa.feature.rms(S=stft)
    zcr = librosa.feature.zero_crossing_rate(y=y)

    rms_max = float(np.max(rms)) or 1e-6

    hits: List[BeatHit] = []
    for frame, t_sec in zip(onset_frames, onset_times):
        frame_idx = min(int(frame), centroid.shape[1] - 1)
        feat_centroid = float(centroid[0, frame_idx])
        feat_rms = float(rms[0, min(frame_idx, rms.shape[1] - 1)])
        feat_zcr = float(zcr[0, min(frame_idx, zcr.shape[1] - 1)])

        instrument, confidence = _classify_hit(
            centroid_hz=feat_centroid,
            rms_value=feat_rms,
            rms_max=rms_max,
            zcr_value=feat_zcr,
        )
        if confidence < options.confidence_threshold:
            continue

        beat_position = _quantize_time(
            t_sec,
            tempo=tempo,
            quantization=options.quantization,
            swing=options.swing,
        )
        velocity = int(np.clip((feat_rms / rms_max) * 110 + 15, 30, 127))

        hits.append(
            BeatHit(
                time=float(t_sec),
                beat_position=beat_position,
                instrument=instrument,
                velocity=velocity,
                confidence=confidence,
            )
        )

    midi_blob = _hits_to_midi(hits, tempo=tempo, plugin=options.plugin)

    summary: Dict[str, int] = {}
    for hit in hits:
        summary[hit.instrument] = summary.get(hit.instrument, 0) + 1

    return {
        "tempo": tempo,
        "hits": [dataclasses.asdict(h) for h in hits],
        "summary": summary,
        "preview_midi": midi_blob["midi_base64"],
        "plugin": midi_blob["plugin"],
        "ticks_per_beat": midi_blob["ticks_per_beat"],
    }


def taps_to_translation(
    hits_payload: Iterable[Dict[str, object]],
    *,
    tempo: float,
    plugin: str = "jamstix",
) -> Dict[str, object]:
    """Convert frontend tap hits into the same structure as translate_beatbox."""

    normalized_hits: List[BeatHit] = []
    for raw in hits_payload:
        instrument = str(raw.get("instrument") or "snare").strip().lower()
        if instrument not in _INSTRUMENT_PITCHES:
            instrument = {
                "kick": "kick",
                "bd": "kick",
                "sn": "snare",
                "rim": "snare",
                "hh": "hihat",
                "hat": "hihat",
                "perc": "perc",
            }.get(instrument, "snare")

        beat_position = float(raw.get("beat_position") or raw.get("beats") or 0.0)
        time_value = float(raw.get("time") or beat_position * 60.0 / max(tempo, 1e-6))
        velocity = int(raw.get("velocity") or 96)
        confidence = float(raw.get("confidence") or 1.0)

        normalized_hits.append(
            BeatHit(
                time=time_value,
                beat_position=beat_position,
                instrument=instrument,
                velocity=max(1, min(127, velocity)),
                confidence=max(0.0, min(1.0, confidence)),
            )
        )

    midi_blob = _hits_to_midi(normalized_hits, tempo=tempo, plugin=plugin)

    summary: Dict[str, int] = {}
    for hit in normalized_hits:
        summary[hit.instrument] = summary.get(hit.instrument, 0) + 1

    return {
        "tempo": tempo,
        "hits": [dataclasses.asdict(h) for h in normalized_hits],
        "summary": summary,
        "preview_midi": midi_blob["midi_base64"],
        "plugin": midi_blob["plugin"],
        "ticks_per_beat": midi_blob["ticks_per_beat"],
    }


def _classify_hit(
    *,
    centroid_hz: float,
    rms_value: float,
    rms_max: float,
    zcr_value: float,
) -> Tuple[str, float]:
    centroid = max(centroid_hz, 1.0)
    loudness = min(1.0, (rms_value / (rms_max or 1e-6)))
    centroid_norm = min(1.0, centroid / 6000.0)

    if centroid < 1400:
        instrument = "kick"
        centroid_score = 1.0 - centroid / 1400.0
    elif centroid < 3200:
        instrument = "snare"
        centroid_score = 1.0 - abs(centroid - 2200.0) / 2200.0
    else:
        instrument = "hihat"
        centroid_score = centroid_norm

    zcr_score = min(1.0, zcr_value * 10.0)
    confidence = float(
        max(0.0, 0.5 * centroid_score + 0.3 * loudness + 0.2 * zcr_score)
    )

    if instrument == "hihat" and zcr_score < 0.25:
        instrument = "perc"

    return instrument, min(1.0, confidence)


def _quantize_time(time_sec: float, tempo: float, quantization: str, swing: float) -> float:
    tempo = tempo if tempo > 0 else 100.0
    divisions = _QUANTIZATION_DIVISIONS.get(quantization, 4)
    seconds_per_beat = 60.0 / tempo
    step = seconds_per_beat / divisions
    approx_idx = int(round(time_sec / step))
    quantized_time = approx_idx * step

    if swing and divisions % 2 == 0 and approx_idx % 2 == 1:
        swing = np.clip(swing, -0.5, 0.5)
        quantized_time += swing * step

    beat_position = quantized_time / seconds_per_beat
    return beat_position


def _hits_to_midi(hits: Iterable[BeatHit], tempo: float, plugin: str) -> Dict[str, object]:
    ppq = 480
    notes = []
    for hit in hits:
        pitch = _INSTRUMENT_PITCHES.get(hit.instrument, 38)
        tick = int(round(hit.beat_position * ppq))
        duration = max(ppq // 8, 30)
        notes.append(
            {
                "t0": tick,
                "t1": tick + duration,
                "pitch": pitch,
                "vel": hit.velocity,
                "chan": 9,
                "articulationId": None,
            }
        )

    payload = {
        "plugin": plugin,
        "ppq": ppq,
        "notes": notes,
    }
    return render_articulated_notes_to_midi(payload)
