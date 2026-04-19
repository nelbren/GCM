import os
import time

import requests


ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-latest").strip()


def safe_print(message, **kwargs):
    try:
        print(message, **kwargs)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="ignore").decode("ascii")
        print(fallback or "[message could not be displayed in this terminal]",
              **kwargs)


def query_model(prompt):
    if not ANTHROPIC_API_KEY:
        return 0, None, None, None, 0

    start_time = time.time()
    provider = "Claude"
    model = CLAUDE_MODEL
    safe_print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...", end='', flush=True)

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 400,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
            },
            timeout=60,
        )
        data = response.json()
        if response.status_code != 200:
            safe_print(f"❌ {response.status_code})")
            error = data.get("error", {}).get("message", response.text)
            return response.status_code, model, error, None, time.time() - start_time

        content_blocks = data.get("content", [])
        content = "".join(
            block.get("text", "") for block in content_blocks
            if block.get("type") == "text"
        ).strip()
        usage_data = data.get("usage", {})
        usage = {
            "prompt_tokens": usage_data.get("input_tokens", 0),
            "completion_tokens": usage_data.get("output_tokens", 0),
            "total_tokens": usage_data.get("input_tokens", 0) +
                            usage_data.get("output_tokens", 0),
        }
        safe_print("✅")
        return 200, model, content, usage, time.time() - start_time
    except requests.RequestException as e:
        safe_print("❌ 500)")
        return 500, model, str(e), None, time.time() - start_time
