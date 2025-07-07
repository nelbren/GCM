import os
import sys
import time
import json
import random
import requests

DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
OLLAMA_API_KEY = os.getenv("OPENAI_API_KEY")


def list_models():
    models = []
    response = requests.get("http://localhost:11434/api/tags")

    if response.status_code == 200:
        models_availables = response.json().get("models", [])
        for m in models_availables:
            models.append(m["name"])
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

    return models


def query_model(prompt):
    usage = None
    start_time = time.time()

    model = OLLAMA_MODEL
    if model == "RANDOM":
        models = list_models()
        model = random.choice(models)

    provider = "Ollama"
    print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...\n")

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }
    )

    if DEBUG:
        data = response.json()
        print(json.dumps(data, indent=4))

    content = response.json()["response"].strip()

    elapsed_time = time.time() - start_time
    code = response.status_code

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
