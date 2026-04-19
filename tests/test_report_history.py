import json
import os
import unittest
from io import StringIO
from tempfile import mkstemp
from unittest.mock import patch

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
                "os": "WINDOWS",
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
                "os": "LINUX",
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
        self.assertEqual(summary["runs_by_os"]["WINDOWS"], 1)
        self.assertEqual(summary["runs_by_os"]["LINUX"], 1)

    def test_summarize_entries_tracks_canceled_runs_and_cancel_rate(self):
        entries = [
            {
                "os": "WINDOWS",
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
                "os": "MACOS",
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

    def test_summarize_entries_infers_os_from_legacy_final_message(self):
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM"},
                "final_message": "linea final | 🌐: CYGWIN | 🤖: Codex",
                "displayed_messages": [],
            },
            {
                "outcome": "committed",
                "project": {"name": "GCM"},
                "final_message": "linea final | 🌐: MACOS | 🤖: OpenAI",
                "displayed_messages": [],
            },
        ]

        summary = report_history.summarize_entries(entries)

        self.assertEqual(summary["runs_by_os"]["WINDOWS"], 1)
        self.assertEqual(summary["runs_by_os"]["MACOS"], 1)

    def test_summarize_entries_infers_os_from_header_emoji(self):
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM"},
                "final_message": "[💻builder🐧] 🔀: update report formatting",
                "displayed_messages": [],
            },
            {
                "outcome": "committed",
                "project": {"name": "GCM"},
                "final_message": "[💻builder🪟] 🔀: add history analytics",
                "displayed_messages": [],
                "os": "MACOS",
            },
        ]

        summary = report_history.summarize_entries(entries)

        self.assertEqual(summary["runs_by_os"]["LINUX"], 1)
        self.assertEqual(summary["runs_by_os"]["WINDOWS"], 1)
        self.assertNotIn("MACOS", summary["runs_by_os"])

    def test_render_plain_summary_includes_os_breakdown(self):
        global_overview = {
            "total_runs": 3,
            "os_total_runs": 3,
            "total_commits": 2,
            "total_canceled": 1,
            "projects": {"GCM"},
            "runs_by_os": {
                "WINDOWS": 2,
                "LINUX": 1,
                "MACOS": 0,
            },
        }
        project_overview = {
            "total_runs": 2,
            "os_total_runs": 2,
            "total_commits": 2,
            "total_canceled": 0,
            "projects": {"GCM"},
            "runs_by_os": {
                "WINDOWS": 1,
                "LINUX": 1,
                "MACOS": 0,
            },
        }
        summary = {
            "total_runs": 3,
            "selected_indexes": {},
        }

        with patch("sys.stdout", new_callable=StringIO) as stdout:
            report_history._render_plain_summary(
                [],
                summary,
                [],
                global_overview,
                project_overview,
                "GCM",
            )

        output = stdout.getvalue()
        self.assertIn("History Overview Global", output)
        self.assertIn("History Overview Project (GCM)", output)
        self.assertIn("Runs analyzed: 003", output)
        self.assertIn("Commits completed: 002", output)
        self.assertIn("Canceled runs: 001", output)
        self.assertIn("Projects found: 001", output)
        self.assertIn("OS bar chart:", output)
        self.assertIn("🪟 Windows", output)
        self.assertIn("🐧 Linux", output)

    @patch("report_history.load_git_log_messages")
    def test_build_overview_summary_separates_global_and_project(self, load_git_log_messages_mock):
        def fake_git_log(project_path):
            if project_path == "C:\\repo\\GCM":
                return [
                    "[💻host🪟] 🔀: one | 🌐: WINDOWS | 🤖: OpenAI 🧠: gpt | ⏱️: 1.00 secs",
                    "[💻host🐧] 🔀: two | 🌐: LINUX | 🤖: OpenAI 🧠: gpt | ⏱️: 1.00 secs",
                ]
            if project_path == "C:\\repo\\Other":
                return [
                    "[💻mac🍎] 🔀: three | 🌐: MACOS | 🤖: Codex 🧠: gpt | ⏱️: 1.00 secs",
                ]
            return []

        load_git_log_messages_mock.side_effect = fake_git_log
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM", "path": "C:\\repo\\GCM"},
                "displayed_messages": [],
            },
            {
                "outcome": "canceled",
                "project": {"name": "GCM", "path": "C:\\repo\\GCM"},
                "displayed_messages": [],
            },
            {
                "outcome": "committed",
                "project": {"name": "Other", "path": "C:\\repo\\Other"},
                "displayed_messages": [],
            },
        ]

        global_overview = report_history.build_overview_summary(entries)
        project_overview = report_history.build_overview_summary(
            entries,
            project_path="C:\\repo\\GCM",
            project_name="GCM",
        )

        self.assertEqual(global_overview["runs_by_os"]["WINDOWS"], 1)
        self.assertEqual(global_overview["runs_by_os"]["LINUX"], 1)
        self.assertEqual(global_overview["runs_by_os"]["MACOS"], 1)
        self.assertEqual(global_overview["os_total_runs"], 3)
        self.assertEqual(project_overview["runs_by_os"]["WINDOWS"], 1)
        self.assertEqual(project_overview["runs_by_os"]["LINUX"], 1)
        self.assertEqual(project_overview["os_total_runs"], 2)
        self.assertEqual(project_overview["total_runs"], 2)

    def test_build_os_bar_chart_lines_uses_threshold_characters(self):
        overview = {
            "os_total_runs": 100,
            "runs_by_os": {
                "WINDOWS": 75,
                "LINUX": 50,
                "MACOS": 25,
                "UNKNOWN": 0,
            },
        }

        lines = report_history.build_os_bar_chart_lines(overview, width=8)

        self.assertIn("████████", lines[0]["text"])
        self.assertIn("▓▓▓▓▓", lines[1]["text"])
        self.assertIn("▒▒▒", lines[2]["text"])
        self.assertEqual(lines[0]["style"], "green")
        self.assertEqual(lines[1]["style"], "blue")
        self.assertEqual(lines[2]["style"], "yellow")

    def test_build_os_bar_chart_lines_uses_light_shade_below_25_pct(self):
        overview = {
            "os_total_runs": 100,
            "runs_by_os": {
                "WINDOWS": 10,
                "LINUX": 0,
                "MACOS": 0,
            },
        }

        lines = report_history.build_os_bar_chart_lines(overview, width=8)

        self.assertIn("░░░░░░░░", lines[0]["text"])
        self.assertEqual(lines[0]["style"], "dark_orange")

    def test_load_registered_repos_skips_comments_blank_lines_and_duplicates(self):
        fd, path = mkstemp()
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# repos\n")
                f.write("C:\\repo\\GCM\n")
                f.write("\n")
                f.write("C:\\repo\\GCM\n")
                f.write("C:\\repo\\Other\n")

            repos = report_history.load_registered_repos(path)
        finally:
            os.remove(path)

        self.assertEqual(
            repos,
            [
                os.path.abspath("C:\\repo\\GCM"),
                os.path.abspath("C:\\repo\\Other"),
            ],
        )

    @patch("report_history.load_git_log_messages")
    def test_build_global_overview_prefers_registered_repos(self, load_git_log_messages_mock):
        def fake_git_log(project_path):
            if project_path == os.path.abspath("C:\\repo\\RegistryOnly"):
                return [
                    "[💻host🍎] 🔀: one | 🌐: MACOS | 🤖: OpenAI 🧠: gpt | ⏱️: 1.00 secs",
                ]
            if project_path == os.path.abspath("C:\\repo\\GCM"):
                return [
                    "[💻host🪟] 🔀: two | 🌐: WINDOWS | 🤖: OpenAI 🧠: gpt | ⏱️: 1.00 secs",
                ]
            return []

        load_git_log_messages_mock.side_effect = fake_git_log
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM", "path": "C:\\repo\\GCM"},
                "displayed_messages": [],
            },
        ]

        overview = report_history.build_global_overview(
            entries,
            registered_repos=[os.path.abspath("C:\\repo\\RegistryOnly"), os.path.abspath("C:\\repo\\GCM")],
        )

        self.assertEqual(overview["runs_by_os"]["WINDOWS"], 1)
        self.assertEqual(overview["runs_by_os"]["MACOS"], 1)
        self.assertEqual(overview["os_total_runs"], 2)

    @patch("report_history.load_git_log_messages")
    def test_summarize_entries_uses_git_log_for_selected_provider(self, load_git_log_messages_mock):
        final_message = (
            "[💻builder🪟] 🔀: update report\n"
            "   🤖: Codex 🧠: gpt-5-codex\n"
            "   ⏱️: 4.20 secs"
        )
        load_git_log_messages_mock.return_value = [final_message]
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM", "path": "C:\\repo\\GCM"},
                "final_message": final_message,
                "selected_candidate": {
                    "provider": "OpenAI",
                    "elapsed": 1.5,
                },
                "displayed_messages": [
                    {"provider": "Codex", "elapsed": 4.2},
                    {"provider": "OpenAI", "elapsed": 1.5},
                ],
            },
        ]

        summary = report_history.summarize_entries(entries)
        rows = report_history.compute_provider_rows(summary)
        by_project_provider = {
            (row["project"], row["provider"]): row
            for row in rows
        }

        self.assertEqual(by_project_provider[("GCM", "Codex")]["selected"], 1)
        self.assertEqual(by_project_provider[("GCM", "OpenAI")]["selected"], 0)
        self.assertAlmostEqual(by_project_provider[("GCM", "Codex")]["avg_selected"], 4.2)

    @patch("report_history.load_git_log_messages")
    def test_summarize_entries_uses_git_log_for_committed_os(self, load_git_log_messages_mock):
        final_message = (
            "[💻builder🐧] 🔀: update report\n"
            "   🤖: Codex 🧠: gpt-5-codex\n"
            "   🌐: LINUX | ⏱️: 4.20 secs"
        )
        load_git_log_messages_mock.return_value = [final_message]
        entries = [
            {
                "outcome": "committed",
                "project": {"name": "GCM", "path": "C:\\repo\\GCM"},
                "final_message": final_message,
                "os": "WINDOWS",
                "displayed_messages": [],
            },
            {
                "outcome": "canceled",
                "project": {"name": "GCM", "path": "C:\\repo\\GCM"},
                "final_message": "",
                "os": "WINDOWS",
                "displayed_messages": [],
            },
        ]

        summary = report_history.summarize_entries(entries)

        self.assertEqual(summary["runs_by_os"]["LINUX"], 1)
        self.assertNotIn("WINDOWS", summary["runs_by_os"])
        self.assertEqual(summary["os_total_runs"], 1)


if __name__ == "__main__":
    unittest.main()
