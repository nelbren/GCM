import os
import sys
import time
import json
import random
import requests
from openai import OpenAI

DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
MODEL_TIER = os.getenv("MODEL_TIER", "cheap")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def list_models():
    models = []
    response = requests.get(
        "https://api.openai.com/v1/models",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
    )

    if response.status_code == 200:
        models_availables = response.json().get("data", [])
        for m in models_availables:
            models.append(m["id"])
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

    return models


def query_model(prompt):
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
    print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...\n")
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
        if DEBUG:
            print(response.status_code)
        return code, model, response, usage, elapsed_time

    return code, model, content, usage, elapsed_time


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) > 0 and argv[0] == "list":
        models = list_models()
        for model in models:
            print(model)
        exit(0)
    prompt = "What is the meaning of life?"
    code, model, content, usage, elapsed_time = query_model(prompt)
    print(f"🌐 Code: {code}")
    print(f"🧠 Model: {model}")
    print(f"💬 Response: {content}")
    print(f"📊 Usage: {usage}")
    print(f"⏱️ Elapsed time: {elapsed_time:.2f} seconds")
