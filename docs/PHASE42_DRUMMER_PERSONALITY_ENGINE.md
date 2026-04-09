# Phase 42: Drummer Personality Engine

Adds:
- personality profile extraction (aggressiveness, restraint, consistency/chaos, ghost style, kick drive)
- section-level personality planning
- runtime application of personality to phrase events

Why it matters:
- gives the drummer a stable behavioral character
- lets choruses feel more assertive, verses more restrained
- introduces signature habits that persist across generated parts

Integration:
- build personality profile from assimilated phrases + rollup
- call plan_personality_for_sections(...) after roadmap generation
- call apply_drummer_personality(...) after contour/narrative processing and before final render
