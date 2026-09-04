#!/usr/bin/env bash
# Build UnifAI Guard for macOS (must run on a Mac — cannot cross-build from Windows).
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
RELEASE="$ROOT/release"
mkdir -p "$RELEASE"

PYTHON="${PYTHON:-python3}"
BACKEND_URL="${UNIFAI_BACKEND_URL:-https://unifaiv2.dev-yp.com}"

echo "==> UnifAI Guard macOS build"
echo "    Python: $($PYTHON --version 2>&1)"
echo "    Backend baked into employee config: $BACKEND_URL"

$PYTHON -m pip install -U pip wheel
$PYTHON -m pip install -U pyinstaller mitmproxy pypdf pillow

# Employee runtime config (same pattern as Windows installer)
CFG_DIR="$ROOT/dist_mac_cfg"
mkdir -p "$CFG_DIR"
cat > "$CFG_DIR/unifai_guard_config.json" <<EOF
{
  "backend_url": "$BACKEND_URL",
  "proxy_addr": "127.0.0.1:8085"
}
EOF

# Copy config next to agent so frozen app can find it via exe_dir heuristics
mkdir -p "$ROOT/agent"
cp "$CFG_DIR/unifai_guard_config.json" "$ROOT/agent/unifai_guard_config.json" 2>/dev/null || true

$PYTHON -m PyInstaller --noconfirm --clean UnifAI_Guard_macos.spec

APP="$ROOT/dist/UnifAI Guard.app"
if [[ ! -d "$APP" ]]; then
  echo "ERROR: expected app bundle at: $APP"
  exit 1
fi

# Place config inside the app Resources / next to binary for load_runtime_config
MACOS_BIN="$APP/Contents/MacOS"
cp "$CFG_DIR/unifai_guard_config.json" "$MACOS_BIN/unifai_guard_config.json"
cp "$ROOT/MAC_INSTALL.txt" "$MACOS_BIN/MAC_INSTALL.txt" 2>/dev/null || true

ZIP_OUT="$RELEASE/UnifAI_Guard_macOS.zip"
rm -f "$ZIP_OUT"
(
  cd "$ROOT/dist"
  zip -r -y "$ZIP_OUT" "UnifAI Guard.app"
)
cp "$ROOT/MAC_INSTALL.txt" "$RELEASE/MAC_INSTALL.txt" 2>/dev/null || true

echo ""
echo "==> Done"
echo "    App:  $APP"
echo "    ZIP:  $ZIP_OUT"
echo "    Copy ZIP to server: apps/browser-guard/release/UnifAI_Guard_macOS.zip"
echo "    (or release/UnifAI_Guard_macOS.zip)"
echo ""
echo "Employee install: unzip → drag UnifAI Guard.app to /Applications → open once."
echo "First open may need: System Settings → Privacy & Security → Open Anyway"
