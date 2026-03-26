import json
import tempfile
import unittest
from pathlib import Path


class TestDrummerBrainIngestTranscriptionArtifacts(unittest.TestCase):
    def test_ingest_transcription_artifacts_inserts_row(self):
        from backend.drummerbrain import db as dtkdb
        from backend.drummerbrain.ingest_transcription_artifacts import main as ingest_main

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "db.sqlite"
            conn = dtkdb.connect(db_path)
            try:
                dtkdb.ensure_schema(conn)
                dtkdb.upsert_dataset(conn, dataset_id="ds", label="DS", root_path=str(Path(td)), dataset_type="audio_phrase")
                dtkdb.upsert_audio_asset(
                    conn,
                    asset_id="ds:aaaaaaaaaaaaaaaa",
                    dataset_id="ds",
                    song_key="song",
                    variant="original",
                    source_path=str(Path(td) / "x.wav"),
                    content_sha256="a" * 64,
                    size_bytes=123,
                )
            finally:
                conn.close()

            in_path = Path(td) / "artifacts.json"
            in_path.write_text(
                json.dumps(
                    [
                        {
                            "asset_id": "ds:aaaaaaaaaaaaaaaa",
                            "events": [{"t": 0.0, "beat_index": 0, "sub": 0, "subdiv": 4, "lane": "hit", "strength": 0.9}],
                            "features": {"duration_s": 1.0},
                            "confidence": 0.8,
                            "provenance": {"stage": "transcription", "error_type": "none"},
                        }
                    ]
                ),
                encoding="utf-8",
            )

            rc = int(ingest_main(["--db-path", str(db_path), "--in", str(in_path), "--transcription-version", "unit_test_v1"]))
            self.assertEqual(rc, 0)

            conn2 = dtkdb.connect(db_path)
            try:
                cur = conn2.cursor()
                cur.execute(
                    "SELECT asset_id, transcription_version, confidence, events_json FROM transcription_artifacts WHERE asset_id = ?",
                    ("ds:aaaaaaaaaaaaaaaa",),
                )
                row = cur.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "ds:aaaaaaaaaaaaaaaa")
                self.assertEqual(row[1], "unit_test_v1")
                self.assertAlmostEqual(float(row[2]), 0.8)
                self.assertTrue(isinstance(row[3], str) and len(row[3]) > 0)
            finally:
                conn2.close()
