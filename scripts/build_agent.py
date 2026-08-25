#!/usr/bin/env python3
"""
UnifAI Guard Agent EXE Builder
==============================
Compiles scripts/unifai_agent.py & scripts/browser_ai_proxy.py
into a single standalone executable: dist/UnifAI_Guard.exe
"""

import os
import sys
import subprocess

def build_exe():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    agent_py = os.path.join(script_dir, "unifai_agent.py")
    proxy_py = os.path.join(script_dir, "browser_ai_proxy.py")

    if not os.path.exists(agent_py) or not os.path.exists(proxy_py):
        print("Error: Source files missing!")
        sys.exit(1)

    print("==========================================================")
    print("   Building Standalone UnifAI_Guard.exe Executable...    ")
    print("==========================================================")

    # PyInstaller: --noconsole = no black terminal window (runs as background agent)
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name", "UnifAI_Guard",
        f"--add-data={proxy_py}{os.pathsep}.",
        "--hidden-import", "pypdf",
        "--collect-all", "pypdf",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL.Image",
        "--collect-all", "PIL",
        "--hidden-import", "winrt",
        "--hidden-import", "winrt.windows.media.ocr",
        "--hidden-import", "winrt.windows.globalization",
        "--hidden-import", "winrt.windows.graphics.imaging",
        "--hidden-import", "winrt.windows.storage.streams",
        "--collect-all", "winrt",
        "--collect-all", "mitmproxy",
        "--collect-all", "mitmproxy_windows",
        agent_py
    ]

    print("Executing PyInstaller command:")
    print(" ".join(cmd))

    res = subprocess.run(cmd, cwd=project_root)

    if res.returncode == 0:
        exe_path = os.path.join(project_root, "dist", "UnifAI_Guard.exe")
        print("\n==========================================================")
        print(" SUCCESS! UnifAI_Guard.exe successfully created at:")
        print(f" -> {exe_path}")
        print("==========================================================")
    else:
        print("\n[ERROR] PyInstaller build failed.")
        sys.exit(res.returncode)

if __name__ == "__main__":
    build_exe()
