#!/usr/bin/env bash
# UnifAI Guard — macOS uninstall helper
set -euo pipefail

WRAPPER="${UNIFAI_GUARD_HOME:-$HOME/Library/Application Support/UnifAI/Guard/runtime}/UnifAI_Guard"
PLIST="$HOME/Library/LaunchAgents/com.unifai.guard.plist"
DATA_DIR="$HOME/Library/Application Support/UnifAI/Guard"
INSTALL_ROOT="${UNIFAI_GUARD_HOME:-$HOME/Library/Application Support/UnifAI/Guard/runtime}"

echo "UnifAI Guard macOS uninstall"
if [[ -x "$WRAPPER" ]]; then
  if [[ "${1:-}" == "--key" && -n "${2:-}" ]]; then
    "$WRAPPER" --uninstall "$2" || true
  else
    "$WRAPPER" --uninstall-prompt || true
  fi
fi

launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"

# Best-effort: turn off auto proxy on common services
for svc in "Wi-Fi" "Ethernet" "USB 10/100/1000 LAN" "Thunderbolt Bridge"; do
  networksetup -setautoproxystate "$svc" off 2>/dev/null || true
done

echo "LaunchAgent removed. Runtime left at: $INSTALL_ROOT"
echo "To wipe files:  rm -rf \"$INSTALL_ROOT\" \"$DATA_DIR\""
echo "(Only wipe after successful --uninstall with company key if required.)"
