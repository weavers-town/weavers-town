#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
elif [[ -f "$ROOT_DIR/../threads-of-meaning/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/../threads-of-meaning/.env"
  set +a
fi

VENV_DIR="$ROOT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
REQUIREMENTS="$ROOT_DIR/requirements-translation.txt"

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON" -c "import openai, yaml" >/dev/null 2>&1; then
  "$PYTHON" -m pip install --quiet -r "$REQUIREMENTS"
fi

exec "$PYTHON" "$ROOT_DIR/scripts/translate_explorations.py" "$@"