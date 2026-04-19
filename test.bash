#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/_bash_common.bash"

gcm_run_repo_python "${SCRIPT_DIR}" "test_runner.py" "$@"
