
# Phase 36: Extended Rudiment Runtime Integration

This phase wires the extended rudiment library from Phase 35 into runtime planning.

Added:
- extended rudiment policy gating
- roadmap annotation with `extendedRudimentPlan`
- performance-spec phrase integration with `extendedRudimentApplied`

Intended integration points:
- call `annotate_song_roadmap_with_extended_rudiments(...)` after roadmap generation
- call `apply_extended_rudiments_to_phrases(...)` after phrase construction and before final render
