from __future__ import annotations

import json
import math
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TAXONOMY_PATH = PROJECT_ROOT / "admin" / "data" / "knowledge_sources" / "coaching_taxonomy.json"
DEFAULT_KNOWLEDGE_CORPUS = PROJECT_ROOT / "llm_training_project" / "knowledge_corpus" / "knowledge_corpus.jsonl"


_CORPUS_CACHE: Dict[str, Any] = {
    "mtime": 0.0,
    "loaded_at": 0.0,
    "docs": [],
    "df": {},
    "n": 0,
}


def _tokenize(text: str) -> List[str]:
    t = str(text or "").lower()
    # Keep simple word tokens; avoid deps.
    return [x for x in re.split(r"[^a-z0-9_\-]+", t) if len(x) >= 3]


def _load_corpus(corpus_path: Path = DEFAULT_KNOWLEDGE_CORPUS) -> None:
    try:
        if not corpus_path.exists():
            _CORPUS_CACHE.update({"mtime": 0.0, "loaded_at": time.time(), "docs": [], "df": {}, "n": 0})
            return
        mtime = float(corpus_path.stat().st_mtime)
        if _CORPUS_CACHE.get("mtime", 0.0) == mtime and _CORPUS_CACHE.get("docs"):
            return

        docs: List[Dict[str, Any]] = []
        df: Dict[str, int] = {}
        n = 0

        with corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = (line or "").strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                text = str(obj.get("text") or "")
                if not text.strip():
                    continue
                tokens = _tokenize(text)
                if not tokens:
                    continue
                n += 1
                seen = set(tokens)
                for tok in seen:
                    df[tok] = int(df.get(tok, 0)) + 1
                docs.append({
                    "doc_id": obj.get("doc_id"),
                    "chunk_id": obj.get("chunk_id"),
                    "text": text,
                    "tags": obj.get("tags") or [],
                    "source": obj.get("source") or obj.get("source_ref") or obj.get("sourceRef") or {},
                    "_tokens": tokens,
                })

        _CORPUS_CACHE.update({"mtime": mtime, "loaded_at": time.time(), "docs": docs, "df": df, "n": n})
    except Exception:
        _CORPUS_CACHE.update({"mtime": 0.0, "loaded_at": time.time(), "docs": [], "df": {}, "n": 0})


def _search_knowledge(query: str, *, top_k: int = 4, corpus_path: Path = DEFAULT_KNOWLEDGE_CORPUS) -> List[Dict[str, Any]]:
    _load_corpus(corpus_path)
    docs = _CORPUS_CACHE.get("docs") or []
    df = _CORPUS_CACHE.get("df") or {}
    n = int(_CORPUS_CACHE.get("n") or 0)
    if not docs or n <= 0:
        return []

    q_tokens = _tokenize(query)
    if not q_tokens:
        return []

    # Compute query tf-idf vector
    q_tf: Dict[str, int] = {}
    for t in q_tokens:
        q_tf[t] = int(q_tf.get(t, 0)) + 1

    def idf(tok: str) -> float:
        # Smooth idf
        dfi = float(df.get(tok, 0) or 0.0)
        return math.log((n + 1.0) / (dfi + 1.0)) + 1.0

    q_vec: Dict[str, float] = {t: float(c) * idf(t) for t, c in q_tf.items()}
    q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

    scored: List[Dict[str, Any]] = []
    for d in docs:
        toks = d.get("_tokens") or []
        if not toks:
            continue
        d_tf: Dict[str, int] = {}
        for t in toks:
            if t in q_vec:
                d_tf[t] = int(d_tf.get(t, 0)) + 1
        if not d_tf:
            continue
        d_vec: Dict[str, float] = {t: float(c) * idf(t) for t, c in d_tf.items()}
        d_norm = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0
        dot = 0.0
        for t, qv in q_vec.items():
            dv = d_vec.get(t)
            if dv is not None:
                dot += qv * dv
        score = dot / (q_norm * d_norm)
        if score <= 0:
            continue
        scored.append({
            "score": float(score),
            "doc_id": d.get("doc_id"),
            "chunk_id": d.get("chunk_id"),
            "tags": d.get("tags") or [],
            "source": d.get("source") or {},
            "text": d.get("text") or "",
        })

    scored.sort(key=lambda x: float(x.get("score") or 0.0), reverse=True)
    return scored[: max(0, int(top_k))]


def knowledge_search(*, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """Lightweight local retrieval against the ingested knowledge corpus."""
    try:
        return _search_knowledge(str(query or ""), top_k=int(top_k))
    except Exception:
        return []


@dataclass
class KnobSuggestion:
    path: str
    direction: str
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "direction": self.direction,
            "reason": self.reason,
        }


@dataclass
class CoachSuggestion:
    id: str
    label: str
    description: str
    tags: List[str]
    knob_suggestions: List[KnobSuggestion]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "tags": list(self.tags),
            "knob_suggestions": [k.to_dict() for k in self.knob_suggestions],
        }


def _load_taxonomy(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"version": 0, "goals_sound_first": [], "goals_technique_first": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _as_knob_suggestions(items: Any) -> List[KnobSuggestion]:
    out: List[KnobSuggestion] = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        out.append(
            KnobSuggestion(
                path=str(it.get("path") or "").strip(),
                direction=str(it.get("direction") or "").strip(),
                reason=str(it.get("reason") or "").strip(),
            )
        )
    return [k for k in out if k.path and k.direction]


def list_available_goals(taxonomy_path: Path = DEFAULT_TAXONOMY_PATH) -> Dict[str, List[Dict[str, Any]]]:
    data = _load_taxonomy(taxonomy_path)

    def _strip_goal(g: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": g.get("id"),
            "label": g.get("label"),
            "tags": g.get("tags") or [],
            "description": g.get("description"),
        }

    return {
        "sound_first": [_strip_goal(g) for g in (data.get("goals_sound_first") or []) if isinstance(g, dict)],
        "technique_first": [_strip_goal(g) for g in (data.get("goals_technique_first") or []) if isinstance(g, dict)],
    }


def generate_suggestions(
    *,
    goal_ids: Optional[List[str]] = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
    max_suggestions: int = 3,
) -> List[CoachSuggestion]:
    data = _load_taxonomy(taxonomy_path)
    goal_set = {str(g).strip() for g in (goal_ids or []) if str(g).strip()}

    all_goals: List[Dict[str, Any]] = []
    all_goals.extend([g for g in (data.get("goals_sound_first") or []) if isinstance(g, dict)])
    all_goals.extend([g for g in (data.get("goals_technique_first") or []) if isinstance(g, dict)])

    picked: List[Dict[str, Any]] = []
    if goal_set:
        for g in all_goals:
            if str(g.get("id") or "").strip() in goal_set:
                picked.append(g)
    else:
        # Default: pick the first few sound-first goals
        picked = [g for g in (data.get("goals_sound_first") or []) if isinstance(g, dict)][: max(0, int(max_suggestions))]

    out: List[CoachSuggestion] = []
    for g in picked[: max(0, int(max_suggestions))]:
        out.append(
            CoachSuggestion(
                id=str(g.get("id") or ""),
                label=str(g.get("label") or g.get("id") or ""),
                description=str(g.get("description") or ""),
                tags=list(g.get("tags") or []),
                knob_suggestions=_as_knob_suggestions(g.get("suggested_knobs")),
            )
        )
    return [s for s in out if s.id]


def apply_config_patch(*, base_config: Dict[str, Any], config_patch: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a coach config_patch to a DrumGenerationConfig-like dict.

    Patch format is a nested dict where leaf nodes are:
      {"op":"add","delta":<float>,"clamp":[min,max]}

    This function is intentionally permissive and fail-soft.
    """

    def _clamp(v: float, clamp_range: Any) -> float:
        try:
            if isinstance(clamp_range, (list, tuple)) and len(clamp_range) == 2:
                lo = float(clamp_range[0])
                hi = float(clamp_range[1])
                if lo > hi:
                    lo, hi = hi, lo
                return max(lo, min(hi, v))
        except Exception:
            pass
        return v

    def _apply_leaf(current_value: Any, patch_leaf: Dict[str, Any]) -> Any:
        op = str(patch_leaf.get("op") or "").strip().lower()
        if op != "add":
            return current_value
        try:
            delta = float(patch_leaf.get("delta") or 0.0)
        except Exception:
            delta = 0.0

        try:
            base_num = float(current_value)
        except Exception:
            base_num = 0.0

        out_num = base_num + delta
        out_num = _clamp(out_num, patch_leaf.get("clamp"))
        return out_num

    def _recurse_apply(cfg_node: Any, patch_node: Any) -> Any:
        if isinstance(patch_node, dict) and "op" in patch_node and "delta" in patch_node:
            return _apply_leaf(cfg_node, patch_node)

        if isinstance(patch_node, dict):
            out_node: Dict[str, Any] = {}
            if isinstance(cfg_node, dict):
                out_node.update(cfg_node)
            for k, v in patch_node.items():
                out_node[k] = _recurse_apply(out_node.get(k), v)
            return out_node

        # Unknown patch shape, ignore
        return cfg_node

    base: Dict[str, Any] = dict(base_config or {})
    patch: Dict[str, Any] = dict(config_patch or {})
    return _recurse_apply(base, patch)


def build_groove_coach_response(
    *,
    job_id: Optional[str] = None,
    section_id: Optional[str] = None,
    section_label: Optional[str] = None,
    goals: Optional[List[str]] = None,
    current_config: Optional[Dict[str, Any]] = None,
    taxonomy_path: Path = DEFAULT_TAXONOMY_PATH,
) -> Dict[str, Any]:
    # v1: deterministic placeholder scores until we wire in real groove analysis.
    # Keep these stable so the UI doesn't flicker.
    timing_score = 0.78
    velocity_score = 0.74
    humanization_score = 0.76
    overall_score = (timing_score + velocity_score + humanization_score) / 3.0

    inferred_goals: Optional[List[str]] = None
    if not goals:
        label = str(section_label or "").strip().lower()
        if label:
            if "chorus" in label:
                inferred_goals = ["more_energy_bigger_chorus"]
            elif "verse" in label:
                inferred_goals = ["less_busy_more_space"]
            elif "bridge" in label or "break" in label:
                inferred_goals = ["tight_and_punchy"]
            elif "intro" in label or "outro" in label:
                inferred_goals = ["tight_and_punchy"]

    suggestions = generate_suggestions(goal_ids=(goals or inferred_goals), taxonomy_path=taxonomy_path, max_suggestions=3)

    # Knowledge retrieval query: section context + selected goals + tags.
    q_parts: List[str] = []
    if section_label:
        q_parts.append(str(section_label))
    for gid in (goals or inferred_goals or []):
        q_parts.append(str(gid))
    for s in suggestions:
        q_parts.append(str(s.label))
        for t in (s.tags or []):
            q_parts.append(str(t))
    knowledge_query = " ".join([x for x in q_parts if x]).strip()
    citations = _search_knowledge(knowledge_query, top_k=4)

    config_patch: Dict[str, Any] = {}

    def _get_path(root: Any, path: str) -> Any:
        cur = root
        for p in [x for x in str(path or "").split(".") if x]:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(p)
        return cur

    def _clamp(v: float, clamp_range: Any) -> float:
        try:
            if isinstance(clamp_range, (list, tuple)) and len(clamp_range) == 2:
                lo = float(clamp_range[0])
                hi = float(clamp_range[1])
                if lo > hi:
                    lo, hi = hi, lo
                return max(lo, min(hi, v))
        except Exception:
            pass
        return v

    def _direction_to_delta(d: str) -> float:
        key = str(d or "").strip().lower()
        mapping = {
            "slight_up": 0.07,
            "up": 0.15,
            "slight_down": -0.07,
            "down": -0.15,
        }
        return float(mapping.get(key, 0.0))

    def _set_path(root: Dict[str, Any], path: str, value: Any) -> None:
        parts = [p for p in str(path or "").split(".") if p]
        if not parts:
            return
        cur: Dict[str, Any] = root
        for p in parts[:-1]:
            nxt = cur.get(p)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[p] = nxt
            cur = nxt
        cur[parts[-1]] = value

    for s in suggestions:
        for k in s.knob_suggestions:
            delta = _direction_to_delta(k.direction)
            if delta == 0.0:
                continue

            leaf = {
                "op": "add",
                "delta": float(delta),
                "clamp": [0.0, 1.0],
                "reason": k.reason,
            }

            # If we know current values, reduce/omit deltas that would clamp out.
            if isinstance(current_config, dict):
                cur_v = _get_path(current_config, k.path)
                try:
                    cur_num = float(cur_v)
                except Exception:
                    cur_num = None
                if cur_num is not None:
                    target = _clamp(cur_num + float(delta), leaf.get("clamp"))
                    eff_delta = target - cur_num
                    if abs(eff_delta) < 1e-9:
                        continue
                    leaf["delta"] = float(eff_delta)

            _set_path(
                config_patch,
                k.path,
                leaf,
            )

    return {
        "job_id": job_id,
        "section_id": section_id,
        "section_label": section_label,
        "goals": goals or inferred_goals or [],
        "suggestions": [s.to_dict() for s in suggestions],
        "scores": {
            "timing": timing_score,
            "velocity": velocity_score,
            "humanization": humanization_score,
            "overall": overall_score,
        },
        "config_patch": config_patch,
        "citations": citations,
    }
