#!/usr/bin/env python3
# gcm.py - Git Commit Message Generator
# authors 🧑‍💻Nelbren & 🤖Aren

import os
import sys
import yaml
import shutil
import socket
import subprocess
from datetime import datetime
from utils import detect_environment, ENVIRONMENT_EMOJI, \
                  format_usage, get_cost, get_commit_count

from apis.OpenRouter.query_model import query_model as query_openrouter
from apis.OpenAI.query_model import query_model as query_openai
from apis.Ollama.query_model import query_model as query_ollama

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")

available_apis = []
if OPENROUTER_API_KEY:
    available_apis.append(("OpenRouter", query_openrouter))
if OPENAI_API_KEY:
    available_apis.append(("OpenAI", query_openai))
if OLLAMA_API_KEY:
    available_apis.append(("Ollama", query_ollama))


def load_config(path=None):
    if path is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "config.yml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


config = load_config()

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
MAX_CHARACTERS = config.get("max_characters", 160)
SUGGESTED_MESSAGES = config.get("suggested_messages", 1)

EMOJIS = config.get("emojis", {
    "header": "🔀",
    "add": "🆕",
    "change": "📝",
    "delete": "🗑️",
    "info": "ℹ️",
    "summary": "🎯"
})

PROMPT_TEMPLATE = config.get("prompt_template", "")
columns = shutil.get_terminal_size().columns


def is_git_repo():
    return os.path.isdir(".git")


def get_machine_name():
    return socket.gethostname()


def get_git_changes():
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().splitlines()
    except subprocess.CalledProcessError as e:
        print("Error ejecutando git:", e)
        sys.exit(1)


def get_git_diff_summary():
    try:
        result = subprocess.run(
            ["git", "diff", "--shortstat"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def format_file_list(file_list):
    if not file_list:
        return ""

    quoted_files = [f'"{file}"' for file in file_list]

    if len(quoted_files) == 1:
        return quoted_files[0]

    return ", ".join(quoted_files[:-1]) + " and " + quoted_files[-1]


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


def build_prompt(changes, diff_summary=""):
    summary = []
    for key, files in changes.items():
        if files:
            filenames = format_file_list([os.path.basename(f) for f in files])
            summary.append(f"{key}: {filenames}")

    prompt_filled = PROMPT_TEMPLATE.format(
        changes="; ".join(summary),
        diff=diff_summary or "No diff available."
    )
    return prompt_filled


def build_commit_message(env, emoji, machine, summary,
                         suggestion, diff_summary=""):
    header = f"[💻{machine}{emoji}]"
    padding = " " * (len(header) + 3)

    header_emoji = EMOJIS.get("header")
    lines = [f"{header} {header_emoji}: {summary}"]

    keywords = {
        "Summary", "insertions", "deletion",
        "Modified", "added", "deleted"
    }

    replacements = {
        "chore:": "🧹:",
        "feat:": "✨:",
    }

    for line in suggestion.splitlines():
        for key, value in replacements.items():
            if key in line:
                line = line.replace(key, value)
        if line.strip():
            emoji2 = EMOJIS.get("summary") if any(
                word in line for word in keywords) else EMOJIS.get("info")
            lines.append(f"{padding}{emoji2}: {line}")

    if diff_summary and diff_summary not in suggestion:
        for line in diff_summary.splitlines():
            if line.strip():
                lines.append(f"{padding}{EMOJIS.get('summary')}: {line}")

    commit_count = get_commit_count() + 1
    commit_number_str = f"{commit_count:07,}"
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    commit_id_line = f"🆔: {commit_number_str} | 🕒: {timestamp_str} " + \
                     f"| {ENVIRONMENT_EMOJI}: {env}"
    lines.append(f"{padding}{commit_id_line}")

    return "\n".join(lines)


def save_to_history(message, path):
    try:
        with open(os.path.expanduser(path), "a", encoding="utf-8") as f:
            f.write(message + "\n" + ("-" * 80) + "\n")
    except Exception as e:
        print(f"⚠️ Could not save history: {e}")


def has_staged_changes():
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True
    )
    return bool(result.stdout.strip())


if __name__ == "__main__":
    if not is_git_repo():
        print("❌ This directory is not a valid Git repository (missing .git).")
        sys.exit(1)

    env, emoji = detect_environment()

    machine_name = get_machine_name()
    changes = classify_changes(get_git_changes())

    if not any(changes.values()):
        print("ℹ️ No changes detected. Nothing to do.")
        sys.exit(0)

    diff_summary = get_git_diff_summary()

    summary = "; ".join(
        f"{EMOJIS.get(key.lower(), '')}: {format_file_list(v)}"
        for key, v in changes.items() if v
    )

    prompt = build_prompt(changes, diff_summary)

    messages = []

    for i in range(SUGGESTED_MESSAGES):
        provider, query_fn = available_apis[i % len(available_apis)]
        if provider != "OpenRouter" and i >= len(available_apis):
            provider, query_fn = "OpenRouter", query_openrouter

        code, model, response, usage, elapsed = query_fn(prompt)

        content = response[:MAX_CHARACTERS] if MAX_CHARACTERS else response

        message = build_commit_message(
            env, emoji, machine_name, summary, content, diff_summary
        )

        messages.append((provider, model, message, usage, elapsed))

    # ai_suggestion, usage, elapsed_time = query_model(prompt)

    print("\n📝 Suggested Commit Message:\n")
    for idx, (provider, model, msg, usage, elapsed) in enumerate(messages, 1):
        print(f"#{idx}: 🤖 {provider} 🧠 {model} | ", end="")
        print(f"⏱️ Elapsed time: {elapsed:.2f} seconds")
        print("-" * columns)
        print(msg)
        if usage:
            print("-" * columns)
            print(format_usage(usage))
        print("=" * columns)

    # cost = get_cost(USE_OLLAMA, MODEL_TIER)
    #    print(f"🤖 Ollama 🧠 {OLLAMA_MODEL} ({cost})")

    if USE_CONFIRM:
        options = len(messages)
        confirm = input(
            f"\n✅ Do you want to use this message to commit? (1~{options}/0): "
        ).strip()

        try:
            val = int(confirm)
        except ValueError:
            val = 0

        if val >= 1 and val <= options:
            print(f"DO SOMETHING WITH {val}")
        if val == "0":
            print("🚫 Commit canceled by user.")
            sys.exit(0)

    if not has_staged_changes():
        print("ℹ️ No changes staged. Running: git add .")
        subprocess.run(["git", "add", "."], check=True)

    try:
        subprocess.run(["git", "commit", "-m", message], check=True)
        print("✅ Commit successfully completed.")

        if SAVE_HISTORY:
            save_to_history(message, HISTORY_PATH)

    except subprocess.CalledProcessError as e:
        print("❌ Error executing git commit:", e)
