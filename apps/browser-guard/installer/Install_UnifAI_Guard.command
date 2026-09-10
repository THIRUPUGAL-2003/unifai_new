#!/bin/bash
# Double-click or run in Terminal to install UnifAI Guard on this Mac.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
APP_SRC="$DIR/UnifAI_Guard.app"
DEST="/Applications/UnifAI_Guard.app"

echo "============================================================"
echo " UnifAI Guard — macOS install"
echo "============================================================"

if [[ ! -d "$APP_SRC" ]]; then
  osascript -e 'display dialog "UnifAI_Guard.app not found next to this installer.\nUnzip UnifAI_Guard_macOS.zip fully, then run Install_UnifAI_Guard.command again." with title "UnifAI Guard" buttons {"OK"} default button 1 with icon stop' || true
  echo "ERROR: Missing $APP_SRC"
  exit 1
fi

# Clear quarantine so Gatekeeper does not block unsigned / first-run apps from ZIP
xattr -dr com.apple.quarantine "$APP_SRC" 2>/dev/null || true

if [[ -d "$DEST" ]]; then
  echo "Removing previous install at $DEST ..."
  # Prefer clean stop via LaunchAgent unload
  PLIST="$HOME/Library/LaunchAgents/com.unifai.guard.plist"
  if [[ -f "$PLIST" ]]; then
    launchctl unload "$PLIST" 2>/dev/null || true
  fi
  pkill -f "/Applications/UnifAI_Guard.app/Contents/MacOS/UnifAI_Guard" 2>/dev/null || true
  sleep 1
  rm -rf "$DEST"
fi

echo "Copying to /Applications ..."
cp -R "$APP_SRC" "$DEST"
xattr -dr com.apple.quarantine "$DEST" 2>/dev/null || true

# Prefer config from package next to installer
if [[ -f "$DIR/unifai_guard_config.json" ]]; then
  mkdir -p "$DEST/Contents/Resources"
  cp "$DIR/unifai_guard_config.json" "$DEST/Contents/Resources/unifai_guard_config.json"
fi

echo "Starting Guard (registers LaunchAgent + system PAC) ..."
open "$DEST"

osascript -e 'display dialog "UnifAI Guard installed.\n\n1) Fully quit Safari/Chrome/Edge/Firefox\n2) Reopen browsers\n3) Visit a monitored AI site\n\nHealth: http://127.0.0.1:18085/\n\nTo turn OFF / uninstall: run Uninstall_UnifAI_Guard.command" with title "UnifAI Guard" buttons {"OK"} default button 1 with icon note' || true

echo "Done. Health check: open http://127.0.0.1:18085/"
echo "Off / uninstall: double-click Uninstall_UnifAI_Guard.command"
