#!/usr/bin/env bash
# Build UnifAI Guard for macOS (.app + release ZIP). Run on a Mac.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Prefer Python 3.11+ (mitmproxy 10+). Override with: PYTHON=/path/to/python ./installer/build_macos.sh
if [[ -z "${PYTHON:-}" ]]; then
  for c in python3.13 python3.12 python3.11 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      PYTHON="$(command -v "$c")"
      break
    fi
  done
fi
if [[ -z "${PYTHON:-}" ]]; then
  echo "ERROR: Python 3.11+ required (mitmproxy 10)."
  exit 1
fi

PY_VER="$("$PYTHON" -c "import sys; print('%d.%d' % sys.version_info[:2])")"
PY_MAJOR="$("$PYTHON" -c "import sys; print(sys.version_info[0])")"
PY_MINOR="$("$PYTHON" -c "import sys; print(sys.version_info[1])")"
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 11 ) ]]; then
  echo "ERROR: $PYTHON is $PY_VER - need Python 3.11+ for Guard packaging."
  echo "Install: brew install python@3.12"
  echo "Then:    PYTHON=/opt/homebrew/bin/python3.12 ./installer/build_macos.sh"
  exit 1
fi

VERSION="$(tr -d '[:space:]\ufeff' < release/VERSION.txt 2>/dev/null || true)"
VERSION="${VERSION//$'\xef\xbb\xbf'/}"
if [[ -z "${VERSION}" ]]; then
  VERSION="$("$PYTHON" -c "import re, pathlib; t=pathlib.Path('agent/agent_config.py').read_text(encoding='utf-8'); m=re.search(r'AGENT_VERSION\\s*=\\s*[\"\\']([^\"\\']+)[\"\\']', t); print(m.group(1) if m else '0.0.0')")"
fi

echo "============================================================"
echo " UnifAI Guard macOS build  v${VERSION}"
echo " Python: $PYTHON ($PY_VER)"
echo "============================================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: Build macOS Guard on a Mac (PyInstaller cannot cross-compile Darwin)."
  exit 1
fi

for f in agent/unifai_agent.py proxy/browser_ai_proxy.py config/unifai_guard_config.json; do
  if [[ ! -f "$f" ]]; then
    echo "Missing $f"
    exit 1
  fi
done

# Preflight: modular agent + proxy parts (post-split layout)
for f in \
  agent/agent_config.py \
  agent/agent_health.py \
  agent/agent_heartbeat.py \
  agent/agent_lifecycle.py \
  agent/guard_platform.py \
  proxy/unifai_proxy_parts/MANIFEST.txt \
  proxy/unifai_proxy_parts/responses_inject.py \
  proxy/unifai_proxy_parts/responses_addon.py
do
  if [[ ! -f "$f" ]]; then
    echo "Missing $f (Mac build needs latest split layout — sync repo from Windows first)"
    exit 1
  fi
done
while IFS= read -r part || [[ -n "$part" ]]; do
  part="${part#"${part%%[![:space:]]*}"}"
  part="${part%"${part##*[![:space:]]}"}"
  part="${part#$'\xef\xbb\xbf'}"
  [[ -z "$part" ]] && continue
  if [[ ! -f "proxy/unifai_proxy_parts/$part" ]]; then
    echo "Missing proxy part from MANIFEST: $part"
    exit 1
  fi
done < proxy/unifai_proxy_parts/MANIFEST.txt

# Keep Info.plist version in sync with VERSION / agent_config
SPEC="$ROOT/UnifAI_Guard.macos.spec"
if [[ -f "$SPEC" ]]; then
  "$PYTHON" - "$SPEC" "$VERSION" <<'PY'
import pathlib, re, sys
spec, ver = pathlib.Path(sys.argv[1]), sys.argv[2]
text = spec.read_text(encoding="utf-8")
text2 = re.sub(
    r'("CFBundleShortVersionString":\s*")[^"]+(")',
    rf'\g<1>{ver}\g<2>',
    text,
)
text2 = re.sub(
    r'("CFBundleVersion":\s*")[^"]+(")',
    rf'\g<1>{ver}\g<2>',
    text2,
)
if text2 != text:
    spec.write_text(text2, encoding="utf-8")
    print(f"Updated {spec.name} bundle version → {ver}")
PY
fi

VENV="$ROOT/.venv-guard"
if [[ ! -d "$VENV" ]]; then
  echo "Creating venv at $VENV"
  "$PYTHON" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
PYTHON="$VENV/bin/python"

"$PYTHON" -m pip install -q --upgrade pip
"$PYTHON" -m pip install -q -r requirements-guard.txt

echo ""
echo "1) PyInstaller → UnifAI_Guard.app"
"$PYTHON" installer/build_agent.py

APP_REL="release/UnifAI_Guard.app"
if [[ ! -d "$APP_REL" ]]; then
  echo "ERROR: $APP_REL missing after build"
  exit 1
fi

echo ""
echo "2) Stage macOS employee package"
STAGE="installer/staging-mac"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP_REL" "$STAGE/UnifAI_Guard.app"
cp config/unifai_guard_config.json "$STAGE/unifai_guard_config.json"
cp installer/EMPLOYEE_README_MAC.txt "$STAGE/EMPLOYEE_README_MAC.txt"
cp release/INSTALL_MACOS.txt "$STAGE/INSTALL_MACOS.txt"
cp release/UNINSTALL_MACOS.txt "$STAGE/UNINSTALL_MACOS.txt"
cp installer/Install_UnifAI_Guard.command "$STAGE/Install_UnifAI_Guard.command"
cp installer/Uninstall_UnifAI_Guard.command "$STAGE/Uninstall_UnifAI_Guard.command"
chmod +x "$STAGE/Install_UnifAI_Guard.command" "$STAGE/Uninstall_UnifAI_Guard.command"

mkdir -p "$STAGE/UnifAI_Guard.app/Contents/Resources"
cp config/unifai_guard_config.json "$STAGE/UnifAI_Guard.app/Contents/Resources/unifai_guard_config.json"

echo ""
echo "3) ZIP for Download Setup package"
mkdir -p release
ZIP_OUT="$ROOT/release/UnifAI_Guard_macOS.zip"
rm -f "$ZIP_OUT"
(
  cd "$STAGE"
  zip -r -y "$ZIP_OUT" \
    UnifAI_Guard.app \
    unifai_guard_config.json \
    EMPLOYEE_README_MAC.txt \
    INSTALL_MACOS.txt \
    UNINSTALL_MACOS.txt \
    Install_UnifAI_Guard.command \
    Uninstall_UnifAI_Guard.command
)

printf '%s\n' "$VERSION" > release/VERSION.txt

cp -f installer/Install_UnifAI_Guard.command release/Install_UnifAI_Guard.command
cp -f installer/Uninstall_UnifAI_Guard.command release/Uninstall_UnifAI_Guard.command
cp -f installer/EMPLOYEE_README_MAC.txt release/EMPLOYEE_README_MAC.txt
chmod +x release/Install_UnifAI_Guard.command release/Uninstall_UnifAI_Guard.command

echo ""
echo "============================================================"
echo " SUCCESS — UnifAI Guard ${VERSION} (macOS)"
echo "  App:  release/UnifAI_Guard.app"
echo "  ZIP:  release/UnifAI_Guard_macOS.zip"
echo "  Docs: release/INSTALL_MACOS.txt  release/UNINSTALL_MACOS.txt"
echo "============================================================"
ls -la release/UnifAI_Guard.app release/UnifAI_Guard_macOS.zip release/INSTALL_MACOS.txt release/UNINSTALL_MACOS.txt
