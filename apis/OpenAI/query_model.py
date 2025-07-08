import os
import sys
import time
import json
import random
import requests
from openai import OpenAI

sys.path.append('../..')
from utils import detect_environment


DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
MODEL_TIER = os.getenv("MODEL_TIER", "cheap")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_KEY = OPENAI_API_KEY.strip()


def list_models():
    print("List models:")
    print("------------")
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
        print(f"❌ ({code}: {error}")
        if DEBUG:
            print(response.text)

    return models


def query_model(prompt):
    if not OPENAI_API_KEY:
        return 0, None, None, None, 0
    usage = None
    start_time = time.time()

    if MODEL_TIER == "cheap":
        OPENAI_MODEL = "gpt-3.5-turbo"
    elif MODEL_TIER == "premium":
        OPENAI_MODEL = "gpt-4o"
    else:
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

    model = OPENAI_MODEL
    if model == "RANDOM":
        models = list_models()
        model = random.choice(models)

    provider = "OpenAI"
    model = model.strip()
    print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...", end='', flush=True)
    code = None
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=400
        )
        code = 200
    except client.error.OpenAIError as e:
        code = getattr(e, 'http_status', 500)
        return code, None, str(e), None, 0

    elapsed_time = time.time() - start_time

    if DEBUG:
        data = response.json()
        print(json.dumps(data, indent=4))

    content = response.choices[0].message.content.strip()
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens
    }

    if code != 200:
        print(f"❌ {code})")
        if DEBUG:
            print(response.status_code)
        return code, model, response, usage, elapsed_time
    else:
        print("✅")

    return code, model, content, usage, elapsed_time


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) > 0 and argv[0] == "list":
        models = list_models()
        for model in models:
            print(model)
        exit(0)
    env, emoji = detect_environment()
    prompt = "What is the meaning of life?"
    code, model, content, usage, elapsed_time = query_model(prompt)
    print(f"🌐 Code: {code}")
    print(f"🧠 Model: {model}")
    print(f"💬 Response: {content}")
    print(f"📊 Usage: {usage}")
    fix = " " if env == "MACOS" else ""
    print(f"⏱️{fix} Elapsed time: {elapsed_time:.2f} seconds")
