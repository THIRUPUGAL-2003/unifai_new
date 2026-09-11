# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve()
AGENT = ROOT / "agent" / "unifai_agent.py"
PROXY = ROOT / "proxy" / "browser_ai_proxy.py"
PROXY_PARTS = ROOT / "proxy" / "unifai_proxy_parts"

datas = [
    (str(PROXY), "."),
    (str(PROXY_PARTS), "unifai_proxy_parts"),
]
binaries = []
hiddenimports = [
    "pypdf",
    "PIL",
    "PIL.Image",
    "winrt",
    "winrt.windows.media.ocr",
    "winrt.windows.globalization",
    "winrt.windows.graphics.imaging",
    "winrt.windows.storage.streams",
]

for pkg in ("pypdf", "PIL", "winrt", "mitmproxy", "mitmproxy_windows"):
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
    icon=str(ROOT / "unifai_guard.ico"),
)
