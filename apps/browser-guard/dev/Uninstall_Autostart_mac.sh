#!/bin/bash
# Dev helper: stop Guard + remove LaunchAgent (does NOT verify uninstall key / clear PAC).
# For full OFF + PAC clear, use installer/Uninstall_UnifAI_Guard.command instead.
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/com.unifai.guard.plist"
if [[ -f "$PLIST" ]]; then
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "LaunchAgent removed."
fi
pkill -f "UnifAI_Guard.app/Contents/MacOS/UnifAI_Guard" 2>/dev/null || true
pkill -f "/MacOS/UnifAI_Guard" 2>/dev/null || true
echo "Guard process stopped (if it was running)."
echo "NOTE: PAC may still be on. Use Uninstall_UnifAI_Guard.command to clear proxy properly."
