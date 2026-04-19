#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_bash_common.bash"

PYTHON_BIN="$(gcm_require_repo_python "${SCRIPT_DIR}")" || exit 1

gcm_export_terminal_env
"${PYTHON_BIN}" "${SCRIPT_DIR}/test_runner.py"
