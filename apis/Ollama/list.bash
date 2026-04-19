#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
source "${REPO_DIR}/_bash_common.bash"
source "${SCRIPT_DIR}/secret.bash"
PYTHON_BIN="$(gcm_require_repo_python "${REPO_DIR}")" || exit 1
cd "${SCRIPT_DIR}" || exit 1
"${PYTHON_BIN}" "query_model.py" list
