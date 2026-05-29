import argparse
import os
import sys
import uuid
from pathlib import Path
from typing import Iterable, Optional

from sqlalchemy import create_engine, text


_AUDIO_SUFFIXES = {
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
    ".aif",
    ".aiff",
    ".wma",
}
_NON_AUDIO_SUFFIXES = {
    ".json",
    ".txt",
    ".csv",
    ".xml",
    ".yaml",
    ".yml",
    ".md",
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".svg",
    ".mid",
    ".midi",
}


def _is_likely_audio_path(value: Optional[str]) -> bool:
    candidate = str(value or "").strip()
    if not candidate:
        return False
    suffix = Path(candidate).suffix.lower()
    if suffix in _AUDIO_SUFFIXES:
        return True
    if suffix in _NON_AUDIO_SUFFIXES:
        return False
    return True


def _is_cloud_uri(value: Optional[str]) -> bool:
    uri = str(value or "").strip().lower()
    return uri.startswith(("https://", "http://", "s3://", "supabase://", "gs://", "r2://"))


def _existing_local_file(value: Optional[str]) -> Optional[str]:
    candidate = str(value or "").strip()
    if not candidate:
        return None
    p = Path(candidate)
    if not (p.exists() and p.is_file()):
        return None
    return str(p) if _is_likely_audio_path(str(p)) else None


def _pick_local_source_path(conn, analysis_id: str) -> Optional[str]:
    row = conn.execute(
        text(
            """
            SELECT source_file
            FROM public.song_performance_analysis
            WHERE analysis_id = :analysis_id
            LIMIT 1
            """
        ),
        {"analysis_id": analysis_id},
    ).mappings().first()
    source_file = _existing_local_file(str((row or {}).get("source_file") or ""))
    if source_file:
        return source_file

    stem_rows = conn.execute(
        text(
            """
            SELECT stem_name, file_path
            FROM public.stem_artifacts
            WHERE analysis_id = :analysis_id
            ORDER BY created_at DESC
            """
        ),
        {"analysis_id": analysis_id},
    ).mappings().all()
    preferred_stems = ("drums", "drum", "mix", "master")
    for preferred in preferred_stems:
        for stem in stem_rows:
            stem_name = str(stem.get("stem_name") or "").strip().lower()
            if stem_name != preferred:
                continue
            local = _existing_local_file(stem.get("file_path"))
            if local:
                return local
    for stem in stem_rows:
        local = _existing_local_file(stem.get("file_path"))
        if local:
            return local

    artifact_rows = conn.execute(
        text(
            """
            SELECT artifact_role, file_path
            FROM public.analysis_artifacts
            WHERE analysis_id = :analysis_id
            ORDER BY created_at DESC
            """
        ),
        {"analysis_id": analysis_id},
    ).mappings().all()
    preferred_roles = ("source_audio", "source", "drums", "drum_mix", "mix")
    for role in preferred_roles:
        for artifact in artifact_rows:
            artifact_role = str(artifact.get("artifact_role") or "").strip().lower()
            if artifact_role != role:
                continue
            local = _existing_local_file(artifact.get("file_path"))
            if local:
                return local
    for artifact in artifact_rows:
        local = _existing_local_file(artifact.get("file_path"))
        if local:
            return local

    return None


def _pick_existing_cloud_audio_uri(conn, analysis_id: str) -> Optional[str]:
    stem_rows = conn.execute(
        text(
            """
            SELECT stem_name, file_path
            FROM public.stem_artifacts
            WHERE analysis_id = :analysis_id
            ORDER BY created_at DESC
            """
        ),
        {"analysis_id": analysis_id},
    ).mappings().all()
    preferred_stems = ("drums", "drum", "mix", "master")
    for preferred in preferred_stems:
        for stem in stem_rows:
            stem_name = str(stem.get("stem_name") or "").strip().lower()
            file_path = str(stem.get("file_path") or "").strip()
            if stem_name != preferred:
                continue
            if _is_cloud_uri(file_path) and _is_likely_audio_path(file_path):
                return file_path

    artifact_rows = conn.execute(
        text(
            """
            SELECT artifact_role, file_path
            FROM public.analysis_artifacts
            WHERE analysis_id = :analysis_id
            ORDER BY created_at DESC
            """
        ),
        {"analysis_id": analysis_id},
    ).mappings().all()
    preferred_roles = ("source_audio", "source", "drums", "drum_mix", "mix")
    for role in preferred_roles:
        for artifact in artifact_rows:
            artifact_role = str(artifact.get("artifact_role") or "").strip().lower()
            file_path = str(artifact.get("file_path") or "").strip()
            if artifact_role != role:
                continue
            if _is_cloud_uri(file_path) and _is_likely_audio_path(file_path):
                return file_path

    return None


def _iter_target_analyses(conn, drummer_slug: str, limit: int) -> Iterable[dict]:
    return conn.execute(
        text(
            """
            SELECT spa.analysis_id, spa.source_file, spa.created_at
            FROM public.song_performance_analysis spa
            LEFT JOIN public.drummers d ON CAST(d.id AS TEXT) = CAST(spa.drummer_id AS TEXT)
            WHERE CAST(spa.drummer_id AS TEXT) = CAST(:slug AS TEXT)
               OR CAST(COALESCE(d.drummer_id, '') AS TEXT) = CAST(:slug AS TEXT)
               OR LOWER(REPLACE(COALESCE(d.display_name, ''), ' ', '_')) = LOWER(CAST(:slug AS TEXT))
               OR LOWER(REPLACE(COALESCE(d.name, ''), ' ', '_')) = LOWER(CAST(:slug AS TEXT))
            ORDER BY spa.created_at DESC
            LIMIT :limit
            """
        ),
        {"slug": drummer_slug, "limit": int(limit)},
    ).mappings().all()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill cloud-readable source URIs for assimilation analyses")
    parser.add_argument("--drummer-slug", required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    database_url = str(os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    bucket = str(os.getenv("AWS_S3_BUCKET") or "").strip()
    region = str(os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "").strip()
    if not bucket or not region:
        raise SystemExit("AWS_S3_BUCKET and AWS_REGION (or AWS_DEFAULT_REGION) are required")

    try:
        import boto3  # type: ignore
    except Exception as exc:
        raise SystemExit(f"boto3 import failed: {exc}")

    s3 = boto3.client("s3", region_name=region)
    engine = create_engine(database_url)

    total = 0
    already_cloud = 0
    updated = 0
    missing_local = 0
    failures = 0

    with engine.begin() as conn:
        rows = list(_iter_target_analyses(conn, args.drummer_slug, args.limit))
        total = len(rows)
        print(f"Found {total} analyses for {args.drummer_slug}")

        for row in rows:
            analysis_id = str(row.get("analysis_id") or "").strip()
            existing_source = str(row.get("source_file") or "").strip()
            if not analysis_id:
                continue

            if _is_cloud_uri(existing_source) and _is_likely_audio_path(existing_source):
                already_cloud += 1
                continue

            existing_cloud_audio_uri = _pick_existing_cloud_audio_uri(conn, analysis_id)
            if existing_cloud_audio_uri:
                if args.dry_run:
                    print(f"DRYRUN {analysis_id}: existing cloud audio -> {existing_cloud_audio_uri}")
                    updated += 1
                    continue
                conn.execute(
                    text(
                        """
                        UPDATE public.song_performance_analysis
                        SET source_file = :source_file,
                            updated_at = NOW()
                        WHERE analysis_id = :analysis_id
                        """
                    ),
                    {"source_file": existing_cloud_audio_uri, "analysis_id": analysis_id},
                )
                updated += 1
                print(f"OK   {analysis_id}: {existing_cloud_audio_uri}")
                continue

            local_path = _pick_local_source_path(conn, analysis_id)
            if not local_path:
                missing_local += 1
                print(f"SKIP {analysis_id}: no local source path found")
                continue

            key = f"drummers/{args.drummer_slug}/assimilation/source/{analysis_id}/{Path(local_path).name}"
            s3_uri = f"s3://{bucket}/{key}"

            if args.dry_run:
                print(f"DRYRUN {analysis_id}: {local_path} -> {s3_uri}")
                updated += 1
                continue

            try:
                s3.upload_file(local_path, bucket, key)
                conn.execute(
                    text(
                        """
                        UPDATE public.song_performance_analysis
                        SET source_file = :source_file,
                            updated_at = NOW()
                        WHERE analysis_id = :analysis_id
                        """
                    ),
                    {"source_file": s3_uri, "analysis_id": analysis_id},
                )
                conn.execute(
                    text(
                        """
                        INSERT INTO public.analysis_artifacts (
                            artifact_id, analysis_id, drummer_id, song_id,
                            artifact_role, file_path, file_format,
                            extractor_name, extractor_version, created_at
                        )
                        SELECT
                            :artifact_id,
                            spa.analysis_id,
                            spa.drummer_id,
                            spa.song_id,
                            'source_audio',
                            :file_path,
                            :file_format,
                            'source_uri_backfill',
                            'v1',
                            NOW()
                        FROM public.song_performance_analysis spa
                        WHERE spa.analysis_id = :analysis_id
                        """
                    ),
                    {
                        "artifact_id": str(uuid.uuid4()),
                        "analysis_id": analysis_id,
                        "file_path": s3_uri,
                        "file_format": Path(local_path).suffix.lower().lstrip(".") or None,
                    },
                )
                updated += 1
                print(f"OK   {analysis_id}: {s3_uri}")
            except Exception as exc:
                failures += 1
                print(f"FAIL {analysis_id}: {exc}")

    print(
        "Summary: "
        f"total={total} already_cloud={already_cloud} updated={updated} "
        f"missing_local={missing_local} failures={failures}"
    )


if __name__ == "__main__":
    main()
