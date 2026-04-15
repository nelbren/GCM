import os
import sys
import time
import json
import random
import requests
from openai import OpenAI, OpenAIError

sys.path.append('../..')
from utils import detect_environment  # noqa: E402


DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
MODEL_TIER = os.getenv("MODEL_TIER", "cheap").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()


def safe_print(message, **kwargs):
    try:
        print(message, **kwargs)
    except UnicodeEncodeError:
        fallback = message.encode("ascii", errors="ignore").decode("ascii")
        print(fallback or "[message could not be displayed in this terminal]",
              **kwargs)


def list_models():
    code = None
    models = []
    try:
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
        )
        data = response.json()
        code = response.status_code
    except requests.exceptions.HTTPError as e:
        code = response.status_code
        error = f"Error HTTP: {e.response.status_code}"

    if code == 200:
        models_availables = response.json().get("data", [])
        for m in models_availables:
            models.append(m["id"])
    else:
        if "error" in data:
            error = data["error"]["message"]
        safe_print(f"❌ ({code}: {error}")
        if DEBUG:
            safe_print(response.text)

    return models


def query_model(prompt):
    if not OPENAI_API_KEY:
        return 0, None, None, None, 0
    usage = None
    start_time = time.time()

    if MODEL_TIER == "cheap":
        OPENAI_MODEL = "gpt-5-nano"
    elif MODEL_TIER == "premium":
        OPENAI_MODEL = "gpt-5.2"
    else:
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    model = OPENAI_MODEL
    if model == "RANDOM":
        models = list_models()
        model = random.choice(models)

    provider = "OpenAI"
    model = model.strip()
    safe_print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...", end='', flush=True)
    code = 500
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=400
        )
        code = 200

        if DEBUG:
            data = response.json()
            safe_print(json.dumps(data, indent=4))

        content = (getattr(response, "output_text", "") or "").strip()

        usage = getattr(response, "usage", None)
        if usage is not None:
            usage = {
                "prompt_tokens": getattr(usage, "input_tokens", 0) or 0,
                "completion_tokens": getattr(usage, "output_tokens", 0) or 0,
                "total_tokens": getattr(usage, "total_tokens", 0) or 0,
            }
        else:
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

    except OpenAIError as e:
        code = getattr(e, "status_code", 500) or 500
        content = f"❌ ERROR = {e}"
    finally:
        elapsed_time = time.time() - start_time

    if code != 200:
        safe_print(f"❌ {code})")
        if DEBUG:
            safe_print(str(response))
        return code, model, response, usage, elapsed_time
    else:
        safe_print("✅")

    return code, model, content, usage, elapsed_time


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) > 0 and argv[0] == "list":
        models = list_models()
        safe_print("List models:")
        safe_print("------------")
        for model in models:
            safe_print(model)
        exit(0)
    env, emoji = detect_environment()
    prompt = "What is the meaning of life?"
    code, model, content, usage, elapsed_time = query_model(prompt)
    safe_print(f"🌐 Code: {code}")
    safe_print(f"🧠 Model: {model}")
    safe_print(f"💬 Response: {content}")
    safe_print(f"📊 Usage: {usage}")
    fix = " " if env == "MACOS" else ""
    safe_print(f"⏱️{fix} Elapsed time: {elapsed_time:.2f} seconds")
