#!/usr/bin/env bash
set -euo pipefail

MODEL_URL_DEFAULT="https://alphacephei.com/vosk/models/vosk-model-small-cn-0.22.zip"
TARGET_DIR_DEFAULT="models/vosk"

MODEL_URL="${1:-$MODEL_URL_DEFAULT}"
TARGET_DIR="${2:-$TARGET_DIR_DEFAULT}"
ARCHIVE_NAME="/tmp/vosk_model_$$.zip"

if command -v curl >/dev/null 2>&1; then
  DL_CMD=(curl -L -o "$ARCHIVE_NAME" "$MODEL_URL")
elif command -v wget >/dev/null 2>&1; then
  DL_CMD=(wget -O "$ARCHIVE_NAME" "$MODEL_URL")
else
  echo "need curl or wget" >&2
  exit 1
fi

if ! command -v unzip >/dev/null 2>&1; then
  echo "need unzip" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
"${DL_CMD[@]}"
unzip -q "$ARCHIVE_NAME" -d "$TARGET_DIR"

# If the zip contains a nested directory, move its contents up one level.
FIRST_DIR=$(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1 || true)
if [ -n "$FIRST_DIR" ]; then
  shopt -s dotglob
  mv "$FIRST_DIR"/* "$TARGET_DIR"/ 2>/dev/null || true
  rmdir "$FIRST_DIR" 2>/dev/null || true
  shopt -u dotglob
fi

rm -f "$ARCHIVE_NAME"

echo "Vosk model ready at: $TARGET_DIR"
