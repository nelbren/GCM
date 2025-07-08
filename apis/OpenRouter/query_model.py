import os
import re
import sys
import json
import time
import random
import secrets
import requests

sys.path.append('../..')
from utils import detect_environment


DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "FreeAll")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_API_KEY = OPENROUTER_API_KEY.strip()
random.seed(secrets.randbits(64))


def load_blacklist(filename="blacklist.txt"):
    if not os.path.exists(filename):
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_to_blacklist(model, filename="blacklist.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{model}\n")


def extract_model_size(model_id):
    """
    Returns the approximate number of parameters in millions.
    """
    match = re.search(r'(\d+)([bm])', model_id.lower())
    if not match:
        return 0
    size = int(match.group(1))
    scale = match.group(2)
    return size * (1_000 if scale == 'b' else 1)  # 1B = 1000M


def list_free_models(selection="FreeAll", top_n=5):
    blacklist = load_blacklist()

    r = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    )

    models = r.json().get("data", [])

    free = [
        m for m in models
        if (
            m.get("pricing", {}).get("prompt") == "0" and
            m.get("pricing", {}).get("completion") == "0"
        )
    ]

    if not free:
        return []

    if DEBUG:
        print(f"🔍 Free models found: {len(free)}")

    detailed_models = []
    for m in free:
        model_id = m["id"]
        if model_id in blacklist:
            continue  # Ignorar modelos en blacklist

        context = m.get("context_length", 0)
        size = extract_model_size(model_id)
        detailed_models.append({
            "id": model_id,
            "context": context,
            "size": size,
            "description": m.get("description", "")
        })

        if DEBUG:
            print(f'🧠 Model: {model_id}')
            # print(f'🗨️ Description: {m.get("description", "")}…')  # [:60]
            print(f'📦 Params: {size}M')
            print(f'🧵 CTX: {context}\n')

    if not detailed_models:
        print("⚠️ There are no valid models "
              "available after applying blacklist.")
        return []

    if selection == "FreeAll":
        return [m["id"] for m in detailed_models]

    elif selection == "FreeTop":
        sorted_models = sorted(detailed_models, key=lambda
                               m: m["size"], reverse=True)
        return [m["id"] for m in sorted_models[:top_n]]

    elif selection == "FreeCtxMax":
        sorted_models = sorted(detailed_models, key=lambda
                               m: m["context"], reverse=True)
        return [m["id"] for m in sorted_models[:top_n]]

    elif selection == "FreeSmart":
        sorted_models = sorted(
            detailed_models,
            key=lambda m: (m["size"] * 0.7) + (m["context"] / 1000 * 0.3),
            reverse=True
        )
        return [m["id"] for m in sorted_models[:top_n]]

    else:
        random_model = random.choice(detailed_models)
        return [random_model["id"]]


def query_with_fallback(models_to_use, prompt):
    provider = "OpenRouter"
    attempted_models = set()

    for model in random.sample(models_to_use, len(models_to_use)):
        if model in attempted_models:
            continue  # Ya intentado, lo saltamos

        attempted_models.add(model)

        start_time = time.time()
        print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...", end='', flush=True)

        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                })
            )
            elapsed_time = time.time() - start_time
            code = response.status_code

            if code == 200:
                print("✅")
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                usage_data = data.get("usage", {})
                usage = {
                    "prompt_tokens": usage_data.get("prompt_tokens", 0),
                    "completion_tokens":
                        usage_data.get("completion_tokens", 0),
                    "total_tokens": usage_data.get("total_tokens", 0)
                }
                return code, model, content, usage, elapsed_time
            # if "error" in data:
            #     error = data["error"]["message"]
            # print(f"❌ ({code}: {error})")

            elif response.status_code == 404:
                print(f"🚫 Model not fount (404): {model}")
                save_to_blacklist(model)
                continue  # Try the following model

            else:
                print(f"❌ Error {code} with model {model}")
                continue

        except Exception as e:
            print(f"❌ Exception with model {model}: {e}")
            continue

    print("❌ No valid model responded.")
    return 666, None, "No response could be obtained from any model.", None, 0


def query_model(prompt):
    if not OPENROUTER_API_KEY:
        return 0, None, None, None, 0

    keywords = {"FreeAll", "FreeTop", "FreeCtxMax", "FreeSmart"}
    model = OPENROUTER_MODEL

    if model in keywords:
        models_to_use = list_free_models(OPENROUTER_MODEL)
        # print("models_to_use -> ", models_to_use)
        model = random.choice(models_to_use)
        # print("model ->", model)

    # model = model.strip()
    return query_with_fallback(models_to_use, prompt)

    # return code, model, final_response, usage, elapsed_time


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) > 0 and argv[0] == "list":
        free_models = list_free_models()
        print("Free models:")
        print("------------")
        for model in free_models:
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
