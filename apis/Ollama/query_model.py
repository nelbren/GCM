import os
import sys
import time
import json
import random
import requests

sys.path.append('../..')
from utils import detect_environment

DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "").strip()
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "").strip()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "localhost:11434").strip()


def list_models():
    models = []
    response = requests.get(f"http://{OLLAMA_HOST}/api/tags")

    if response.status_code == 200:
        models_availables = response.json().get("models", [])
        for m in models_availables:
            models.append(m["name"])
    else:
        print(f"❌ Error: {response.status_code}")
        print(response.text)

    return models


def query_model(prompt):
    if not OLLAMA_API_KEY:
        return 0, None, None, None, 0
    usage = None
    start_time = time.time()

    model = OLLAMA_MODEL
    if model == "RANDOM":
        models = list_models()
        model = random.choice(models)

    provider = "Ollama"
    model = model.strip()
    print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...", end='', flush=True)
    response = None
    error = None
    code = 666
    try:
        response = requests.post(
            f"http://{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        data = response.json()
        content = response.json()["response"].strip()
        code = response.status_code
        error = ""
    except requests.exceptions.ConnectionError:
        error = "Ollama is not running or cannot connect."

    except requests.exceptions.Timeout:
        error = "Timeout occurred while trying to contact Ollama."

    except requests.exceptions.HTTPError as e:
        error = f"Error HTTP: {e.response.status_code}"

    except requests.exceptions.RequestException as e:
        error = f"Error inesperado: {e}"

    except KeyError:
        if "error" in data:
            error = data["error"]

    if DEBUG:
        print(json.dumps(data, indent=4))

    elapsed_time = time.time() - start_time

    if code != 200:
        print(f"❌ ({code}: {error})")
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
        print("List models:")
        print("------------")
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
