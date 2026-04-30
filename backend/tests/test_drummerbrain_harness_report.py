import os
import unittest


class TestDrummerBrainHarnessReport(unittest.TestCase):
    def test_eval_harness_report_shape(self):
        from backend.drummerbrain.eval_harness import run_suite

        # Ensure the harness can run deterministically even if DB missing; it should still return a dict.
        report = run_suite(limit_cases=2)
        self.assertIsInstance(report, dict)
        self.assertIn("ok", report)
        self.assertIn("cases_path", report)
        self.assertIn("case_count", report)
        self.assertIn("results", report)
        self.assertIsInstance(report.get("results"), list)

        # New expanded report fields
        self.assertIn("used_fraction", report)
        self.assertIn("dataset_stats", report)
        self.assertIn("dataset_type_stats", report)
        self.assertIn("failure_reasons", report)
        self.assertIn("checks", report)

        results = report.get("results") or []
        if results and isinstance(results, list) and isinstance(results[0], dict):
            self.assertIn("dataset_type", results[0])

        checks = report.get("checks") or {}
        self.assertIsInstance(checks, dict)
        self.assertIn("used_fraction", checks)

        # Optional env-driven thresholds should not crash.
        os.environ["DRUMMERBRAIN_EVAL_MIN_USED_FRACTION"] = "0.0"
        report2 = run_suite(limit_cases=2)
        self.assertIn("checks", report2)
        self.assertIn("min_used_fraction_ok", report2.get("checks") or {})
