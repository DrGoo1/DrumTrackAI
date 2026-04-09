# Phase 40: Dynamic Contour Modeling

Adds:
- phrase-level dynamic shaping (swell toward phrase end)
- section-aware targets (verse steady, bridge build, chorus lift)
- profile-driven mean/peak targets

Integration:
- build profile from assimilated phrases
- call plan_dynamic_contour_for_sections(...) after roadmap
- call apply_dynamic_contour(...) before final render
