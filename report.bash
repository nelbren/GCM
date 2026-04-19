#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_bash_common.bash"

if [ ! -f "${SCRIPT_DIR}/config.yml" ]; then
    echo "❌ ${SCRIPT_DIR}/config.yml not found. Abort."
    exit 1
fi

gcm_run_repo_python "${SCRIPT_DIR}" "report_history.py" "$@"
