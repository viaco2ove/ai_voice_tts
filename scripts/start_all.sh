#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_PATH="${1:-config/services.yaml}"

if [ ! -d ".venv" ]; then
  echo ".venv 不存在，请先创建虚拟环境" >&2
  exit 1
fi

source .venv/bin/activate
export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"
python -m src.voice_service.launcher --config "$CONFIG_PATH"
