from typing import Dict, List

def summarize_user_edits(edit_events: List[Dict]) -> Dict:
    summary = {
        "deleted_fills": 0,
        "velocity_reductions": 0,
        "velocity_increases": 0,
        "timing_loosen_requests": 0,
    }
    for e in edit_events or []:
        kind = e.get("type")
        if kind == "delete_fill":
            summary["deleted_fills"] += 1
        elif kind == "velocity_reduce":
            summary["velocity_reductions"] += 1
        elif kind == "velocity_increase":
            summary["velocity_increases"] += 1
        elif kind == "timing_loosen":
            summary["timing_loosen_requests"] += 1
    return summary

def adapt_profile_from_feedback(profile: Dict, edit_events: List[Dict]) -> Dict:
    out = dict(profile or {})
    s = summarize_user_edits(edit_events)

    if s["deleted_fills"] > 0:
        out["fills_per_min"] = max(0.0, float(out.get("fills_per_min", 1.0)) - 0.25 * s["deleted_fills"])

    if s["velocity_reductions"] > s["velocity_increases"]:
        out["targetVelocityScale"] = max(0.5, float(out.get("targetVelocityScale", 1.0)) - 0.1)

    if s["velocity_increases"] > s["velocity_reductions"]:
        out["targetVelocityScale"] = min(1.5, float(out.get("targetVelocityScale", 1.0)) + 0.1)

    if s["timing_loosen_requests"] > 0:
        out["humanizeAmount"] = min(1.0, float(out.get("humanizeAmount", 0.5)) + 0.1 * s["timing_loosen_requests"])

    out["adaptiveFeedbackSummary"] = s
    return out
