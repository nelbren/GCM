#!/usr/bin/env python3
# gcm.py - Git Commit Message Generator
# authors 🧑‍💻Nelbren & 🤖Aren

import os
import sys
import json
import re
import yaml
import shutil
import socket
import requests
import subprocess
from datetime import datetime
from utils import detect_environment, ENVIRONMENT_EMOJI, \
                  format_usage, get_commit_count, normalize_os_name, \
                  run_git_command
from version import load_version_config, update_version_file
from apis.registry import get_available_provider_pairs, discover_available_providers
from apis.orchestrator import build_execution_plan, run_generators, \
                              run_judge, run_refiner

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None
    Panel = None
    Text = None

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")


def load_config(path=None):
    if path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "config.yml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()
version_config = load_version_config()

USE_OLLAMA = os.getenv("USE_OLLAMA", "True")
USE_OLLAMA = True if USE_OLLAMA == "True" else False
OLLAMA_MODEL = config.get("ollama_model", "llama3")
MODEL_TIER = os.getenv("MODEL_TIER", "cheap")

MAX_TOKENS = config.get("max_tokens", 400)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_CONFIRM = config.get("use_confirmation", True)
SAVE_HISTORY = config.get("save_history", True)
HISTORY_PATH = os.path.expanduser(
    config.get("history_path", "~/.gcm_history.log")
)
HISTORY_JSON_PATH = os.path.expanduser(
    config.get("history_json_path", "~/.gcm_history.jsonl")
)
INCLUDE_LOCATION = config.get("include_location", False)
MAX_CHARACTERS = config.get("max_characters", 160)
SUGGESTED_MESSAGES = config.get("suggested_messages", 1)

EMOJIS = config.get("emojis", {
    "header": "🔀",
    "add": "🆕",
    "change": "📝",
    "delete": "🗑️",
    "info": "ℹ️",
    "summary": "🎯",
    "test": "🧪"
})

PROMPT_TEMPLATE = config.get("prompt_template", "")
columns = shutil.get_terminal_size().columns
RICH_CONSOLE = Console() if HAS_RICH else None


def safe_print(message):
    try:
        print(message)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="ignore").decode("ascii")
        print(fallback or "[message could not be displayed in this terminal]")


def build_commit_option_title(index, provider, model=None, recommended=False):
    title = f"✍️ Option {index} · 🤖 {provider}"
    if model:
        title = f"{title} · 🧠 {model}"
    if recommended:
        title = f"{title} · 🏆 Recommended"
    return title


def render_commit_options(messages, recommended_index=None):
    if not HAS_RICH:
        safe_print("\n📝 Suggested Commit Message:\n")
        for idx, (provider, model, msg, usage, elapsed) in enumerate(messages, 1):
            option_label = f"[ {idx} ] {provider}"
            if model:
                option_label = f"{option_label} ({model})"
            if idx == recommended_index:
                option_label = f"{option_label} [Recommended]"
            cols = max(columns - len(option_label), 1)
            safe_print(f"{option_label}{'-' * cols}")
            safe_print(msg)
            if usage:
                safe_print("-" * columns)
                safe_print(format_usage(usage))
            safe_print("=" * columns)
        return

    RICH_CONSOLE.print()
    RICH_CONSOLE.print(
        Panel.fit("📝 Suggested Commit Messages", border_style="cyan")
    )

    for idx, (provider, model, msg, usage, elapsed) in enumerate(messages, 1):
        is_recommended = idx == recommended_index
        body = Text(msg)
        if usage:
            body.append("\n\n")
            body.append(format_usage(usage), style="dim")
        body.append("\n")
        body.append(f"⏱️ Elapsed: {elapsed:.2f} secs", style="dim")
        RICH_CONSOLE.print(
            Panel(
                body,
                title=build_commit_option_title(
                    idx, provider, model, recommended=is_recommended
                ),
                border_style="green" if is_recommended else "blue",
            )
        )


def is_git_repo():
    return os.path.isdir(".git")


def get_available_apis():
    return get_available_provider_pairs(config)


def get_machine_name():
    return socket.gethostname()


def get_git_changes():
    try:
        result = run_git_command(
            ["status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().splitlines()
    except subprocess.CalledProcessError as e:
        safe_print(f"Error ejecutando git: {e}")
        sys.exit(1)


def get_git_diff_summary():
    summaries = []
    commands = [
        ("Staged", ["git", "diff", "--cached", "--shortstat"]),
        ("Unstaged", ["git", "diff", "--shortstat"]),
    ]

    for label, command in commands:
        try:
            result = subprocess.run(
                ["git", "-c", f"safe.directory={os.path.abspath(os.getcwd())}", *command[1:]],
                capture_output=True,
                text=True,
                check=True
            )
            output = result.stdout.strip()
            if output:
                summaries.append(f"{label}: {output}")
        except subprocess.CalledProcessError:
            continue

    return "\n".join(summaries)


def format_file_list(file_list):
    if not file_list:
        return ""

    quoted_files = [f'"{file}"' for file in file_list]

    if len(quoted_files) == 1:
        return quoted_files[0]

    return ", ".join(quoted_files[:-1]) + " and " + quoted_files[-1]


def format_count_label(count, noun="file"):
    suffix = "" if count == 1 else "s"
    return f"{count} {noun}{suffix}"


def build_change_rollup_summary(changes):
    sections = []
    labels = {
        "Add": EMOJIS.get("add", "Add"),
        "Change": EMOJIS.get("change", "Change"),
        "Delete": EMOJIS.get("delete", "Delete"),
    }

    for key in ("Add", "Change", "Delete"):
        files = changes.get(key, [])
        if files:
            sections.append(f"{labels[key]}: {format_count_label(len(files))}")

    return "; ".join(sections)


def classify_changes(lines):
    changes = {"Add": [], "Change": [], "Delete": []}
    for line in lines:
        code = line[:2].strip()
        file = line[2:].lstrip() if len(line) > 3 else line.strip()

        if code in {"A", "??"}:
            changes["Add"].append(file)
        elif code == "M":
            changes["Change"].append(file)
        elif code == "D":
            changes["Delete"].append(file)
    return changes


def build_prompt(changes, diff_summary="", note=""):
    summary = []
    for key, files in changes.items():
        if files:
            filenames = format_file_list([os.path.basename(f) for f in files])
            summary.append(f"{key}: {filenames}")

    prompt_filled = PROMPT_TEMPLATE.format(
        note=note.strip(),
        changes="; ".join(summary),
        diff=diff_summary or "No diff available."
    )
    return prompt_filled


def contains_file_reference(text):
    patterns = [
        r'["\'][^"\']+\.[A-Za-z0-9]{1,10}["\']',
        r"\b[\w.-]+\.[A-Za-z0-9]{1,10}\b",
        r"(?:[A-Za-z]:)?[\\/][\w .-]+(?:[\\/][\w .-]+)+",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def sanitize_suggestion_line(line):
    sanitized = line.strip()
    if not sanitized:
        return sanitized

    if not contains_file_reference(sanitized):
        return sanitized

    prefix_match = re.match(r"^([^:]{1,20}:)\s*", sanitized)
    if prefix_match:
        return (
            f"{prefix_match.group(1)} summarize repository changes "
            "without listing files."
        )

    return "summarize repository changes without listing files."


def apply_commit_line_replacements(line):
    replacements = {
        r"chore:": "🧹:",
        r"feat:": "✨:",
        r"fix:": "🛠️:",
        r"docs:": "📄:",
        r"refactor:": "🔧:",
        r"test:": "🧪:",
        r"unstaged:": "⚠️:",
    }

    updated_line = line
    for pattern, value in replacements.items():
        updated_line = re.sub(pattern, value, updated_line, flags=re.IGNORECASE)
    return updated_line


def get_location():
    try:
        r = requests.get("https://ipinfo.io/json", timeout=5)
        data = r.json()
        city = data.get("city", "Unknown city")
        region = data.get("region", "")
        country = data.get("country", "")
        return f"{city}, {region}, {country}".strip(", ")
    except Exception as e:
        return f"Unknown ({type(e).__name__}: {e})"


def amend_commit_message():
    run_git_command(
        ["commit", "--amend"],
        check=True
    )


def build_commit_message(env, emoji, machine, summary,
                         suggestion, diff_summary,
                         provider, model, elapsed):
    header = f"[💻{machine}{emoji}]"
    padding = " " * (len(header) + 3)

    header_emoji = EMOJIS.get("header")
    lines = [f"{header} {header_emoji}: {summary}"]

    keywords = {
        "Summary", "insertions", "deletion",
        "Modified", "added", "deleted"
    }

    for line in suggestion.splitlines():
        line = apply_commit_line_replacements(line)
        line = sanitize_suggestion_line(line)
        if line.strip():
            emoji2 = EMOJIS.get("summary") if any(
                word in line for word in keywords) else EMOJIS.get("info")
            lines.append(f"{padding}{emoji2}: {line}")

    if diff_summary and diff_summary not in suggestion:
        for line in diff_summary.splitlines():
            if line.strip():
                line = apply_commit_line_replacements(line)
                lines.append(f"{padding}{EMOJIS.get('summary')}: {line}")

    commit_count = get_commit_count() + 1
    commit_number_str = f"{commit_count:011,}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    commit_id_parts = [
        f"🆔: {commit_number_str}",
        f"🕒: {timestamp_str}",
    ]

    if INCLUDE_LOCATION:
        commit_id_parts.append(f"📍: {get_location()}")

    commit_id_parts.extend([
        f"{ENVIRONMENT_EMOJI}: {env}",
        f"🤖: {provider} 🧠: {model}",
        f"⏱️: {elapsed:.2f} secs",
    ])
    commit_id_line = " | ".join(commit_id_parts)

    lines.append(f"{padding}{commit_id_line}")

    return "\n".join(lines)


def save_to_history(message, path):
    try:
        with open(os.path.expanduser(path), "a", encoding="utf-8") as f:
            f.write(message + "\n" + ("-" * 80) + "\n")
    except Exception as e:
        safe_print(f"⚠️ Could not save history: {e}")


def get_project_metadata():
    project_path = os.path.abspath(os.getcwd())
    project_name = os.path.basename(project_path) or project_path
    return {
        "name": project_name,
        "path": project_path,
    }


def create_history_entry(final_message, selected_index, displayed_messages,
                         candidates, selected_candidate, plan, prompt,
                         diff_summary, user_note, outcome="committed"):
    environment_name, _ = detect_environment(EMOJIS)
    history_os = normalize_os_name(environment_name)
    return {
        "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        "outcome": outcome,
        "os": history_os,
        "project": get_project_metadata(),
        "selected_index": selected_index,
        "user_note": user_note,
        "prompt_length": len(prompt or ""),
        "diff_summary": diff_summary,
        "final_message": final_message,
        "selected_candidate": {
            "provider": getattr(selected_candidate, "provider", None),
            "model": getattr(selected_candidate, "model", None),
            "elapsed": getattr(selected_candidate, "elapsed", None),
            "content": getattr(selected_candidate, "content", None),
        } if selected_candidate else None,
        "plan": {
            "generators": [provider.name for provider in plan.generators],
            "judge": plan.judge.name if plan.judge else None,
            "refiner": plan.refiner.name if plan.refiner else None,
        },
        "displayed_messages": [
            {
                "index": idx,
                "provider": provider,
                "model": model,
                "elapsed": elapsed,
                "usage": usage,
                "message": message,
            }
            for idx, (provider, model, message, usage, elapsed)
            in enumerate(displayed_messages, 1)
        ],
        "raw_candidates": [
            {
                "provider": candidate.provider,
                "model": candidate.model,
                "elapsed": candidate.elapsed,
                "usage": candidate.usage,
                "content": candidate.content,
            }
            for candidate in candidates
        ],
    }


def save_history_entry(entry, path):
    try:
        with open(os.path.expanduser(path), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        safe_print(f"⚠️ Could not save structured history: {e}")


def has_staged_changes():
    result = run_git_command(
        ["diff", "--cached", "--name-only"],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


def confirm_stage_all_changes():
    if not USE_CONFIRM:
        safe_print("❌ No changes staged. Stage files explicitly before committing.")
        sys.exit(1)

    while True:
        confirm = input(
            "\n⚠️ No changes are staged. Stage all detected changes with "
            "'git add .' and continue? (y/n): "
        ).strip().lower()

        if confirm in {"y", "yes"}:
            safe_print("ℹ️ Running: git add .")
            run_git_command(["add", "."], check=True)
            return
        if confirm in {"n", "no"}:
            safe_print("🚫 Commit canceled. Stage the intended files and rerun.")
            sys.exit(0)


if __name__ == "__main__":
    if not is_git_repo():
        safe_print("❌ This directory is not a valid Git repository (missing .git).")
        sys.exit(1)

    env, emoji = detect_environment()
    machine_name = get_machine_name()

    changes = classify_changes(get_git_changes())
    if not any(changes.values()):
        safe_print("ℹ️ No changes detected. Nothing to do.")
        sys.exit(0)

    available_apis = get_available_apis()
    if not available_apis:
        safe_print(
            "❌ No AI providers configured. Set OpenAI, OpenRouter, "
            "Ollama, Codex, or Claude credentials first."
        )
        sys.exit(0)

    version = update_version_file(version_config)
    if version:
        safe_print(f"🔖 Version: {version}")

    diff_summary = get_git_diff_summary()
    summary = build_change_rollup_summary(changes)

    user_note = sys.argv[1] if len(sys.argv) > 1 else "None"

    prompt = build_prompt(changes, diff_summary, user_note)
    providers = discover_available_providers(config)
    plan = build_execution_plan(providers, config)

    if plan.generators:
        generator_names = ", ".join(provider.name for provider in plan.generators)
        safe_print(f"🤖 Generators selected: {generator_names}")
    if plan.judge:
        safe_print(f"⚖️ Using {plan.judge.name} as judge.")
    if plan.refiner:
        safe_print(f"✨ Using {plan.refiner.name} as refiner.")

    candidates = run_generators(plan.generators, prompt, MAX_CHARACTERS)

    if len(candidates) == 0:
        safe_print("\n⚠️ There are no suggested confirmation messages!\n")
        exit(1)

    selected_candidate = run_judge(
        plan.judge,
        prompt,
        candidates,
        MAX_CHARACTERS
    )
    selected_candidate = run_refiner(
        plan.refiner,
        prompt,
        selected_candidate,
        MAX_CHARACTERS
    )

    messages = []
    seen = set()

    ordered_candidates = list(candidates)
    if selected_candidate:
        selected_key = (
            selected_candidate.provider,
            selected_candidate.model,
            selected_candidate.content
        )
        if selected_key not in {
            (candidate.provider, candidate.model, candidate.content)
            for candidate in ordered_candidates
        }:
            ordered_candidates.insert(0, selected_candidate)

    for candidate in ordered_candidates:
        unique_key = (candidate.provider, candidate.model, candidate.content)
        if unique_key in seen:
            continue
        seen.add(unique_key)
        message = build_commit_message(
            env, emoji, machine_name, summary,
            candidate.content, diff_summary,
            candidate.provider, candidate.model, candidate.elapsed
        )
        messages.append((
            candidate.provider,
            candidate.model,
            message,
            candidate.usage,
            candidate.elapsed
        ))

    if len(messages) == 0:
        safe_print("\n⚠️ There are no suggested confirmation messages!\n")
        exit(1)

    recommended_index = None
    if selected_candidate:
        selected_message = build_commit_message(
            env, emoji, machine_name, summary,
            selected_candidate.content, diff_summary,
            selected_candidate.provider, selected_candidate.model,
            selected_candidate.elapsed
        )
        for idx, (_, _, msg, _, _) in enumerate(messages, 1):
            if msg == selected_message:
                recommended_index = idx
                break

    render_commit_options(messages, recommended_index=recommended_index)

    if USE_CONFIRM:
        options = len(messages)
        selected_index = None
        while True:
            confirm = input(
                f"\n✅ Do you want to use any of these messages "
                f"(1~{options}) to commit? (1~{options}/0=Cancel): "
            ).strip()

            try:
                val = int(confirm)
            except ValueError:
                val = -1

            if val >= 1 and val <= options:
                selected_index = val
                message = messages[val - 1][2]
                break
            if val == 0:
                if SAVE_HISTORY:
                    history_entry = create_history_entry(
                        final_message="",
                        selected_index=0,
                        displayed_messages=messages,
                        candidates=ordered_candidates,
                        selected_candidate=selected_candidate,
                        plan=plan,
                        prompt=prompt,
                        diff_summary=diff_summary,
                        user_note=user_note,
                        outcome="canceled",
                    )
                    save_history_entry(history_entry, HISTORY_JSON_PATH)
                safe_print("🚫 Commit canceled by user.")
                sys.exit(0)
    else:
        selected_index = 1
        message = messages[0][2]

    if not has_staged_changes():
        confirm_stage_all_changes()

    try:
        run_git_command(["commit", "-m", message], check=True)
        safe_print("✅ Commit successfully completed.")

        if SAVE_HISTORY:
            save_to_history(message, HISTORY_PATH)
            history_entry = create_history_entry(
                final_message=message,
                selected_index=selected_index,
                displayed_messages=messages,
                candidates=ordered_candidates,
                selected_candidate=selected_candidate,
                plan=plan,
                prompt=prompt,
                diff_summary=diff_summary,
                user_note=user_note,
                outcome="committed",
            )
            save_history_entry(history_entry, HISTORY_JSON_PATH)

    except subprocess.CalledProcessError as e:
        safe_print(f"❌ Error executing git commit: {e}")
