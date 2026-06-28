from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse


class ArtifactUrlService:
    """Builds public URLs for stored artifacts.

    This bootstrap implementation returns the given storage URI as-is or
    prefixes with a leading slash for relative paths. Replace with S3/GCS
    resolver as needed.
    """

    def build_url(self, storage_uri: str) -> Optional[str]:
        if not storage_uri:
            return None
        uri = str(storage_uri).strip()
        if not uri:
            return None

        normalized = uri.replace("\\", "/")
        lower = normalized.lower()

        marker = "artifacts/calibration/"
        marker_index = lower.find(marker)
        if marker_index != -1:
            relative = normalized[marker_index + len(marker):].lstrip("/")
            return f"/static/calibration_artifacts/{relative}"

        if lower.startswith("http://") or lower.startswith("https://"):
            return normalized

        if normalized.startswith("/static/calibration_artifacts/"):
            return normalized

        parsed = urlparse(normalized)
        if parsed.scheme and parsed.scheme not in {"http", "https"}:
            return None

        if normalized.startswith("/"):
            return normalized
        return "/" + normalized.lstrip("/")
