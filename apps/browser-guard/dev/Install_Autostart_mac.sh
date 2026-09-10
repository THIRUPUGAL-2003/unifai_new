#!/bin/bash
# Dev helper: register LaunchAgent for a local UnifAI_Guard.app in this folder.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/UnifAI_Guard.app"
BIN="$APP/Contents/MacOS/UnifAI_Guard"
if [[ ! -x "$BIN" ]]; then
  echo "ERROR: $BIN not found. Build with installer/build_macos.sh first."
  exit 1
fi
"$BIN" &
echo "Started. Autostart registers on first frozen run."
echo "Health: http://127.0.0.1:18085/"
