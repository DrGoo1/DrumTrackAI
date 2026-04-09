
# Phase 37: Phrase Continuity + Variation Engine

This phase adds:
- short-term phrase continuity memory
- phrase similarity scoring against recent history
- automatic light/medium/strong variation when repetition becomes too high
- section-level continuity planning

Why it matters:
- helps the drummer "remember" what it just played
- supports repeat-then-vary behavior
- reduces robotic repetition across adjacent phrases

Intended integration points:
- call `continuity_plan_for_sections(...)` after roadmap generation
- call `apply_phrase_continuity_runtime(...)` after phrase selection and before final render
