#!/bin/bash

gcm_repo_python() {
    local script_dir="$1"

    if [ -x "${script_dir}/.venv/bin/python" ]; then
        printf '%s\n' "${script_dir}/.venv/bin/python"
        return 0
    fi

    if [ -x "${script_dir}/.venv/Scripts/python" ]; then
        printf '%s\n' "${script_dir}/.venv/Scripts/python"
        return 0
    fi

    if [ -x "${script_dir}/.venv/Scripts/python.exe" ]; then
        printf '%s\n' "${script_dir}/.venv/Scripts/python.exe"
        return 0
    fi

    return 1
}

gcm_require_repo_python() {
    local script_dir="$1"
    local python_bin

    python_bin="$(gcm_repo_python "$script_dir")" || {
        echo "❌ Virtual environment .venv not found. Run install.bat first."
        return 1
    }

    printf '%s\n' "$python_bin"
}

gcm_source_provider_secrets() {
    local script_dir="$1"
    local base_dir="${script_dir}/apis"
    local dir
    local secret_file

    for dir in "$base_dir"/*/; do
        secret_file="${dir}secret.bash"

        if [ ! -f "$secret_file" ]; then
            echo "❌ $secret_file not found. Abort."
            echo "👉 cp $secret_file.example $secret_file"
            return 1
        fi

        source "$secret_file"
    done
}

gcm_export_terminal_env() {
    export MSYSTEM
    export OSTYPE
}

gcm_run_repo_python() {
    local script_dir="$1"
    local target_script="$2"
    shift 2

    local python_bin
    python_bin="$(gcm_require_repo_python "$script_dir")" || return 1

    gcm_export_terminal_env

    if [ "$OSTYPE" = "cygwin" ]; then
        local win_script_dir
        win_script_dir="$(cygpath -w "$script_dir")"
        "$win_script_dir/.venv/Scripts/python.exe" "$win_script_dir/$target_script" "$@"
        return $?
    fi

    "$python_bin" "${script_dir}/${target_script}" "$@"
}
