import json
import os
import unittest
from tempfile import mkstemp

import report_history


class ReportHistoryTests(unittest.TestCase):
    def test_load_history_entries_reads_jsonl(self):
        fd, path = mkstemp()
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json.dumps({"selected_index": 1}) + "\n")
                f.write(json.dumps({"selected_index": 2}) + "\n")
            entries = report_history.load_history_entries(path)
        finally:
            os.remove(path)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["selected_index"], 1)

    def test_summarize_entries_computes_acceptance_and_roles(self):
        entries = [
            {
                "selected_index": 1,
                "selected_candidate": {
                    "provider": "Codex",
                    "elapsed": 1.2,
                },
                "plan": {
                    "generators": ["OpenAI", "Ollama"],
                    "judge": "Codex",
                    "refiner": None,
                },
                "displayed_messages": [
                    {"provider": "OpenAI", "elapsed": 2.0},
                    {"provider": "Codex", "elapsed": 1.2},
                ],
            },
            {
                "selected_index": 2,
                "selected_candidate": {
                    "provider": "OpenAI",
                    "elapsed": 1.8,
                },
                "plan": {
                    "generators": ["OpenAI", "OpenRouter"],
                    "judge": "Claude",
                    "refiner": "Codex",
                },
                "displayed_messages": [
                    {"provider": "OpenAI", "elapsed": 1.8},
                    {"provider": "OpenRouter", "elapsed": 3.0},
                ],
            },
        ]

        summary = report_history.summarize_entries(entries)
        rows = report_history.compute_provider_rows(summary)
        by_provider = {row["provider"]: row for row in rows}

        self.assertEqual(summary["total_commits"], 2)
        self.assertEqual(summary["judge_usage"]["Codex"], 1)
        self.assertEqual(summary["judge_usage"]["Claude"], 1)
        self.assertEqual(summary["refiner_usage"]["Codex"], 1)
        self.assertEqual(by_provider["OpenAI"]["displayed"], 2)
        self.assertEqual(by_provider["Codex"]["selected"], 1)
        self.assertAlmostEqual(by_provider["Codex"]["acceptance_vs_shown"], 100.0)


if __name__ == "__main__":
    unittest.main()
