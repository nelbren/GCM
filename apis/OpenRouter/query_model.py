import os
import sys
import json
import time
import random
import requests

DEBUG = os.getenv("DEBUG", "False")
DEBUG = True if DEBUG == "True" else False
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "FreeAll")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def list_free_models(selection="FreeAll"):
    # free_models = []
    r = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    )

    models = r.json().get("data", [])

    # Filtrar modelos gratuitos
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
        print(f"🔍 Modelos gratuitos encontrados: {len(free)}")

    # Preparar la lista de modelos con datos relevantes
    detailed_models = []
    for m in free:
        detailed_models.append({
            "id": m["id"],
            "context": m.get("context_length", 0),
            "description": m.get("description", "")
        })
        if DEBUG:
            print(f'🧠 Model: {m["id"]}')
            print(f'🗨️ Description: {m.get("description", "")}…')  # [:60]
            print(f'🧵 CTX: {m.get("context_length", 0)}\n')

    if selection == "FreeAll":
        return [m["id"] for m in detailed_models]

    elif selection == "FreeTop":
        top_model = max(detailed_models, key=lambda m: m["id"])
        return [top_model["id"]]

    elif selection == "FreeCtxMax":
        top_ctx_model = max(detailed_models, key=lambda m: m["context"])
        return [top_ctx_model["id"]]

    else:
        random_model = random.choice(detailed_models)
        return [random_model["id"]]


def query_model(prompt):
    usage = None
    start_time = time.time()

    keywords = {"FreeAll", "FreeTop", "FreeCtxMax"}
    model = OPENROUTER_MODEL

    if model in keywords:
        models_to_use = list_free_models(OPENROUTER_MODEL)
        model = random.choice(models_to_use)

    provider = "OpenRouter"
    print(f"🔍 Consulting 🤖 {provider} 🧠 {model}...\n")

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        data=json.dumps({
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })
    )
    elapsed_time = time.time() - start_time
    code = response.status_code
    data = response.json()

    if DEBUG:
        print(json.dumps(data, indent=4))

    if code != 200:
        if DEBUG:
            print(response.status_code)
        return code, model, response, usage, elapsed_time

    usage_data = data.get("usage", {})
    usage = {
        "prompt_tokens": usage_data.get("prompt_tokens", 0),
        "completion_tokens": usage_data.get("completion_tokens", 0),
        "total_tokens": usage_data.get("total_tokens", 0)
    }

    try:
        message = data["choices"][0]["message"]
        content = message.get("content", "").strip()
        reasoning = (message.get("reasoning") or "").strip()

        if content:
            final_response = content
        elif reasoning:
            final_response = reasoning
        else:
            final_response = "⚠️ A valid response could not be obtained."

    except (KeyError, IndexError):
        code = 666
        final_response = "❌ Could not get response from model."

    return code, model, final_response, usage, elapsed_time


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) > 0 and argv[0] == "list":
        free_models = list_free_models()
        for model in free_models:
            print(model)
        exit(0)
    prompt = "What is the meaning of life?"
    code, model, content, usage, elapsed_time = query_model(prompt)
    print(f"🌐 Code: {code}")
    print(f"🧠 Model: {model}")
    print(f"💬 Response: {content}")
    print(f"📊 Usage: {usage}")
    print(f"⏱️ Elapsed time: {elapsed_time:.2f} seconds")
