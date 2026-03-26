import json
from pathlib import Path
from typing import Dict, Any, Optional


class ArticulationMapper:
    """Load per-plugin articulation maps and classify MIDI -> articulationId.

    Map format examples live in config/articulation_maps/ (e.g. superior_drummer3.json).
    """

    def __init__(self, map_path: str | Path) -> None:
        self.map_path = Path(map_path)
        self.map: Dict[str, Any] = json.loads(self.map_path.read_text(encoding="utf-8"))
        self.articulations: Dict[str, Any] = self.map.get("articulations", {})

    def all_articulations(self) -> Dict[str, Any]:
        return self.articulations

    def get_articulation(self, articulation_id: str) -> Optional[Dict[str, Any]]:
        return self.articulations.get(articulation_id)

    def classify_from_midi(self, pitch: int, cc_state: Dict[int, int]) -> Optional[str]:
        """Given MIDI pitch and current CC values, pick the best articulationId.

        Scoring heuristic:
        - +1 if note matches
        - + up to +1 for CC closeness per CC definition
        """
        best_id: Optional[str] = None
        best_score: float = -1.0

        for art_id, art in self.articulations.items():
            score = 0.0

            # Note-based match
            art_note = art.get("note")
            if art_note is not None and art_note == pitch:
                score += 1.0

            # CC-based match
            for cc_spec in art.get("cc", []):
                cc_num = cc_spec.get("controller")
                target_val = cc_spec.get("value")
                if cc_num is None or target_val is None:
                    continue
                cur_val = cc_state.get(cc_num)
                if cur_val is not None:
                    diff = abs(cur_val - target_val)
                    # Reward close match (within ~32 units)
                    score += max(0.0, 1.0 - diff / 32.0)

            if score > best_score:
                best_score = score
                best_id = art_id

        return best_id
