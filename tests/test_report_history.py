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
                "outcome": "committed",
                "project": {"name": "GCM"},
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
                "outcome": "committed",
                "project": {"name": "GCM"},
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
        by_project_provider = {
            (row["project"], row["provider"]): row
            for row in rows
        }
        codex_row = by_project_provider[("GCM", "Codex")]
        openai_row = by_project_provider[("GCM", "OpenAI")]

        self.assertEqual(summary["total_commits"], 2)
        self.assertEqual(summary["projects"], {"GCM"})
        self.assertEqual(
            summary["judge_usage_by_project_provider"][("GCM", "Codex")],
            1
        )
        self.assertEqual(
            summary["judge_usage_by_project_provider"][("GCM", "Claude")],
            1
        )
        self.assertEqual(
            summary["refiner_usage_by_project_provider"][("GCM", "Codex")],
            1
        )
        self.assertEqual(openai_row["displayed"], 2)
        self.assertEqual(codex_row["selected"], 1)
        self.assertAlmostEqual(codex_row["acceptance_vs_shown"], 100.0)
        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["total_canceled"], 0)

    def test_summarize_entries_tracks_canceled_runs_and_cancel_rate(self):
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM"},
                "selected_index": 1,
                "selected_candidate": {
                    "provider": "OpenAI",
                    "elapsed": 1.5,
                },
                "plan": {
                    "generators": ["OpenAI", "Codex"],
                    "judge": "Codex",
                    "refiner": None,
                },
                "displayed_messages": [
                    {"provider": "OpenAI", "elapsed": 1.5},
                    {"provider": "Codex", "elapsed": 1.2},
                ],
            },
            {
                "outcome": "canceled",
                "project": {"name": "GCM"},
                "selected_index": 0,
                "selected_candidate": {
                    "provider": "Codex",
                    "elapsed": 1.1,
                },
                "plan": {
                    "generators": ["OpenAI", "Codex"],
                    "judge": "Codex",
                    "refiner": None,
                },
                "displayed_messages": [
                    {"provider": "OpenAI", "elapsed": 1.9},
                    {"provider": "Codex", "elapsed": 1.1},
                ],
            },
        ]

        summary = report_history.summarize_entries(entries)
        rows = report_history.compute_provider_rows(summary)
        by_project_provider = {
            (row["project"], row["provider"]): row
            for row in rows
        }
        openai_row = by_project_provider[("GCM", "OpenAI")]
        codex_row = by_project_provider[("GCM", "Codex")]

        self.assertEqual(summary["total_runs"], 2)
        self.assertEqual(summary["total_commits"], 1)
        self.assertEqual(summary["total_canceled"], 1)
        self.assertEqual(summary["selected_indexes"]["0"], 1)
        self.assertEqual(openai_row["displayed"], 2)
        self.assertEqual(openai_row["selected"], 1)
        self.assertAlmostEqual(openai_row["cancel_vs_shown"], 50.0)
        self.assertEqual(codex_row["selected"], 0)
        self.assertAlmostEqual(codex_row["cancel_vs_shown"], 50.0)


if __name__ == "__main__":
    unittest.main()
