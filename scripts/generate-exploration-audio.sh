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
REQUIREMENTS="$ROOT_DIR/requirements-audio.txt"

if [[ ! -x "$PYTHON" ]]; then
  echo "Creating Python virtual environment..."
  python3 -m venv "$VENV_DIR"
fi

if ! "$PYTHON" -c "import requests, yaml" >/dev/null 2>&1; then
  echo "Installing audio dependencies..."
  "$PYTHON" -m pip install --quiet -r "$REQUIREMENTS"
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Error: ffmpeg is required for exploration audio generation." >&2
  exit 1
fi

exec "$PYTHON" "$ROOT_DIR/scripts/generate_exploration_audio.py" "$@"