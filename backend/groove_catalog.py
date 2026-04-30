from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass
class GrooveCard:
    id: str
    title: str
    source: str
    tags: List[str]
    preview_png: Optional[str]
    extracted_dir: Optional[str]
    default_role: str
    actions: List[str]
    phrase_id: Optional[int] = None
    basename: Optional[str] = None
    style_group: Optional[str] = None
    style_detail: Optional[str] = None
    tempo_bpm: Optional[float] = None
    meter: Optional[str] = None
    bars: Optional[int] = None
    midi_path: Optional[str] = None
    audio_path: Optional[str] = None

    complexity_score: Optional[float] = None
    hits_per_bar: Optional[float] = None
    active_instruments: Optional[int] = None
    offbeat_ratio: Optional[float] = None
    snare_backbeat_ratio: Optional[float] = None

    kick_share: Optional[float] = None
    snare_share: Optional[float] = None
    kick_snare_share: Optional[float] = None
    cymbal_share: Optional[float] = None
    tom_share: Optional[float] = None

    kick_hits_per_bar: Optional[float] = None
    snare_hits_per_bar: Optional[float] = None
    hat_hits_per_bar: Optional[float] = None
    ride_tip_hits_per_bar: Optional[float] = None
    ride_bell_hits_per_bar: Optional[float] = None

    complexity_tier: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "source": self.source,
            "tags": self.tags,
            "preview_png": self.preview_png,
            "extracted_dir": self.extracted_dir,
            "default_role": self.default_role,
            "actions": self.actions,
            "phrase_id": self.phrase_id,
            "basename": self.basename,
            "style_group": self.style_group,
            "style_detail": self.style_detail,
            "tempo_bpm": self.tempo_bpm,
            "meter": self.meter,
            "bars": self.bars,
            "midi_path": self.midi_path,
            "audio_path": self.audio_path,
            "complexity_score": self.complexity_score,
            "hits_per_bar": self.hits_per_bar,
            "active_instruments": self.active_instruments,
            "offbeat_ratio": self.offbeat_ratio,
            "snare_backbeat_ratio": self.snare_backbeat_ratio,
            "kick_share": self.kick_share,
            "snare_share": self.snare_share,
            "kick_snare_share": self.kick_snare_share,
            "cymbal_share": self.cymbal_share,
            "tom_share": self.tom_share,

            "kick_hits_per_bar": self.kick_hits_per_bar,
            "snare_hits_per_bar": self.snare_hits_per_bar,
            "hat_hits_per_bar": self.hat_hits_per_bar,
            "ride_tip_hits_per_bar": self.ride_tip_hits_per_bar,
            "ride_bell_hits_per_bar": self.ride_bell_hits_per_bar,
            "complexity_tier": self.complexity_tier,
            "has_midi": bool(self.midi_path),
            "has_audio": bool(self.audio_path),
        }


class GrooveCatalog:
    def __init__(self, manifest_jsonl_path: Path | Sequence[Path]):
        if isinstance(manifest_jsonl_path, (list, tuple)):
            self.manifest_jsonl_paths = [Path(p) for p in manifest_jsonl_path]
        else:
            self.manifest_jsonl_paths = [Path(manifest_jsonl_path)]
        self._loaded_at: float = 0.0
        self._mtimes: Dict[str, float] = {}
        self._entries: List[Dict[str, Any]] = []

        self._complexity_cache_path: Path = Path(__file__).resolve().parent / "cache" / "egmd_complexity_cache.json"
        self._complexity_cache: Dict[str, Any] = {}
        self._complexity_cache_loaded: bool = False
        self._complexity_cache_dirty: bool = False

        self._manifest_base_dirs: List[Path] = []
        for p in self.manifest_jsonl_paths:
            try:
                self._manifest_base_dirs.append(Path(p).resolve().parent)
            except Exception:
                continue

    def _resolve_media_path(self, p: str) -> Optional[Path]:
        raw = str(p or "").strip()
        if not raw:
            return None
        try:
            cand = Path(raw)
        except Exception:
            return None

        try:
            if cand.exists():
                return cand.resolve()
        except Exception:
            pass

        # Try relative to known bases.
        bases: List[Path] = []
        try:
            bases.extend(self._manifest_base_dirs)
        except Exception:
            pass
        try:
            bases.append(Path(__file__).resolve().parents[1])
        except Exception:
            pass
        try:
            bases.append(Path(__file__).resolve().parents[2])
        except Exception:
            pass
        try:
            bases.append(Path.cwd())
        except Exception:
            pass

        for b in bases:
            try:
                c2 = (b / cand).resolve()
                if c2.exists():
                    return c2
            except Exception:
                continue
        return None

    def _maybe_load_complexity_cache(self) -> None:
        if self._complexity_cache_loaded:
            return
        self._complexity_cache_loaded = True
        self._complexity_cache = {}
        self._complexity_cache_dirty = False

        try:
            p = self._complexity_cache_path
            if not p.exists():
                return
            raw = p.read_text(encoding="utf-8")
            if not raw.strip():
                return
            obj = json.loads(raw)
            if isinstance(obj, dict):
                self._complexity_cache = obj
        except Exception:
            self._complexity_cache = {}

    @staticmethod
    def _complexity_tier_from_metrics(metrics: Dict[str, Any] | None) -> Optional[str]:
        if not isinstance(metrics, dict):
            return None
        try:
            cs = metrics.get("complexity_score")
            if cs is None:
                return None
            v = float(cs)
        except Exception:
            return None

        # Default global thresholds.
        # simple: <= 0.40
        # intermediate: <= 0.65
        # complex: > 0.65
        try:
            if v <= 0.40:
                return "simple"
            if v <= 0.65:
                return "intermediate"
            return "complex"
        except Exception:
            return None

    @staticmethod
    def _percentile(values: Sequence[float], p: float) -> Optional[float]:
        try:
            vals = [float(x) for x in values if x is not None and isinstance(x, (int, float))]
            if not vals:
                return None
            vals.sort()
            pp = max(0.0, min(1.0, float(p)))
            if len(vals) == 1:
                return float(vals[0])
            idx = pp * (len(vals) - 1)
            lo = int(idx)
            hi = min(len(vals) - 1, lo + 1)
            frac = float(idx - lo)
            return float(vals[lo] * (1.0 - frac) + vals[hi] * frac)
        except Exception:
            return None

    def _maybe_flush_complexity_cache(self) -> None:
        if not self._complexity_cache_dirty:
            return
        try:
            p = self._complexity_cache_path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(self._complexity_cache, ensure_ascii=False), encoding="utf-8")
            self._complexity_cache_dirty = False
        except Exception:
            # Best-effort cache; ignore failures.
            pass

    @staticmethod
    def _egmd_inst_group(midi_pitch: int) -> str:
        # Light-weight GM drum grouping; sufficient for complexity metrics.
        p = int(midi_pitch)
        if p in (35, 36):
            return "kick"
        if p in (38, 40, 37):
            return "snare"
        if p in (42, 44, 46):
            return "hat"
        if p in (51, 59):
            return "ride_tip"
        if p in (53,):
            return "ride_bell"
        if p in (41, 43, 45, 47, 48, 50):
            return "tom"
        if p in (49, 57):
            return "cymbal"
        if p in (52, 55):
            return "cymbal"
        return "other"

    def _compute_egmd_complexity(
        self,
        *,
        midi_path: str,
        bars: int,
        beats_per_bar: int,
    ) -> Optional[Dict[str, Any]]:
        try:
            import mido
        except Exception:
            return None

        mp = self._resolve_media_path(midi_path)
        if mp is None:
            return None

        try:
            mid = mido.MidiFile(str(mp))
        except Exception:
            return None

        tpb = int(getattr(mid, "ticks_per_beat", 480) or 480)
        total_hits = 0
        offbeat_hits = 0
        snare_hits = 0
        snare_backbeat_hits = 0
        inst_used: Set[str] = set()
        grp_hits: Dict[str, int] = {}

        # Interpret timing in beats (not seconds) so it's independent of embedded MIDI tempo.
        for track in mid.tracks:
            abs_ticks = 0
            for msg in track:
                try:
                    abs_ticks += int(getattr(msg, "time", 0) or 0)
                except Exception:
                    pass
                if msg.type != "note_on" or not getattr(msg, "velocity", 0):
                    continue
                if getattr(msg, "channel", None) != 9:
                    continue

                pitch = int(getattr(msg, "note", 0) or 0)
                grp = self._egmd_inst_group(pitch)
                inst_used.add(grp)
                total_hits += 1
                grp_hits[grp] = int(grp_hits.get(grp, 0)) + 1

                beats = float(abs_ticks) / float(max(tpb, 1))
                beat_in_bar = beats % float(max(beats_per_bar, 1))

                # On-beat if close to an integer beat (quarter notes). Otherwise offbeat.
                nearest_q = round(beat_in_bar)
                if abs(beat_in_bar - nearest_q) > 0.12:
                    offbeat_hits += 1

                if grp == "snare":
                    snare_hits += 1
                    # Backbeat in 4/4: beats 2 and 4 (0-indexed 1 and 3)
                    if beats_per_bar >= 4:
                        if abs(beat_in_bar - 1.0) <= 0.12 or abs(beat_in_bar - 3.0) <= 0.12:
                            snare_backbeat_hits += 1

        if total_hits <= 0:
            return None

        bars_safe = max(1, int(bars or 1))
        hits_per_bar = float(total_hits) / float(bars_safe)
        active_instruments = len([x for x in inst_used if x not in {"other"}])
        offbeat_ratio = float(offbeat_hits) / float(max(total_hits, 1))
        snare_backbeat_ratio = float(snare_backbeat_hits) / float(max(snare_hits, 1)) if snare_hits > 0 else 0.0

        kick_hits = int(grp_hits.get("kick", 0))
        sn_hits = int(grp_hits.get("snare", 0))
        hat_hits = int(grp_hits.get("hat", 0))
        ride_tip_hits = int(grp_hits.get("ride_tip", 0))
        ride_bell_hits = int(grp_hits.get("ride_bell", 0))
        cym_hits = int(grp_hits.get("cymbal", 0))
        tom_hits = int(grp_hits.get("tom", 0))

        kick_share = float(kick_hits) / float(max(total_hits, 1))
        snare_share = float(sn_hits) / float(max(total_hits, 1))
        kick_snare_share = float(kick_hits + sn_hits) / float(max(total_hits, 1))
        cymbal_share = float(hat_hits + ride_tip_hits + ride_bell_hits + cym_hits) / float(max(total_hits, 1))
        tom_share = float(tom_hits) / float(max(total_hits, 1))

        # Normalize coarse components into ~0..1 ranges.
        hits_norm = max(0.0, min(1.0, hits_per_bar / 16.0))
        inst_norm = max(0.0, min(1.0, float(active_instruments) / 5.0))
        complexity_score = max(
            0.0,
            min(
                1.0,
                0.50 * hits_norm + 0.30 * offbeat_ratio + 0.20 * inst_norm,
            ),
        )

        return {
            "complexity_score": float(complexity_score),
            "hits_per_bar": float(hits_per_bar),
            "active_instruments": int(active_instruments),
            "offbeat_ratio": float(offbeat_ratio),
            "snare_backbeat_ratio": float(snare_backbeat_ratio),
            "kick_share": float(kick_share),
            "snare_share": float(snare_share),
            "kick_snare_share": float(kick_snare_share),
            "cymbal_share": float(cymbal_share),
            "tom_share": float(tom_share),

            "kick_hits_per_bar": float(kick_hits) / float(bars_safe),
            "snare_hits_per_bar": float(sn_hits) / float(bars_safe),
            "hat_hits_per_bar": float(hat_hits) / float(bars_safe),
            "ride_tip_hits_per_bar": float(ride_tip_hits) / float(bars_safe),
            "ride_bell_hits_per_bar": float(ride_bell_hits) / float(bars_safe),
        }

    def _get_or_compute_egmd_complexity(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if str(entry.get("source") or "").strip().lower() != "egmd":
                return None
            midi_path = str(entry.get("midi_path") or "").strip()
            if not midi_path:
                return None
        except Exception:
            return None

        self._maybe_load_complexity_cache()

        mp = self._resolve_media_path(midi_path)
        try:
            mtime = float(mp.stat().st_mtime) if mp is not None else -1.0
        except Exception:
            mtime = -1.0

        cache_key = str(mp) if mp is not None else midi_path
        cached = self._complexity_cache.get(cache_key)
        if isinstance(cached, dict):
            try:
                if float(cached.get("mtime", -2.0)) == float(mtime) and isinstance(cached.get("metrics"), dict):
                    metrics = cached.get("metrics")
                    # If cache predates new metrics fields, recompute.
                    if not isinstance(metrics, dict):
                        metrics = None
                    else:
                        required = {
                            "kick_snare_share",
                            "cymbal_share",
                            "tom_share",
                            "kick_hits_per_bar",
                            "snare_hits_per_bar",
                            "hat_hits_per_bar",
                            "ride_tip_hits_per_bar",
                            "ride_bell_hits_per_bar",
                        }
                        if not required.issubset(set(metrics.keys())):
                            metrics = None
                    if metrics is not None:
                        return metrics
            except Exception:
                pass

        # Compute and persist.
        bars = self._safe_int(entry.get("bars")) or 1
        meter = str(entry.get("meter") or "4/4")
        beats_per_bar = 4
        try:
            beats_per_bar = int(str(meter).split("/", 1)[0] or 4)
        except Exception:
            beats_per_bar = 4

        metrics = self._compute_egmd_complexity(midi_path=str(mp) if mp is not None else midi_path, bars=bars, beats_per_bar=beats_per_bar)
        if not metrics:
            return None

        self._complexity_cache[cache_key] = {"mtime": float(mtime), "metrics": metrics}
        self._complexity_cache_dirty = True
        return metrics

    def _maybe_reload(self) -> None:
        mtimes_now: Dict[str, float] = {}
        for p in self.manifest_jsonl_paths:
            try:
                mtimes_now[str(p)] = p.stat().st_mtime
            except Exception:
                mtimes_now[str(p)] = -1.0

        if self._entries and mtimes_now == self._mtimes:
            return

        self._mtimes = mtimes_now
        self._loaded_at = time.time()
        self._entries = []

        for p in self.manifest_jsonl_paths:
            try:
                if not p.exists():
                    continue
                with p.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = (line or "").strip()
                        if not line:
                            continue
                        try:
                            self._entries.append(json.loads(line))
                        except Exception:
                            continue
            except Exception:
                continue

    @staticmethod
    def _normalize_tags(tags: Sequence[str] | None) -> Set[str]:
        return {str(t).strip().lower() for t in (tags or []) if str(t)}

    @staticmethod
    def _title_from_entry(groove_id: str, entry: Dict[str, Any]) -> str:
        source = str(entry.get("source") or "").strip().lower()
        if source == "egmd":
            style_group = str(entry.get("style_group") or "").strip()
            style_detail = str(entry.get("style_detail") or "").strip()
            groove_num: Optional[int] = None
            if "groove" in style_detail.lower():
                tail = style_detail.lower().split("groove", 1)[-1]
                digits = "".join(ch for ch in tail if ch.isdigit())
                if digits:
                    try:
                        groove_num = int(digits)
                    except Exception:
                        groove_num = None
            if groove_num is not None and style_group:
                return f"{style_group.title()} Groove {groove_num:02d}"
            if style_group:
                return f"{style_group.title()} Groove"
        if source == "dtk_standard":
            style_group = str(entry.get("style_group") or "").strip()
            basename = str(entry.get("basename") or "").strip()
            if style_group:
                return f"DTK {style_group.title()} Standard"
            if basename:
                s = basename.replace("_", " ").replace("-", " ")
                s = " ".join(w for w in s.split() if w)
                return f"DTK {s.title()}"
        s = str(groove_id or "").strip().replace("_", " ").replace("-", " ")
        s = " ".join(w for w in s.split() if w)
        return s.title() if s else groove_id

    @staticmethod
    def _derive_egmd_style_group(entry: Dict[str, Any]) -> Optional[str]:
        def _normalize_group(style_token: str) -> Optional[str]:
            s = str(style_token or "").strip().lower()
            if not s:
                return None
            # Remove common EGMD suffixes like 'soul-groove10' -> 'soul', 'rock-fill3' -> 'rock'.
            s = re.sub(r"-(?:groove|fill)\d*$", "", s)
            # Broad buckets used by the UI.
            if s.startswith("jazz") or "jazz" in s:
                return "jazz"
            if s.startswith("rock") or "rock" in s:
                return "rock"
            # Keep funk separate from jazz-funk (mapped above).
            if s == "funk" or s.startswith("funk") or "funk" in s:
                return "funk"
            if s.startswith("reggae") or "reggae" in s:
                return "reggae"
            if s.startswith("metal") or "metal" in s:
                return "metal"
            if s.startswith("blues") or "blues" in s:
                return "blues"
            if s.startswith("latin") or "afrocuban" in s or "brazil" in s or "baiao" in s:
                return "latin"
            if s.startswith("edm") or "edm" in s:
                return "edm"
            return s

        # Prefer explicit basename if present; otherwise derive from midi/audio filename stem.
        base = str(entry.get("basename") or "").strip().lower()
        if not base:
            mp = str(entry.get("midi_path") or "").strip()
            ap = str(entry.get("audio_path") or "").strip()
            fp = mp or ap
            if fp:
                try:
                    stem = os.path.splitext(os.path.basename(fp))[0]
                except Exception:
                    stem = fp
                base = str(stem or "").strip().lower()

        if not base:
            return None

        # Common EGMD naming: '<num>_<style>_<bpm>_<groove|fill>_...'
        m = re.match(r"^\d+_([^_]+)_\d+(?:\.\d+)?_(?:groove|fill)\b", base)
        if m:
            return _normalize_group(m.group(1))

        # Alternate EGMD naming: '<num>_<style>_<bpm>_beat_...'
        # Example: '10_country_114_beat_4-4_1'
        m_beat = re.match(r"^\d+_([^_]+)_\d+(?:\.\d+)?_beat\b", base)
        if m_beat:
            return _normalize_group(m_beat.group(1))

        # Older/alternate naming: '<style>-groove' or '<style>-fill' (hyphen form)
        m2 = re.search(r"(?:^|[_/\\])([a-z0-9]+)-(?:groove|fill)\b", base)
        if m2:
            return _normalize_group(m2.group(1))

        # As a fallback, map any token containing '-groove' (e.g. 'rock-groove8')
        m3 = re.match(r"^([a-z0-9]+)-groove", base)
        if m3:
            return _normalize_group(m3.group(1))

        return None

    @staticmethod
    def _default_role_for_source(source: str) -> str:
        src = str(source or "").strip().lower()
        if src in {"bangthedrumschool"}:
            return "fill"
        if src in {"rudiments"}:
            return "fill"
        if src in {"egmd"}:
            return "groove"
        if src in {"drum_patterns"}:
            return "groove"
        return "groove"

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        try:
            if value is None:
                return None
            s = str(value).strip()
            if not s:
                return None
            return int(float(s))
        except Exception:
            return None

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        try:
            if value is None:
                return None
            s = str(value).strip()
            if not s:
                return None
            return float(s)
        except Exception:
            return None

    def search(
        self,
        *,
        query: str | None = None,
        tags: Sequence[str] | None = None,
        sources: Sequence[str] | None = None,
        style_group: str | None = None,
        limit: int = 10,
    ) -> List[GrooveCard]:
        self._maybe_reload()

        q = str(query or "").strip().lower()
        want_tags = self._normalize_tags(tags)
        want_sources = {str(s).strip().lower() for s in (sources or []) if str(s).strip()}
        want_style_group = str(style_group or "").strip().lower() or None

        def score_entry(e: Dict[str, Any]) -> Tuple[int, int, int]:
            eid = str(e.get("id") or "")
            hay = " ".join(
                [
                    str(e.get("id") or ""),
                    str(e.get("pdf_stem") or ""),
                    " ".join(str(t) for t in (e.get("tags") or [])),
                ]
            ).lower()

            entry_tags = self._normalize_tags(e.get("tags") or [])

            tag_hits = len(want_tags.intersection(entry_tags)) if want_tags else 0
            q_hit = 1 if (q and q in hay) else 0
            prefix = 1 if (q and eid.lower().startswith(q)) else 0
            return (tag_hits, q_hit, prefix)

        scored: List[Tuple[Tuple[int, int, int], Dict[str, Any]]] = []
        for e in self._entries:
            if want_sources:
                src = str(e.get("source") or "").strip().lower()
                if src not in want_sources:
                    continue
            if want_style_group:
                src2 = str(e.get("source") or "").strip().lower()
                sg = str(e.get("style_group") or "").strip().lower()
                if (not sg) and src2 == "egmd":
                    try:
                        derived = self._derive_egmd_style_group(e)
                        sg = str(derived or "").strip().lower()
                    except Exception:
                        sg = ""
                if not sg or sg != want_style_group:
                    continue
            s = score_entry(e)
            if want_tags and s[0] <= 0:
                continue
            if q and s[1] <= 0 and s[2] <= 0:
                continue
            scored.append((s, e))

        scored.sort(key=lambda x: (x[0][0], x[0][2], x[0][1]), reverse=True)

        out: List[GrooveCard] = []
        for _, e in scored[: max(1, int(limit))]:
            gid = str(e.get("id") or "")
            source = str(e.get("source") or "unknown")
            default_role = self._default_role_for_source(source)
            title = self._title_from_entry(gid, e)
            phrase_id_value = e.get("phrase_id")
            if phrase_id_value is None or str(phrase_id_value).strip() == "":
                phrase_id_value = e.get("egmd_phrase_id")
            if phrase_id_value is None or str(phrase_id_value).strip() == "":
                phrase_id_value = e.get("phraseId")
            style_group_value = str(e.get("style_group") or "").strip() if e.get("style_group") else None
            if str(source).strip().lower() == "egmd":
                # Prefer the manifest-provided style_group; only derive as a fallback.
                derived = self._derive_egmd_style_group(e)
                if (not style_group_value) and derived:
                    style_group_value = derived

            complexity = self._get_or_compute_egmd_complexity(e)
            complexity_tier = self._complexity_tier_from_metrics(complexity)
            out.append(
                GrooveCard(
                    id=gid,
                    title=title,
                    source=source,
                    tags=[str(t) for t in (e.get("tags") or []) if str(t)],
                    preview_png=str(e.get("preview_png")) if e.get("preview_png") else None,
                    extracted_dir=str(e.get("extracted_dir")) if e.get("extracted_dir") else None,
                    default_role=default_role,
                    actions=["use_as_groove", "use_as_fill"],
                    phrase_id=self._safe_int(phrase_id_value),
                    basename=str(e.get("basename")) if e.get("basename") else None,
                    style_group=style_group_value,
                    style_detail=str(e.get("style_detail")) if e.get("style_detail") else None,
                    tempo_bpm=self._safe_float(e.get("tempo_bpm")),
                    meter=str(e.get("meter")) if e.get("meter") else None,
                    bars=self._safe_int(e.get("bars")),
                    midi_path=str(e.get("midi_path")) if e.get("midi_path") else None,
                    audio_path=str(e.get("audio_path")) if e.get("audio_path") else None,
                    complexity_score=(float(complexity.get("complexity_score")) if isinstance(complexity, dict) and complexity.get("complexity_score") is not None else None),
                    hits_per_bar=(float(complexity.get("hits_per_bar")) if isinstance(complexity, dict) and complexity.get("hits_per_bar") is not None else None),
                    active_instruments=(int(complexity.get("active_instruments")) if isinstance(complexity, dict) and complexity.get("active_instruments") is not None else None),
                    offbeat_ratio=(float(complexity.get("offbeat_ratio")) if isinstance(complexity, dict) and complexity.get("offbeat_ratio") is not None else None),
                    snare_backbeat_ratio=(float(complexity.get("snare_backbeat_ratio")) if isinstance(complexity, dict) and complexity.get("snare_backbeat_ratio") is not None else None),
                    kick_share=(float(complexity.get("kick_share")) if isinstance(complexity, dict) and complexity.get("kick_share") is not None else None),
                    snare_share=(float(complexity.get("snare_share")) if isinstance(complexity, dict) and complexity.get("snare_share") is not None else None),
                    kick_snare_share=(float(complexity.get("kick_snare_share")) if isinstance(complexity, dict) and complexity.get("kick_snare_share") is not None else None),
                    cymbal_share=(float(complexity.get("cymbal_share")) if isinstance(complexity, dict) and complexity.get("cymbal_share") is not None else None),
                    tom_share=(float(complexity.get("tom_share")) if isinstance(complexity, dict) and complexity.get("tom_share") is not None else None),

                    kick_hits_per_bar=(float(complexity.get("kick_hits_per_bar")) if isinstance(complexity, dict) and complexity.get("kick_hits_per_bar") is not None else None),
                    snare_hits_per_bar=(float(complexity.get("snare_hits_per_bar")) if isinstance(complexity, dict) and complexity.get("snare_hits_per_bar") is not None else None),
                    hat_hits_per_bar=(float(complexity.get("hat_hits_per_bar")) if isinstance(complexity, dict) and complexity.get("hat_hits_per_bar") is not None else None),
                    ride_tip_hits_per_bar=(float(complexity.get("ride_tip_hits_per_bar")) if isinstance(complexity, dict) and complexity.get("ride_tip_hits_per_bar") is not None else None),
                    ride_bell_hits_per_bar=(float(complexity.get("ride_bell_hits_per_bar")) if isinstance(complexity, dict) and complexity.get("ride_bell_hits_per_bar") is not None else None),
                    complexity_tier=complexity_tier,
                )
            )
        self._maybe_flush_complexity_cache()
        return out


    def list_style_groups(self, *, sources: Sequence[str] | None = None, limit: int = 200) -> List[str]:
        self._maybe_reload()
        want_sources = {str(s).strip().lower() for s in (sources or []) if str(s).strip()}
        groups: List[str] = []
        seen: Set[str] = set()

        for e in self._entries:
            if want_sources:
                src = str(e.get("source") or "").strip().lower()
                if src not in want_sources:
                    continue
            raw = str(e.get("style_group") or "").strip().lower()
            if not raw:
                src2 = str(e.get("source") or "").strip().lower()
                if src2 == "egmd":
                    try:
                        derived = self._derive_egmd_style_group(e)
                        raw = str(derived or "").strip().lower()
                    except Exception:
                        raw = ""
            if not raw:
                continue
            if raw in seen:
                continue
            seen.add(raw)
            groups.append(raw)
            if len(groups) >= max(1, int(limit)):
                break

        return groups

    def get_by_id(self, groove_id: str) -> Optional[GrooveCard]:
        self._maybe_reload()
        want = str(groove_id or "").strip()
        if not want:
            return None
        for e in self._entries:
            if str(e.get("id") or "") == want:
                gid = str(e.get("id") or "")
                source = str(e.get("source") or "unknown")
                default_role = self._default_role_for_source(source)
                title = self._title_from_entry(gid, e)
                phrase_id_value = e.get("phrase_id")
                if phrase_id_value is None or str(phrase_id_value).strip() == "":
                    phrase_id_value = e.get("egmd_phrase_id")
                if phrase_id_value is None or str(phrase_id_value).strip() == "":
                    phrase_id_value = e.get("phraseId")
                style_group_value = str(e.get("style_group") or "").strip() if e.get("style_group") else None
                if str(source).strip().lower() == "egmd":
                    # Prefer the manifest-provided style_group; only derive as a fallback.
                    derived = self._derive_egmd_style_group(e)
                    if (not style_group_value) and derived:
                        style_group_value = derived

                complexity = self._get_or_compute_egmd_complexity(e)
                complexity_tier = self._complexity_tier_from_metrics(complexity)
                return GrooveCard(
                    id=gid,
                    title=title,
                    source=source,
                    tags=[str(t) for t in (e.get("tags") or []) if str(t)],
                    preview_png=str(e.get("preview_png")) if e.get("preview_png") else None,
                    extracted_dir=str(e.get("extracted_dir")) if e.get("extracted_dir") else None,
                    default_role=default_role,
                    actions=["use_as_groove", "use_as_fill"],
                    phrase_id=self._safe_int(phrase_id_value),
                    basename=str(e.get("basename")) if e.get("basename") else None,
                    style_group=style_group_value,
                    style_detail=str(e.get("style_detail")) if e.get("style_detail") else None,
                    tempo_bpm=self._safe_float(e.get("tempo_bpm")),
                    meter=str(e.get("meter")) if e.get("meter") else None,
                    bars=self._safe_int(e.get("bars")),
                    midi_path=str(e.get("midi_path")) if e.get("midi_path") else None,
                    audio_path=str(e.get("audio_path")) if e.get("audio_path") else None,
                    complexity_score=(float(complexity.get("complexity_score")) if isinstance(complexity, dict) and complexity.get("complexity_score") is not None else None),
                    hits_per_bar=(float(complexity.get("hits_per_bar")) if isinstance(complexity, dict) and complexity.get("hits_per_bar") is not None else None),
                    active_instruments=(int(complexity.get("active_instruments")) if isinstance(complexity, dict) and complexity.get("active_instruments") is not None else None),
                    offbeat_ratio=(float(complexity.get("offbeat_ratio")) if isinstance(complexity, dict) and complexity.get("offbeat_ratio") is not None else None),
                    snare_backbeat_ratio=(float(complexity.get("snare_backbeat_ratio")) if isinstance(complexity, dict) and complexity.get("snare_backbeat_ratio") is not None else None),
                    kick_share=(float(complexity.get("kick_share")) if isinstance(complexity, dict) and complexity.get("kick_share") is not None else None),
                    snare_share=(float(complexity.get("snare_share")) if isinstance(complexity, dict) and complexity.get("snare_share") is not None else None),
                    kick_snare_share=(float(complexity.get("kick_snare_share")) if isinstance(complexity, dict) and complexity.get("kick_snare_share") is not None else None),
                    cymbal_share=(float(complexity.get("cymbal_share")) if isinstance(complexity, dict) and complexity.get("cymbal_share") is not None else None),
                    tom_share=(float(complexity.get("tom_share")) if isinstance(complexity, dict) and complexity.get("tom_share") is not None else None),
                    complexity_tier=complexity_tier,
                )
        self._maybe_flush_complexity_cache()
        return None

    def complexity_summary_by_style_group(
        self,
        *,
        sources: Sequence[str] | None = None,
        style_group: str | None = None,
        limit: int = 200,
        max_entries: int = 50000,
    ) -> Dict[str, Any]:
        self._maybe_reload()

        want_sources = {str(s).strip().lower() for s in (sources or []) if str(s).strip()}
        want_sg = str(style_group or "").strip().lower() or None

        counts: Dict[str, Dict[str, int]] = {}
        scores: Dict[str, List[float]] = {}
        total_by_sg: Dict[str, int] = {}

        scanned = 0
        for e in self._entries:
            if scanned >= max(1, int(max_entries)):
                break
            scanned += 1

            try:
                src = str(e.get("source") or "").strip().lower()
            except Exception:
                continue

            if want_sources:
                if src not in want_sources:
                    continue
            else:
                # Default to EGMD.
                if src != "egmd":
                    continue

            sg = str(e.get("style_group") or "").strip().lower()
            if not sg and src == "egmd":
                try:
                    derived = self._derive_egmd_style_group(e)
                    sg = str(derived or "").strip().lower()
                except Exception:
                    sg = ""
            if not sg:
                continue
            if want_sg and sg != want_sg:
                continue

            metrics = self._get_or_compute_egmd_complexity(e) if src == "egmd" else None
            tier = self._complexity_tier_from_metrics(metrics)
            if not tier:
                continue

            total_by_sg[sg] = int(total_by_sg.get(sg, 0)) + 1
            by_tier = counts.setdefault(sg, {"simple": 0, "intermediate": 0, "complex": 0})
            by_tier[tier] = int(by_tier.get(tier, 0)) + 1

            try:
                if isinstance(metrics, dict) and metrics.get("complexity_score") is not None:
                    scores.setdefault(sg, []).append(float(metrics.get("complexity_score")))
            except Exception:
                pass

        groups = sorted(total_by_sg.keys())
        groups = groups[: max(1, int(limit))]

        items: List[Dict[str, Any]] = []
        for sg in groups:
            by_tier = counts.get(sg) or {"simple": 0, "intermediate": 0, "complex": 0}
            total = int(total_by_sg.get(sg, 0))
            svals = scores.get(sg) or []
            items.append(
                {
                    "style_group": sg,
                    "count": total,
                    "tiers": {
                        "simple": int(by_tier.get("simple", 0)),
                        "intermediate": int(by_tier.get("intermediate", 0)),
                        "complex": int(by_tier.get("complex", 0)),
                    },
                    "complexity_score_p33": self._percentile(svals, 0.33),
                    "complexity_score_p66": self._percentile(svals, 0.66),
                    "complexity_score_min": min(svals) if svals else None,
                    "complexity_score_max": max(svals) if svals else None,
                }
            )

        self._maybe_flush_complexity_cache()
        return {
            "ok": True,
            "sources": list(want_sources) if want_sources else ["egmd"],
            "style_group": want_sg,
            "items": items,
        }
