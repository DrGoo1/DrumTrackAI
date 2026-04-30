import json
import tempfile
import unittest
from pathlib import Path


class TestDrummerBrainWrittenReferences(unittest.TestCase):
    def test_ingest_written_references_and_select_tempo_adaptive(self):
        from backend.drummerbrain.ingest_written_references import main as ingest_written_main
        from backend.drummerbrain.runtime_selection import try_build_internal_events

        class Cfg:
            time_signature = (4, 4)
            tempos = [120]
            measure_count = 2

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "db.sqlite"
            in_path = Path(td) / "written.json"
            in_path.write_text(
                json.dumps(
                    [
                        {
                            "clip_id": "ref1",
                            "meter": "4/4",
                            "resolution_ppq": 480,
                            "subdiv": 4,
                            "source_ref": "docs/timing_review/ref1",
                            "events": [
                                {"barIndex": 0, "tickInBar": 0, "instrument_id": "kick", "velocity": 100},
                                {"barIndex": 0, "tickInBar": 480, "instrument_id": "snare_center", "velocity": 100},
                                {"barIndex": 0, "tickInBar": 960, "instrument_id": "kick", "velocity": 100},
                                {"barIndex": 0, "tickInBar": 1440, "instrument_id": "snare_center", "velocity": 100},
                            ],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            rc = int(
                ingest_written_main(
                    [
                        "--db-path",
                        str(db_path),
                        "--in",
                        str(in_path),
                        "--dataset-id",
                        "written",
                        "--label",
                        "Written",
                        "--transcription-version",
                        "written_v1",
                    ]
                )
            )
            self.assertEqual(rc, 0)

            import os

            os.environ["DRUMMERBRAIN_DB_PATH"] = str(db_path)
            try:
                events, prov = try_build_internal_events(Cfg())
            finally:
                os.environ.pop("DRUMMERBRAIN_DB_PATH", None)

            self.assertIsInstance(prov, dict)
            self.assertTrue(bool(prov.get("used")))
            self.assertIsInstance(events, list)
            self.assertGreater(len(events), 0)

            # Should produce sane seconds near 0..4s for 2 bars @120bpm.
            ts = [float(e.get("time_sec") or 0.0) for e in events]
            self.assertGreaterEqual(min(ts), 0.0)
            self.assertLess(max(ts), 4.1)
