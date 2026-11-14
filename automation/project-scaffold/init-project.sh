#!/usr/bin/env bash
# ==============================================================================
# Youchen Project Scaffolding CLI Wrapper (Bash / POSIX Edition)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_SCRIPT="${SCRIPT_DIR}/scaffold_engine.py"

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
  echo "Error: python3 or python executable is required to run the scaffolding engine." >&2
  exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
  PYTHON_CMD="python"
fi

exec "${PYTHON_CMD}" "${ENGINE_SCRIPT}" "$@"
