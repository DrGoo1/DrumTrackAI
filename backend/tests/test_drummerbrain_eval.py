import os
import unittest
from pathlib import Path


class TestDrummerBrainEvalHarness(unittest.TestCase):
    def test_policy_contract_provenance_shape(self):
        import drum_generation_api

        # Run regardless of DB presence; contract should hold on early failures.
        cfg_payload = {
            "sectionId": "eval_contract",
            "startMeasure": 0,
            "endMeasure": 0,
            "tempos": [120.0],
            "timeSignature": [4, 4],
            "style": "rock",
            "drummer": "studio_rock",
            "intensity": 0.7,
            "variation": 0.5,
            "generationMode": "full_ai",
            "humanize": False,
            "fillLocations": [],
            "fillType": "auto",
            "drummerBrainEnabled": True,
            "buildScope": "selected_section",
        }

        cfg = drum_generation_api.DrumGenerationConfig(cfg_payload)
        _, prov = drum_generation_api._try_build_internal_events_from_drummerbrain(cfg)
        prov = prov if isinstance(prov, dict) else {}

        self.assertIn("used", prov)
        self.assertIn("reason", prov)
        self.assertIn("db_path", prov)
        self.assertIn("policy_version", prov)
        self.assertIn("weights", prov)
        self.assertIn("search_budget", prov)
        self.assertIsInstance(prov.get("search_budget"), dict)
        sb = prov.get("search_budget") or {}
        self.assertIn("max_candidates", sb)
        self.assertIn("tempo_window_bpm", sb)

    def test_deterministic_selection_if_db_present(self):
        import drum_generation_api

        db_path = Path(__file__).resolve().parents[2] / "admin" / "data" / "drummerbrain_clips.db"
        if not db_path.exists():
            self.skipTest("drummerbrain_clips.db not present")

        os.environ["DRUMMERBRAIN_DB_PATH"] = str(db_path)

        cfg_payload = {
            "sectionId": "eval_det",
            "startMeasure": 0,
            "endMeasure": 3,
            "tempos": [120.0] * 4,
            "timeSignature": [4, 4],
            "style": "rock",
            "drummer": "studio_rock",
            "intensity": 0.7,
            "variation": 0.5,
            "generationMode": "full_ai",
            "humanize": False,
            "fillLocations": [],
            "fillType": "auto",
            "drummerBrainEnabled": True,
            "buildScope": "selected_section",
        }

        c1 = drum_generation_api.DrumGenerationConfig(cfg_payload)
        e1, p1 = drum_generation_api._try_build_internal_events_from_drummerbrain(c1)
        c2 = drum_generation_api.DrumGenerationConfig(cfg_payload)
        e2, p2 = drum_generation_api._try_build_internal_events_from_drummerbrain(c2)

        p1 = p1 if isinstance(p1, dict) else {}
        p2 = p2 if isinstance(p2, dict) else {}

        self.assertEqual(bool(e1), bool(e2))
        self.assertEqual(p1.get("asset_id"), p2.get("asset_id"))
        self.assertEqual(p1.get("dataset_id"), p2.get("dataset_id"))

        # When enabled, provenance should always be well-formed.
        self.assertIn("used", p1)
        if bool(p1.get("used")):
            self.assertIn("asset_id", p1)
            self.assertIn("dataset_id", p1)
        else:
            self.assertIn("reason", p1)

    def test_generate_drums_includes_metadata_block_when_enabled(self):
        import drum_generation_api

        db_path = Path(__file__).resolve().parents[2] / "admin" / "data" / "drummerbrain_clips.db"
        if db_path.exists():
            os.environ["DRUMMERBRAIN_DB_PATH"] = str(db_path)

        cfg = drum_generation_api.DrumGenerationConfig(
            {
                "sectionId": "eval_meta",
                "startMeasure": 0,
                "endMeasure": 0,
                "tempos": [120.0],
                "timeSignature": [4, 4],
                "style": "rock",
                "drummer": "studio_rock",
                "intensity": 0.7,
                "variation": 0.5,
                "generationMode": "full_ai",
                "humanize": False,
                "fillLocations": [],
                "fillType": "auto",
                "drummerBrainEnabled": True,
                "buildScope": "selected_section",
                # Ensure the request does not require EGMD pinning / exact playback.
                "grooveSource": "",
                "grooveMode": "",
            }
        )

        out = drum_generation_api.generate_drums(cfg)
        self.assertIsInstance(out, dict)
        self.assertIn("metadata", out)
        md = out.get("metadata") or {}
        self.assertIn("drummerBrain", md)
        block = md.get("drummerBrain") or {}
        self.assertTrue(bool(block.get("enabled")))
        self.assertIn("provenance", block)

        prov = block.get("provenance") or {}
        self.assertIsInstance(prov, dict)
        self.assertIn("attempted", prov)
        self.assertIn("fallback_used", prov)
        self.assertIn("selected_groove_source", prov)
