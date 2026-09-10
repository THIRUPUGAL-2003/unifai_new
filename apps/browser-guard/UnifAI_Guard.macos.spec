# -*- mode: python ; coding: utf-8 -*-
# Build on macOS only:  pyinstaller UnifAI_Guard.macos.spec
# Output: dist/UnifAI_Guard.app
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve()
AGENT = ROOT / "agent" / "unifai_agent.py"
PROXY = ROOT / "proxy" / "browser_ai_proxy.py"

datas = [(str(PROXY), ".")]
binaries = []
hiddenimports = ["pypdf", "PIL", "PIL.Image"]

for pkg in ("pypdf", "PIL", "mitmproxy"):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    [str(AGENT)],
    pathex=[str(ROOT / "agent")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["winrt", "mitmproxy_windows"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="UnifAI_Guard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="UnifAI_Guard",
)

app = BUNDLE(
    coll,
    name="UnifAI_Guard.app",
    icon=None,
    bundle_identifier="com.unifai.guard",
    info_plist={
        "CFBundleDisplayName": "UnifAI Guard",
        "CFBundleName": "UnifAI Guard",
        "CFBundleShortVersionString": "1.6.21",
        "CFBundleVersion": "1.6.21",
        "LSBackgroundOnly": False,
        "NSHighResolutionCapable": True,
    },
)
