#!/usr/bin/env bash
# UnifAI Guard — macOS install (test + employee). Run on a Mac.
# Usage:  chmod +x install_macos.sh && ./install_macos.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_URL="${UNIFAI_BACKEND_URL:-}"
INSTALL_ROOT="${UNIFAI_GUARD_HOME:-$HOME/Library/Application Support/UnifAI/Guard/runtime}"
DATA_DIR="$HOME/Library/Application Support/UnifAI/Guard"
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
PLIST_NAME="com.unifai.guard.plist"
PLIST_PATH="$LAUNCH_AGENTS/$PLIST_NAME"
PYTHON_BIN="${PYTHON:-python3}"

echo "=========================================================="
echo "  UnifAI Guard — macOS setup"
echo "=========================================================="

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: This installer only runs on macOS."
  exit 1
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Xcode CLT or python.org, then retry."
  exit 1
fi

# Backend from env, or bundled config, or default
if [[ -z "$BACKEND_URL" ]]; then
  if [[ -f "$SCRIPT_DIR/config/unifai_guard_config.json" ]]; then
    BACKEND_URL="$(
      "$PYTHON_BIN" -c "import json; print(json.load(open('$SCRIPT_DIR/config/unifai_guard_config.json')).get('backend_url',''))" 2>/dev/null || true
    )"
  fi
fi
BACKEND_URL="${BACKEND_URL:-https://unifaiv2.dev-yp.com}"
BACKEND_URL="${BACKEND_URL%/}"

echo "Backend: $BACKEND_URL"
echo "Install: $INSTALL_ROOT"
echo ""

mkdir -p "$INSTALL_ROOT" "$DATA_DIR" "$LAUNCH_AGENTS"
mkdir -p "$INSTALL_ROOT/agent" "$INSTALL_ROOT/proxy"

# Copy product files
cp -f "$SCRIPT_DIR/agent/unifai_agent.py" "$INSTALL_ROOT/agent/"
cp -f "$SCRIPT_DIR/agent/guard_platform.py" "$INSTALL_ROOT/agent/"
cp -f "$SCRIPT_DIR/proxy/browser_ai_proxy.py" "$INSTALL_ROOT/proxy/"
if [[ -f "$SCRIPT_DIR/MAC_INSTALL.txt" ]]; then
  cp -f "$SCRIPT_DIR/MAC_INSTALL.txt" "$INSTALL_ROOT/"
fi

# Runtime config (exe_dir = agent parent = INSTALL_ROOT when we run from wrapper)
cat > "$INSTALL_ROOT/unifai_guard_config.json" <<EOF
{
  "backend_url": "$BACKEND_URL",
  "proxy_addr": "127.0.0.1:8085"
}
EOF
cp -f "$INSTALL_ROOT/unifai_guard_config.json" "$DATA_DIR/unifai_guard_config.json"

# venv + deps
VENV="$INSTALL_ROOT/.venv"
if [[ ! -x "$VENV/bin/python" ]]; then
  echo "==> Creating Python venv..."
  "$PYTHON_BIN" -m venv "$VENV"
fi
echo "==> Installing mitmproxy / pypdf / pillow..."
"$VENV/bin/python" -m pip install -U pip wheel >/dev/null
"$VENV/bin/python" -m pip install -U "mitmproxy>=10" pypdf pillow

# Launcher (same role as UnifAI_Guard.exe on Windows)
WRAPPER="$INSTALL_ROOT/UnifAI_Guard"
cat > "$WRAPPER" <<'EOF'
#!/usr/bin/env bash
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT/agent${PYTHONPATH:+:$PYTHONPATH}"
# Frozen-style: config next to "exe"
cd "$ROOT"
exec "$ROOT/.venv/bin/python" "$ROOT/agent/unifai_agent.py" "$@"
EOF
chmod +x "$WRAPPER"

# Symlink for easy CLI
mkdir -p "$HOME/bin" 2>/dev/null || true
ln -sf "$WRAPPER" "$HOME/bin/UnifAI_Guard" 2>/dev/null || true

# LaunchAgent — start at login
cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.unifai.guard</string>
  <key>ProgramArguments</key>
  <array>
    <string>$WRAPPER</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>WorkingDirectory</key>
  <string>$INSTALL_ROOT</string>
  <key>StandardOutPath</key>
  <string>$DATA_DIR/launchd.out.log</string>
  <key>StandardErrorPath</key>
  <string>$DATA_DIR/launchd.err.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH" 2>/dev/null || launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true

# Start now
echo "==> Starting UnifAI Guard..."
launchctl start com.unifai.guard 2>/dev/null || "$WRAPPER" &
sleep 2

echo ""
echo "=========================================================="
echo "  INSTALL OK — Mac Guard is ready to test"
echo "=========================================================="
echo "1) Fully quit Safari / Chrome / Firefox / Edge (Cmd+Q)"
echo "2) Reopen browser → open a monitored AI website"
echo "3) Send a test prompt"
echo "4) Admin: Browser AI → Prompt Logs + Agents"
echo ""
echo "Logs:  $DATA_DIR/unifai_guard.log"
echo "Data:  $DATA_DIR"
echo "Run:   $WRAPPER"
echo "Stop:  launchctl unload \"$PLIST_PATH\""
echo "Uninstall key prompt:  $WRAPPER --uninstall-prompt"
echo ""
echo "If HTTPS warnings appear: Keychain → mitmproxy → Trust → Always Trust"
echo "=========================================================="
