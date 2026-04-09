
# Phase 34: Rudiment Runtime Integration

This phase wires rudiment-aware generation into runtime planning.

Added:
- section-aware rudiment injection policy
- roadmap annotation with `rudimentPlan`
- performance-spec phrase integration with `rudimentApplied`

Intended integration points:
- call `annotate_song_roadmap_with_rudiments(...)` after building section roadmap
- call `apply_rudiments_to_phrases(...)` after phrase construction / before final render payload
