# utils.py - Librería compartida para GCM

import os
import platform
import subprocess

DEFAULT_EMOJIS = {
    'windows': '🪟',
    'macos': '🍎',
    'linux': '🐧',
    'cygwin': '🪟',
    'git bash': '🪟',
    'unknown': '❓'
}

ENVIRONMENT_EMOJI = '🌐'
USAGE_EMOJI = '📊'
PROMPT_EMOJI = '📝'
RESPONSE_EMOJI = '💬'
TOTAL_EMOJI = '🧮'

EXPENSIVE_EMOJI = '💸'
CHEAP_EMOJI = '💵'
ENERGY_EMOJI = '🔌'


def detect_environment(emojis=None):
    emojis = emojis or DEFAULT_EMOJIS

    system = platform.system().lower()
    term = os.environ.get('TERM', '').lower()
    shell = os.environ.get('SHELL', '').lower()
    msystem = os.environ.get('MSYSTEM', '').lower()
    ostype = os.environ.get('OSTYPE', '').lower()

    if 'darwin' in ostype or system == 'darwin':
        return 'MACOS', emojis.get('macos', '🍎')
    elif 'linux' in ostype or system == 'linux':
        return 'LINUX', emojis.get('linux', '🐧')
    elif 'cygwin' in ostype or 'cygwin' in term or 'cygwin' in shell:
        return 'CYGWIN', emojis.get('cygwin', '🪟')
    elif 'msys' in ostype or 'mingw' in ostype or 'mingw' in msystem:
        return 'GITBASH', emojis.get('git bash', '🪟')
    elif system == 'windows':
        return 'WINDOWS', emojis.get('windows', '🪟')
    else:
        return 'UNKNOWN', emojis.get('unknown', '❓')


def format_usage(usage_data):
    if not usage_data:
        return ""

    prompt = usage_data.get('prompt_tokens', 0)
    completion = usage_data.get('completion_tokens', 0)
    total = usage_data.get('total_tokens', 0)

    return f"{USAGE_EMOJI} Tokens used: {PROMPT_EMOJI} Prompt={prompt}, " \
           f"{RESPONSE_EMOJI} Response={completion}, " \
           f"{TOTAL_EMOJI} Total={total}"


def get_cost(USE_OLLAMA, MODEL_TIER):
    if USE_OLLAMA:
        return ENERGY_EMOJI
    if MODEL_TIER == "cheap":
        return CHEAP_EMOJI
    return EXPENSIVE_EMOJI


def get_commit_count():
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        count = int(result.stdout.strip())
        return count
    except Exception:
        return 0


if __name__ == "__main__":
    env, emoji = detect_environment()
    print(f"Detected environment: {ENVIRONMENT_EMOJI} {env} {emoji}")
