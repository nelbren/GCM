import os
import time

from openai import OpenAI, OpenAIError


CODEX_API_KEY = os.getenv("CODEX_API_KEY", "").strip()
CODEX_MODEL = os.getenv("CODEX_MODEL", "gpt-5-codex").strip()


def safe_print(message, **kwargs):
    try:
        print(message, **kwargs)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="ignore").decode("ascii")
        print(fallback or "[message could not be displayed in this terminal]",
              **kwargs)


def query_model(prompt):
    if not CODEX_API_KEY:
        return 0, None, None, None, 0

    start_time = time.time()
    model = CODEX_MODEL
    provider = "Codex"
    safe_print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...", end='', flush=True)

    response = None
    usage = None
    try:
        client = OpenAI(api_key=CODEX_API_KEY)
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=400
        )
        content = (getattr(response, "output_text", "") or "").strip()
        raw_usage = getattr(response, "usage", None)
        if raw_usage is not None:
            usage = {
                "prompt_tokens": getattr(raw_usage, "input_tokens", 0) or 0,
                "completion_tokens": getattr(raw_usage, "output_tokens", 0) or 0,
                "total_tokens": getattr(raw_usage, "total_tokens", 0) or 0,
            }
        else:
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        safe_print("✅")
        return 200, model, content, usage, time.time() - start_time
    except OpenAIError as e:
        safe_print(f"❌ {getattr(e, 'status_code', 500) or 500})")
        return (
            getattr(e, "status_code", 500) or 500,
            model,
            str(e),
            usage,
            time.time() - start_time,
        )
