import unittest

import test_runner


class FakeResult:
    def __init__(
        self,
        tests_run,
        successes,
        failures,
        errors,
        skipped,
        expected_failures,
        unexpected_successes,
    ):
        self.testsRun = tests_run
        self.successes = [object()] * successes
        self.failures = [object()] * failures
        self.errors = [object()] * errors
        self.skipped = [object()] * skipped
        self.expectedFailures = [object()] * expected_failures
        self.unexpectedSuccesses = [object()] * unexpected_successes


class TestRunnerSummaryTests(unittest.TestCase):
    def test_build_summary_rows_uses_status_emojis_and_bar_thresholds(self):
        result = FakeResult(
            tests_run=28,
            successes=28,
            failures=7,
            errors=3,
            skipped=1,
            expected_failures=0,
            unexpected_successes=0,
        )

        rows = test_runner.build_summary_rows(result, width=8)

        self.assertEqual(len(rows), 6)
        self.assertIn("✅ Passed", rows[0]["text"])
        self.assertIn("████████", rows[0]["text"])
        self.assertIn("007 (25.0%)", rows[1]["text"])
        self.assertIn("▒▒", rows[1]["text"])
        self.assertIn("003 (10.7%)", rows[2]["text"])
        self.assertIn("░", rows[2]["text"])
        self.assertIn("🧪 Expected failures", rows[4]["text"])
        self.assertIn("000 (0.0%)", rows[4]["text"])

    def test_build_summary_text_includes_bar_chart_rows(self):
        result = FakeResult(
            tests_run=4,
            successes=4,
            failures=0,
            errors=0,
            skipped=0,
            expected_failures=0,
            unexpected_successes=0,
        )

        summary = test_runner.build_summary_text(result)

        self.assertIn("Total: 4", summary.plain)
        self.assertIn("✅ Passed", summary.plain)
        self.assertIn("004 (100.0%)", summary.plain)


if __name__ == "__main__":
    unittest.main()
