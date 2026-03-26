import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class YouTubeCandidate:
    title: str
    url: str
    channel: str = ""
    duration_sec: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None


class LLMProposalClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_sec: float = 30.0,
    ):
        self.base_url = (base_url or os.getenv("DRUMTRACAI_OLLAMA_URL") or "http://localhost:11434").rstrip("/")
        self.model = (model or os.getenv("DRUMTRACAI_OLLAMA_MODEL") or "").strip()
        self.timeout_sec = float(timeout_sec)

    def is_configured(self) -> bool:
        return bool(self.model)

    def propose_signature_songs(
        self,
        drummer_name: str,
        youtube_results: List[Dict[str, Any]],
        n: int = 3,
        use_llm: bool = True,
    ) -> Tuple[List[YouTubeCandidate], Dict[str, Any]]:
        candidates = self._normalize_youtube_results(youtube_results)
        if not candidates:
            return [], {"method": "none", "reason": "no_candidates"}

        if use_llm and self.is_configured():
            try:
                return self._llm_pick_signature_songs(drummer_name, candidates, n=n)
            except Exception as e:
                logger.warning(f"LLM propose_signature_songs failed, falling back to heuristics: {e}")

        picked = self._heuristic_pick_signature_songs(drummer_name, candidates, n=n)
        return picked, {"method": "heuristic"}

    def propose_category_ids(
        self,
        drummer_name: str,
        chosen_titles: List[str],
        available_category_ids: List[str],
        use_llm: bool = True,
    ) -> Tuple[List[str], Dict[str, Any]]:
        # LLM category suggestion is optional and can be added later.
        # For now, do a lightweight keyword match against category ids.
        if not available_category_ids:
            return [], {"method": "none", "reason": "no_categories"}

        if use_llm and self.is_configured():
            try:
                return self._llm_pick_categories(drummer_name, chosen_titles, available_category_ids)
            except Exception as e:
                logger.warning(f"LLM propose_category_ids failed, falling back to heuristics: {e}")

        return self._heuristic_pick_categories(drummer_name, chosen_titles, available_category_ids), {"method": "heuristic"}

    # ------------------------
    # Internal helpers
    # ------------------------

    def _normalize_youtube_results(self, youtube_results: List[Dict[str, Any]]) -> List[YouTubeCandidate]:
        out: List[YouTubeCandidate] = []
        for r in youtube_results or []:
            if not isinstance(r, dict):
                continue
            title = str(r.get("title") or "").strip()
            url = str(r.get("url") or "").strip()
            if not url and r.get("id"):
                url = f"https://www.youtube.com/watch?v={r['id']}"
            if not title or not url:
                continue

            channel = str(r.get("channel") or r.get("uploader") or "").strip()
            dur = r.get("duration")
            duration_sec: Optional[int] = None
            try:
                if isinstance(dur, (int, float)):
                    duration_sec = int(dur)
            except Exception:
                duration_sec = None

            out.append(YouTubeCandidate(title=title, url=url, channel=channel, duration_sec=duration_sec, raw=r))
        return out

    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return json.loads(body)

    def _ollama_generate(self, prompt: str) -> str:
        if not self.model:
            raise RuntimeError("Ollama model not configured")

        try:
            res = self._post_json(
                "/api/generate",
                {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Ollama HTTP error: {e.code} {e.reason}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection error: {e}") from e

        txt = str(res.get("response") or "")
        return txt

    def _llm_pick_signature_songs(
        self, drummer_name: str, candidates: List[YouTubeCandidate], n: int
    ) -> Tuple[List[YouTubeCandidate], Dict[str, Any]]:
        # Provide a compact candidate list. We request strict JSON.
        items = []
        for i, c in enumerate(candidates[:30]):
            items.append(
                {
                    "idx": i,
                    "title": c.title,
                    "channel": c.channel,
                    "url": c.url,
                    "duration_sec": c.duration_sec,
                }
            )

        prompt = (
            "You are helping curate audio for drummer fingerprint analysis. "
            "Select the best studio-quality signature songs for the specified drummer. "
            "Avoid live recordings, covers, lessons, reactions, and drum-cam unless clearly official. "
            "Return STRICT JSON only with shape: {\"picked_idxs\": [int,...], \"reasons\": {\"<idx>\": \"...\"}}.\n\n"
            f"Drummer: {drummer_name}\n\nCandidates JSON:\n{json.dumps(items, ensure_ascii=False)}\n"
        )

        raw = self._ollama_generate(prompt)
        parsed = self._safe_parse_json(raw)
        picked_idxs = parsed.get("picked_idxs") if isinstance(parsed, dict) else None
        if not isinstance(picked_idxs, list):
            raise RuntimeError("LLM did not return picked_idxs")

        idxs: List[int] = []
        for x in picked_idxs:
            try:
                xi = int(x)
            except Exception:
                continue
            if 0 <= xi < len(candidates):
                idxs.append(xi)
        idxs = list(dict.fromkeys(idxs))[: max(1, int(n))]

        picked = [candidates[i] for i in idxs]
        if len(picked) < n:
            # Fill with heuristic remainder
            remainder = [c for c in self._heuristic_pick_signature_songs(drummer_name, candidates, n=30) if c.url not in {p.url for p in picked}]
            picked.extend(remainder[: (n - len(picked))])

        return picked[:n], {"method": "ollama", "raw": raw}

    def _llm_pick_categories(
        self, drummer_name: str, chosen_titles: List[str], available_category_ids: List[str]
    ) -> Tuple[List[str], Dict[str, Any]]:
        prompt = (
            "You are helping assign copyright-safe drummer archetype category_ids to an anonymized drummer fingerprint. "
            "Pick 1-4 category_ids from the provided list that best match the drummer and songs. "
            "Return STRICT JSON only: {\"category_ids\": [\"...\"]}.\n\n"
            f"Drummer: {drummer_name}\n"
            f"Songs: {json.dumps(chosen_titles, ensure_ascii=False)}\n"
            f"Available category_ids: {json.dumps(available_category_ids, ensure_ascii=False)}\n"
        )
        raw = self._ollama_generate(prompt)
        parsed = self._safe_parse_json(raw)
        cids = parsed.get("category_ids") if isinstance(parsed, dict) else None
        if not isinstance(cids, list):
            raise RuntimeError("LLM did not return category_ids")

        allowed = set(str(x) for x in available_category_ids)
        out: List[str] = []
        for x in cids:
            sx = str(x).strip()
            if sx in allowed:
                out.append(sx)
        out = list(dict.fromkeys(out))[:4]
        return out, {"method": "ollama", "raw": raw}

    def _safe_parse_json(self, text: str) -> Any:
        t = (text or "").strip()
        if not t:
            raise RuntimeError("Empty LLM response")

        # Some models wrap JSON in code fences.
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)

        try:
            return json.loads(t)
        except Exception:
            # Try to recover by extracting the first JSON object.
            m = re.search(r"\{[\s\S]*\}", t)
            if m:
                return json.loads(m.group(0))
            raise

    def _heuristic_pick_signature_songs(self, drummer_name: str, candidates: List[YouTubeCandidate], n: int) -> List[YouTubeCandidate]:
        drummer_l = drummer_name.lower().strip()

        # Positive and negative keywords.
        good = [
            "official", "audio", "album", "remaster", "topic", "studio", "hq", "high quality",
            "original",
        ]
        bad = [
            "drum cover", "cover", "lesson", "tutorial", "reaction", "live", "drum cam", "drumcam",
            "isolated drums", "track breakdown", "how to", "karaoke", "remix",
        ]

        def score(c: YouTubeCandidate) -> float:
            t = c.title.lower()
            s = 0.0
            if drummer_l and drummer_l in t:
                s += 1.5
            for kw in good:
                if kw in t:
                    s += 1.0
            for kw in bad:
                if kw in t:
                    s -= 2.0

            # Prefer 2-8 minutes if duration available
            if c.duration_sec is not None:
                if 120 <= c.duration_sec <= 480:
                    s += 0.5
                elif c.duration_sec < 60:
                    s -= 1.0
                elif c.duration_sec > 900:
                    s -= 0.5
            return s

        ranked = sorted(candidates, key=score, reverse=True)
        # de-dupe by URL
        out: List[YouTubeCandidate] = []
        seen = set()
        for c in ranked:
            if c.url in seen:
                continue
            seen.add(c.url)
            out.append(c)
            if len(out) >= n:
                break
        return out

    def _heuristic_pick_categories(
        self, drummer_name: str, chosen_titles: List[str], available_category_ids: List[str]
    ) -> List[str]:
        # Very lightweight mapping based on tokens.
        blob = " ".join([drummer_name] + (chosen_titles or [])).lower()

        scores: Dict[str, float] = {cid: 0.0 for cid in available_category_ids}

        def bump(cid: str, token: str, amount: float):
            if token in blob:
                scores[cid] += amount

        # Generic tokens to help categories like 'jazz', 'funk', 'metal', etc.
        for cid in available_category_ids:
            cid_l = cid.lower()
            for tok in re.split(r"[_\-]+", cid_l):
                if tok and tok in blob:
                    scores[cid] += 0.3

        # Common genre tokens
        for cid in available_category_ids:
            bump(cid, "jazz", 0.5)
            bump(cid, "funk", 0.5)
            bump(cid, "metal", 0.5)
            bump(cid, "latin", 0.5)
            bump(cid, "soul", 0.4)
            bump(cid, "fusion", 0.4)
            bump(cid, "progressive", 0.4)
            bump(cid, "prog", 0.2)

        ranked = sorted(available_category_ids, key=lambda c: scores.get(c, 0.0), reverse=True)
        # Pick those with positive score, else empty.
        picked = [c for c in ranked if scores.get(c, 0.0) > 0.0][:4]
        return picked
