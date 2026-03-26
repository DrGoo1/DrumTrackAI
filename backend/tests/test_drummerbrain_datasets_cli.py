import tempfile
import unittest
from pathlib import Path


class TestDrummerBrainDatasetsCLI(unittest.TestCase):
    def test_list_and_toggle_enabled(self):
        from backend.drummerbrain import db as dtkdb

        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "db.sqlite"
            conn = dtkdb.connect(db_path)
            try:
                dtkdb.ensure_schema(conn)
                dtkdb.upsert_dataset(conn, dataset_id="a", label="A", root_path="x", dataset_type="written_reference")
                dtkdb.upsert_dataset(conn, dataset_id="b", label="B", root_path="y", dataset_type="audio_phrase")

                rows = dtkdb.list_datasets(conn)
                self.assertEqual([r.get("dataset_id") for r in rows], ["a", "b"])

                dtkdb.set_dataset_enabled(conn, dataset_id="a", enabled=False)
                rows2 = dtkdb.list_datasets(conn)
                ra = [r for r in rows2 if r.get("dataset_id") == "a"][0]
                self.assertEqual(int(ra.get("enabled") or 0), 0)

                dtkdb.set_dataset_enabled(conn, dataset_id="a", enabled=True)
                rows3 = dtkdb.list_datasets(conn)
                ra3 = [r for r in rows3 if r.get("dataset_id") == "a"][0]
                self.assertEqual(int(ra3.get("enabled") or 0), 1)
            finally:
                conn.close()
