from __future__ import annotations

from typing import Any, Dict


class CalibrationPhase4SampleMixin:
    """Lightweight stub mixin used by CentralDatabaseService.

    This provides optional hooks for Phase 4 sampling-related helpers. The
    backend API can operate without concrete implementations; callers that rely
    on these should provide their own mixin in admin contexts.
    """

    # Placeholder methods to keep imports and multiple inheritance safely resolvable
    def phase4_prepare_sample(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - optional hook
        return {}

    def phase4_finalize_sample(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:  # pragma: no cover - optional hook
        return {}
