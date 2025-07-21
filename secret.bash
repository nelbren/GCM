#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source $SCRIPT_DIR/apis/OpenRouter/secret.bash
source $SCRIPT_DIR/apis/OpenAI/secret.bash
source $SCRIPT_DIR/apis/Ollama/secret.bash

if [ -f "$SCRIPT_DIR/apis/OpenRouter/secret.bash" ]; then
    echo 🔐 Setting Keys for OpenRouter Secret File...
    source "$SCRIPT_DIR/apis/OpenRouter/secret.bash"
fi

if [ -f "$SCRIPT_DIR/apis/OpenAI/secret.bash" ]; then
    echo 🔐 Setting Keys for OpenAI Secret File...
    source "$SCRIPT_DIR/apis/OpenAI/secret.bash"
fi

if [ -f "$SCRIPT_DIR/apis/Ollama/secret.bash" ]; then
    echo 🔐 Setting Keys for Ollama Secret File...
    source "$SCRIPT_DIR/apis/Ollama/secret.bash"
fi
