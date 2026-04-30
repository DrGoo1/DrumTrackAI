from __future__ import annotations

from typing import Optional


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
        if uri.startswith("http://") or uri.startswith("https://"):
            return uri
        if not uri.startswith("/"):
            uri = "/" + uri
        return uri
