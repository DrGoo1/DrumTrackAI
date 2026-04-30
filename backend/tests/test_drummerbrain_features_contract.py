import unittest


class TestDrummerBrainFeaturesContract(unittest.TestCase):
    def test_feature_extraction_contract_keys(self):
        from backend.drummerbrain.features import extract_features_and_confidence

        events = [
            {"beat_index": 0, "sub": 0, "subdiv": 4, "lane": "kick", "strength": 0.9},
            {"beat_index": 1, "sub": 0, "subdiv": 4, "lane": "snare_center", "strength": 0.8},
            {"beat_index": 1, "sub": 2, "subdiv": 4, "lane": "hihat_closed", "strength": 0.6},
            {"beat_index": 2, "sub": 0, "subdiv": 4, "lane": "kick", "strength": 0.85},
            {"beat_index": 3, "sub": 0, "subdiv": 4, "lane": "snare_center", "strength": 0.8},
        ]
        feats, conf = extract_features_and_confidence(events=events, features_in={"beats_per_bar": 4})

        self.assertIsInstance(feats, dict)
        self.assertIsInstance(conf, float)
        self.assertGreaterEqual(conf, 0.0)
        self.assertLessEqual(conf, 1.0)

        # Core keys
        self.assertIn("event_count", feats)
        self.assertIn("unique_positions", feats)
        self.assertIn("mean_strength", feats)
        self.assertIn("lane_counts", feats)

        # Presence flags
        self.assertIn("has_kick", feats)
        self.assertIn("has_snare", feats)
        self.assertIn("has_hat", feats)

        # Derived ranking features
        self.assertIn("hits_per_beat", feats)
        self.assertIn("syncopation_ratio", feats)
        self.assertIn("backbeat_ratio", feats)

        self.assertTrue(bool(feats.get("has_kick")))
        self.assertTrue(bool(feats.get("has_snare")))
        self.assertTrue(bool(feats.get("has_hat")))

        self.assertGreater(float(feats.get("hits_per_beat") or 0.0), 0.0)
        self.assertGreaterEqual(float(feats.get("syncopation_ratio") or 0.0), 0.0)
        self.assertLessEqual(float(feats.get("syncopation_ratio") or 0.0), 1.0)
        self.assertGreaterEqual(float(feats.get("backbeat_ratio") or 0.0), 0.0)
        self.assertLessEqual(float(feats.get("backbeat_ratio") or 0.0), 1.0)
