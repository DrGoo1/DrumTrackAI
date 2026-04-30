from __future__ import annotations

from typing import Any, Dict


def render_reanalyze_loop(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload or {})
    iterations = int(data.get("max_iterations") or 3)
    iterations = max(1, min(10, iterations))

    target = float(data.get("target_similarity_goal") or 0.85)
    source = float(data.get("source_similarity_initial") or 0.6)
    target_sim = float(data.get("target_similarity_initial") or 0.55)
    feasibility = float(data.get("human_feasibility_initial") or 0.8)
    groove_pres = float(data.get("groove_preservation_initial") or 0.7)

    history = []
    converged = False
    for i in range(iterations):
        gap = max(0.0, target - target_sim)
        step = min(0.12, gap * 0.65)
        target_sim = min(1.0, target_sim + step)
        source = max(0.0, source - (step * 0.35))
        feasibility = max(0.0, min(1.0, feasibility - (step * 0.08) + 0.01))
        groove_pres = max(0.0, min(1.0, groove_pres - (step * 0.10)))

        history.append(
            {
                "iteration": i + 1,
                "target_similarity_score": target_sim,
                "source_similarity_score": source,
                "human_feasibility_score": feasibility,
                "groove_preservation_score": groove_pres,
            }
        )
        if target_sim >= target and feasibility >= 0.7 and groove_pres >= 0.45:
            converged = True
            break

    return {
        "status": "converged" if converged else "max_iterations_reached",
        "iterations_run": len(history),
        "history": history,
        "final": history[-1] if history else {},
        "target_similarity_goal": target,
        "converged": converged,
    }
