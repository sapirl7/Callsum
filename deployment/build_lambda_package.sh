#!/bin/bash
# Сборка артефакта Lambda с vendored Python зависимостями.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="$ROOT_DIR/telegram_bot"
BUILD_DIR="$SOURCE_DIR/build/lambda"

echo "📦 Сборка Lambda package..."

/bin/rm -rf "$BUILD_DIR"
/bin/mkdir -p "$BUILD_DIR"

python3 -m pip install \
  --upgrade \
  --target "$BUILD_DIR" \
  -r "$SOURCE_DIR/requirements.txt"

/bin/cp "$SOURCE_DIR/bot.py" "$BUILD_DIR/bot.py"

echo "✅ Lambda package готов: $BUILD_DIR"
