import unittest
from unittest.mock import patch
from tempfile import mkstemp
import json
import os

import gcm
from apis.types import CandidateMessage, ExecutionPlan, ProviderInfo


class GcmTests(unittest.TestCase):
    def test_get_available_apis_accepts_local_ollama_without_api_key(self):
        with patch.dict(
            "os.environ",
            {"OLLAMA_MODEL": "llama3"},
            clear=True
        ):
            providers = [name for name, _ in gcm.get_available_apis()]

        self.assertEqual(providers, ["Ollama"])

    def test_get_available_apis_keeps_configured_remote_providers(self):
        with patch.dict(
            "os.environ",
            {
                "OPENAI_API_KEY": "openai-key",
                "OPENROUTER_API_KEY": "openrouter-key",
                "OLLAMA_MODEL": "llama3",
            },
            clear=True
        ):
            providers = [name for name, _ in gcm.get_available_apis()]

        self.assertEqual(providers, ["OpenRouter", "OpenAI", "Ollama"])

    def test_get_available_apis_supports_codex_and_claude_when_present(self):
        with patch.dict(
            "os.environ",
            {
                "OPENROUTER_API_KEY": "openrouter-key",
                "OPENAI_API_KEY": "openai-key",
                "CODEX_API_KEY": "codex-key",
                "ANTHROPIC_API_KEY": "claude-key",
                "OLLAMA_MODEL": "llama3",
            },
            clear=True
        ):
            providers = [name for name, _ in gcm.get_available_apis()]

        self.assertEqual(
            providers,
            ["OpenRouter", "OpenAI", "Codex", "Claude", "Ollama"]
        )

    def test_get_git_diff_summary_combines_staged_and_unstaged(self):
        responses = [
            type("Result", (), {"stdout": " 1 file changed, 2 insertions(+)\n"})(),
            type("Result", (), {"stdout": " 2 files changed, 3 deletions(-)\n"})(),
        ]

        with patch("gcm.subprocess.run", side_effect=responses) as run_mock:
            summary = gcm.get_git_diff_summary()

        self.assertEqual(
            summary,
            "Staged: 1 file changed, 2 insertions(+)\n"
            "Unstaged: 2 files changed, 3 deletions(-)"
        )
        self.assertEqual(run_mock.call_count, 2)

    def test_build_commit_message_omits_location_by_default(self):
        with patch("gcm.get_commit_count", return_value=41):
            message = gcm.build_commit_message(
                env="WINDOWS",
                emoji="🪟",
                machine="box",
                summary="📝: gcm.py",
                suggestion="fix: tighten provider selection",
                diff_summary="",
                provider="OpenAI",
                model="gpt-5-mini",
                elapsed=1.23,
            )

        self.assertNotIn("📍:", message)

    def test_build_commit_message_replaces_unstaged_case_insensitively(self):
        with patch("gcm.get_commit_count", return_value=41):
            message = gcm.build_commit_message(
                env="WINDOWS",
                emoji="🪟",
                machine="box",
                summary="📝: gcm.py",
                suggestion="unstaged: 2 files changed, 3 deletions(-)",
                diff_summary="",
                provider="OpenAI",
                model="gpt-5-mini",
                elapsed=1.23,
            )

        self.assertIn("⚠️: 2 files changed, 3 deletions(-)", message)
        self.assertNotIn("Unstaged:", message)

    def test_build_commit_message_replaces_unstaged_inside_diff_summary(self):
        with patch("gcm.get_commit_count", return_value=41):
            message = gcm.build_commit_message(
                env="WINDOWS",
                emoji="🪟",
                machine="box",
                summary="📝: gcm.py",
                suggestion="fix: tighten provider selection",
                diff_summary="Unstaged: 2 files changed, 3 deletions(-)",
                provider="OpenAI",
                model="gpt-5-mini",
                elapsed=1.23,
            )

        self.assertIn("⚠️: 2 files changed, 3 deletions(-)", message)
        self.assertNotIn("Unstaged:", message)

    def test_build_change_rollup_summary_uses_counts_not_filenames(self):
        summary = gcm.build_change_rollup_summary(
            {
                "Add": ["test.bash", "test.bat", "test_runner.py"],
                "Change": ["README.md", "config.yml"],
                "Delete": [],
            }
        )

        self.assertEqual(summary, "🆕: 3 files; 📝: 2 files")
        self.assertNotIn("README.md", summary)
        self.assertNotIn("test.bash", summary)

    def test_sanitize_suggestion_line_redacts_filename_lists(self):
        sanitized = gcm.sanitize_suggestion_line(
            'feat: update "test.bash", "test.bat" and "test_runner.py"'
        )

        self.assertEqual(
            sanitized,
            "feat: summarize repository changes without listing files."
        )

    def test_build_commit_message_redacts_lines_with_filenames(self):
        with patch("gcm.get_commit_count", return_value=41):
            message = gcm.build_commit_message(
                env="WINDOWS",
                emoji="🪟",
                machine="box",
                summary="📝: 2 files",
                suggestion=(
                    'feat: update "test.bash", "test.bat" and "test_runner.py"\n'
                    "Improve the test harness."
                ),
                diff_summary="Unstaged: 7 files changed, 172 insertions(+)",
                provider="OpenAI",
                model="gpt-5-mini",
                elapsed=1.23,
            )

        self.assertIn(
            "✨: summarize repository changes without listing files.",
            message
        )
        self.assertIn("ℹ️: Improve the test harness.", message)
        self.assertNotIn("test.bash", message)
        self.assertNotIn("test_runner.py", message)

    def test_build_commit_option_title_includes_provider_and_model(self):
        title = gcm.build_commit_option_title(2, "Codex", "gpt-5-codex")

        self.assertIn("Option 2", title)
        self.assertIn("Codex", title)
        self.assertIn("gpt-5-codex", title)

    def test_build_commit_option_title_marks_recommended(self):
        title = gcm.build_commit_option_title(
            1,
            "Codex",
            "gpt-5-codex",
            recommended=True,
        )

        self.assertIn("Recommended", title)

    def test_create_history_entry_tracks_provider_flow(self):
        candidate = CandidateMessage(
            provider="Codex",
            model="gpt-5-codex",
            content="fix: improve provider routing",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            elapsed=1.5,
        )
        generator = ProviderInfo(
            name="OpenAI",
            available=True,
            roles=["generate"],
            priority=70,
            query_fn=lambda prompt: (200, "gpt-5-mini", "ok", None, 0.1),
        )
        judge = ProviderInfo(
            name="Codex",
            available=True,
            roles=["judge"],
            priority=100,
            query_fn=lambda prompt: (200, "gpt-5-codex", "ok", None, 0.1),
        )
        plan = ExecutionPlan(generators=[generator], judge=judge, refiner=None)

        entry = gcm.create_history_entry(
            final_message="final commit message",
            selected_index=1,
            displayed_messages=[
                ("Codex", "gpt-5-codex", "formatted message", None, 1.5)
            ],
            candidates=[candidate],
            selected_candidate=candidate,
            plan=plan,
            prompt="prompt body",
            diff_summary="Staged: 1 file changed",
            user_note="note",
        )

        self.assertEqual(entry["selected_candidate"]["provider"], "Codex")
        self.assertEqual(entry["plan"]["generators"], ["OpenAI"])
        self.assertEqual(entry["plan"]["judge"], "Codex")
        self.assertEqual(entry["displayed_messages"][0]["provider"], "Codex")
        self.assertEqual(entry["outcome"], "committed")

    def test_create_history_entry_can_mark_canceled_outcome(self):
        plan = ExecutionPlan(generators=[], judge=None, refiner=None)

        entry = gcm.create_history_entry(
            final_message="",
            selected_index=0,
            displayed_messages=[],
            candidates=[],
            selected_candidate=None,
            plan=plan,
            prompt="prompt body",
            diff_summary="",
            user_note="note",
            outcome="canceled",
        )

        self.assertEqual(entry["outcome"], "canceled")
        self.assertEqual(entry["selected_index"], 0)

    def test_save_history_entry_writes_json_line(self):
        entry = {"provider": "Claude", "message": "fix: test history"}
        fd, path = mkstemp()
        os.close(fd)
        try:
            gcm.save_history_entry(entry, path)
            with open(path, "r", encoding="utf-8") as tmp:
                saved = tmp.read().strip()
        finally:
            os.remove(path)

        self.assertEqual(json.loads(saved), entry)


if __name__ == "__main__":
    unittest.main()
