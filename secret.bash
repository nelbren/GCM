#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for provider in OpenRouter OpenAI Ollama; do
    SECRET_FILE="${SCRIPT_DIR}/apis/${provider}/secret.bash"

    if [ -f "$SECRET_FILE" ]; then
        echo "🔐 Setting Keys for ${provider} Secret File..."
        source "$SECRET_FILE"
    fi
done
