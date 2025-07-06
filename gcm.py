#!/usr/bin/env python3
# gcm.py - Git Commit Message Generator
# version 0002 @ 2025-07-05
# authors 🧑‍💻Nelbren & 🤖Aren

import os
import sys
import yaml
import time
import shutil
import socket
import subprocess
from openai import OpenAI
from datetime import datetime
from utils import detect_environment, ENVIRONMENT_EMOJI, \
                  format_usage, get_cost, get_commit_count


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
MODEL_TIER = config.get("model_tier", "cheap")

if MODEL_TIER == "cheap":
    OPENAI_MODEL = "gpt-3.5-turbo"
elif MODEL_TIER == "premium":
    OPENAI_MODEL = "gpt-4o"
else:
    OPENAI_MODEL = config.get("openai_model", "gpt-3.5-turbo")
MAX_TOKENS = config.get("max_tokens", 400)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
USE_CONFIRM = config.get("use_confirmation", True)
SAVE_HISTORY = config.get("save_history", True)
HISTORY_PATH = os.path.expanduser(
    config.get("history_path", "~/.gcm_history.log")
)
MAX_CHARACTERS = config.get("max_characters", 160)

EMOJIS = config.get("emojis", {
    "add": "🆕",
    "change": "📝",
    "delete": "🗑️",
    "info": "ℹ️",
    "summary": "🎯",
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


def query_model(prompt):
    usage = None
    start_time = time.time()

    model_name = OLLAMA_MODEL if USE_OLLAMA else OPENAI_MODEL
    provider = "Ollama" if USE_OLLAMA else "OpenAI"

    print(f"🔍 Consulting 🤖 {provider} 🧠 {model_name}...\n")

    if USE_OLLAMA:
        import requests

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        content = response.json()["response"].strip()
    else:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=400
        )
        content = response.choices[0].message.content.strip()
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }

    elapsed_time = time.time() - start_time
    final_content = content[:MAX_CHARACTERS] if MAX_CHARACTERS else content
    return final_content, usage, elapsed_time


def build_commit_message(env, emoji, machine, summary,
                         suggestion, diff_summary=""):
    header = f"[💻{machine}{emoji}]"
    padding = " " * (len(header) + 3)

    lines = [f"{header} {summary}"]

    keywords = {
        "Summary", "insertions", "deletion",
        "Modified", "added", "deleted"
    }

    for line in suggestion.splitlines():
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
    ai_suggestion, usage, elapsed_time = query_model(prompt)

    message = build_commit_message(
        env, emoji, machine_name, summary, ai_suggestion, diff_summary
    )

    print("\n📝 Suggested Commit Message:\n")
    print("-" * columns)
    print(message)
    print("-" * columns)

    cost = get_cost(USE_OLLAMA, MODEL_TIER)

    if USE_OLLAMA:
        print(f"🤖 Ollama 🧠 {OLLAMA_MODEL} ({cost})")
    else:
        print(f"🤖 OpenAI 🧠 {OPENAI_MODEL} ({cost})")

    if usage:
        print(format_usage(usage))

    print(f"⏱️ Elapsed time: {elapsed_time:.2f} seconds\n")

    if USE_CONFIRM:
        confirm = input(
            "\n✅ Do you want to use this message to commit? (y/N): "
        ).strip().lower()

        if confirm != "y":
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
