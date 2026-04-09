
# Phase 38: Limb Interaction Model

This phase adds:
- limb load analysis
- interaction bias inference (timekeeper, ghost-to-kick relationship, busy-feet state)
- runtime phrase adjustment based on limb interaction
- section-level limb interaction planning

Why it matters:
- hands and feet now influence one another
- timekeeper choice can shift by drummer tendency and section
- busy kick work can simplify hand embellishment in a more realistic way

Intended integration points:
- build a limb interaction profile from assimilated phrase/event data
- call `plan_limb_interaction_for_sections(...)` after roadmap generation
- call `apply_limb_interaction_runtime(...)` after phrase construction and before final render
