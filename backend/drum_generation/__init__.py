"""
Drum Generation Module
=====================
Complete drum track generation with three-layer architecture.
"""

from .drum_generation_config import (
    DrumGenerationConfig,
    GenerationMode,
    BuildScope,
    GuideInstrument,
    GlobalFeel,
    GridEvent,
)

from .llm_performance_spec import (
    build_llm_prompt_for_performance,
    get_performance_spec_from_llm,
    build_default_performance_spec,
    build_flat_performance_spec,
)

__all__ = [
    "DrumGenerationConfig",
    "GenerationMode",
    "BuildScope",
    "GuideInstrument",
    "GlobalFeel",
    "GridEvent",
    "build_llm_prompt_for_performance",
    "get_performance_spec_from_llm",
    "build_default_performance_spec",
    "build_flat_performance_spec",
]
