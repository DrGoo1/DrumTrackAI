import unittest


class TestDrummerBrainBaselineCompare(unittest.TestCase):
    def test_compare_to_baseline_used_fraction_tolerance(self):
        from backend.drummerbrain.eval_harness import compare_to_baseline

        baseline = {
            "used_fraction": 0.75,
            "results": [
                {"case": "a", "used": True, "reason": "selected", "asset_id": "x", "dataset_id": "d"},
                {"case": "b", "used": False, "reason": "db_missing", "asset_id": None, "dataset_id": None},
            ],
        }
        report = {
            "used_fraction": 0.5,
            "results": [
                {"case": "a", "used": True, "reason": "selected", "asset_id": "x", "dataset_id": "d"},
                {"case": "b", "used": False, "reason": "db_missing", "asset_id": None, "dataset_id": None},
            ],
        }

        # Default tolerance=0 -> should fail when used_fraction drops.
        out = compare_to_baseline(report=report, baseline=baseline)
        self.assertIsInstance(out, dict)
        self.assertIn("ok", out)
        self.assertFalse(bool(out.get("ok")))

    def test_compare_to_baseline_case_drift_counts(self):
        from backend.drummerbrain.eval_harness import compare_to_baseline

        baseline = {
            "used_fraction": 0.5,
            "results": [
                {"case": "a", "used": True, "reason": "selected", "asset_id": "x", "dataset_id": "d"},
                {"case": "b", "used": False, "reason": "db_missing", "asset_id": None, "dataset_id": None},
            ],
        }
        report = {
            "used_fraction": 0.5,
            "results": [
                {"case": "a", "used": True, "reason": "selected", "asset_id": "y", "dataset_id": "d"},
                {"case": "b", "used": True, "reason": "selected", "asset_id": "z", "dataset_id": "d2"},
            ],
        }

        out = compare_to_baseline(report=report, baseline=baseline)
        cd = out.get("case_drift") or {}
        counts = cd.get("counts") or {}
        self.assertEqual(int(counts.get("used") or 0), 1)
        self.assertEqual(int(counts.get("reason") or 0), 1)
        self.assertEqual(int(counts.get("asset_id") or 0), 2)
        self.assertEqual(int(counts.get("dataset_id") or 0), 1)
