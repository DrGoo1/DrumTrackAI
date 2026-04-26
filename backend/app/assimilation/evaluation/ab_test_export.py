from __future__ import annotations

from typing import Any, Dict, List


def export_ab_test_rows(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for idx, item in enumerate(items or []):
        if not isinstance(item, dict):
            continue
        ab = item.get("ab_mapping") if isinstance(item.get("ab_mapping"), dict) else {}
        judgment = item.get("judgment") if isinstance(item.get("judgment"), dict) else {}
        scores = item.get("scores") if isinstance(item.get("scores"), dict) else {}

        rows.append(
            {
                "row_index": idx,
                "item_id": item.get("item_id"),
                "session_id": item.get("session_id"),
                "target_drummer_slug": item.get("target_drummer_slug"),
                "base_groove_id": item.get("base_groove_id"),
                "baseline_run_id": item.get("baseline_run_id"),
                "candidate_a_run_id": ab.get("A") or item.get("candidate_a_run_id"),
                "candidate_b_run_id": ab.get("B") or item.get("candidate_b_run_id"),
                "preferred_candidate": judgment.get("preferred_candidate"),
                "closer_to_target": judgment.get("closer_to_target"),
                "better_feel": judgment.get("better_feel"),
                "more_musical": judgment.get("more_musical"),
                "confidence": judgment.get("confidence"),
                "source_similarity_score": scores.get("source_similarity_score"),
                "target_similarity_score": scores.get("target_similarity_score"),
                "human_feasibility_score": scores.get("human_feasibility_score"),
                "groove_preservation_score": scores.get("groove_preservation_score"),
            }
        )
    return rows
