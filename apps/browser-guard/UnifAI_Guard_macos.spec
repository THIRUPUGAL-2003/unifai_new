# -*- mode: python ; coding: utf-8 -*-
# Build on macOS only: ./build_macos.sh
from PyInstaller.utils.hooks import collect_all
import os

ROOT = os.path.abspath(SPECPATH)
PROXY = os.path.join(ROOT, "proxy", "browser_ai_proxy.py")
AGENT = os.path.join(ROOT, "agent", "unifai_agent.py")

datas = [(PROXY, ".")]
binaries = []
hiddenimports = ["pypdf", "PIL", "PIL.Image", "guard_platform"]

for pkg in ("pypdf", "PIL", "mitmproxy"):
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

a = Analysis(
    [AGENT],
    pathex=[os.path.join(ROOT, "agent")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["winrt", "win32api", "win32com", "pythoncom"],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="UnifAI_Guard",
)

app = BUNDLE(
    coll,
    name="UnifAI Guard.app",
    icon=None,
    bundle_identifier="com.unifai.guard",
    info_plist={
        "CFBundleName": "UnifAI Guard",
        "CFBundleDisplayName": "UnifAI Guard",
        "CFBundleShortVersionString": "1.6.0",
        "CFBundleVersion": "1.6.0",
        "NSHighResolutionCapable": True,
        "LSUIElement": False,
    },
)
