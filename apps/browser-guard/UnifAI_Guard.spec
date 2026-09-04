# -*- mode: python ; coding: utf-8 -*-
# Build on Windows: pyinstaller UnifAI_Guard.spec
from PyInstaller.utils.hooks import collect_all
import os

ROOT = os.path.abspath(SPECPATH)
PROXY = os.path.join(ROOT, "proxy", "browser_ai_proxy.py")
AGENT = os.path.join(ROOT, "agent", "unifai_agent.py")

datas = [(PROXY, ".")]
binaries = []
hiddenimports = [
    "pypdf",
    "PIL",
    "PIL.Image",
    "guard_platform",
    "winrt",
    "winrt.windows.media.ocr",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.storage.streams",
]
for pkg in ("pypdf", "PIL", "winrt", "mitmproxy", "mitmproxy_windows"):
    try:
        tmp_ret = collect_all(pkg)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except Exception:
        pass

a = Analysis(
    [AGENT],
    pathex=[os.path.join(ROOT, "agent")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="UnifAI_Guard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
