"""
OS-specific helpers for UnifAI Guard (Windows + macOS).
Shared agent imports this module so Windows and Mac stay one product.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import uuid

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

if IS_WIN:
    import ctypes
    import winreg
else:
    ctypes = None  # type: ignore
    winreg = None  # type: ignore


def data_dir() -> str:
    """Writable per-user data (PAC, logs, agent_id)."""
    if IS_WIN:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    elif IS_MAC:
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    path = os.path.join(base, "UnifAI", "Guard")
    os.makedirs(path, exist_ok=True)
    return path


def log_hint_path() -> str:
    if IS_WIN:
        return r"%LOCALAPPDATA%\UnifAI\Guard"
    if IS_MAC:
        return "~/Library/Application Support/UnifAI/Guard"
    return "~/.local/share/UnifAI/Guard"


def _guid_from_transport(raw: str) -> str:
    import re

    m = re.search(
        r"\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}",
        raw or "",
    )
    return m.group(0).upper() if m else ""


def detect_mac_and_transport() -> tuple[str, str]:
    """Physical MAC + optional adapter id."""
    if IS_WIN:
        try:
            completed = subprocess.run(
                ["getmac"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
            for line in (completed.stdout or "").splitlines():
                raw = line.strip()
                if not raw or raw.lower().startswith("physical") or set(raw) <= {"=", " ", "-"}:
                    continue
                if "media disconnected" in raw.lower():
                    continue
                parts = raw.split()
                if len(parts) < 2:
                    continue
                mac = parts[0].strip().upper()
                transport = _guid_from_transport(raw[len(parts[0]) :].strip())
                if mac.count("-") == 5 or mac.count(":") == 5:
                    return mac, transport
        except Exception:
            pass
    elif IS_MAC:
        try:
            completed = subprocess.run(
                ["ifconfig"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=8,
                check=False,
            )
            import re

            for m in re.finditer(r"ether\s+([0-9a-f:]{17})", completed.stdout or "", re.I):
                return m.group(1).upper().replace(":", "-"), ""
        except Exception:
            pass
    try:
        node = uuid.getnode()
        mac = "-".join(f"{(node >> ele) & 0xFF:02X}" for ele in range(40, -1, -8))
        return mac, ""
    except Exception:
        return "", ""


def ensure_single_instance(mutex_name: str = "UnifAI_Guard_Agent") -> bool:
    if IS_WIN:
        kernel32 = ctypes.windll.kernel32  # type: ignore[union-attr]
        handle = kernel32.CreateMutexW(None, False, f"Global\\{mutex_name}")
        if kernel32.GetLastError() == 183:
            return False
        ensure_single_instance._handle = handle  # type: ignore[attr-defined]
        return True
    # Unix: flock on a lockfile
    lock_path = os.path.join(data_dir(), "guard.lock")
    try:
        import fcntl

        fp = open(lock_path, "w", encoding="utf-8")
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        ensure_single_instance._fp = fp  # type: ignore[attr-defined]
        return True
    except Exception:
        return False


def show_message(title: str, text: str, error: bool = False) -> None:
    if IS_WIN:
        try:
            flags = 0x10 if error else 0x40
            ctypes.windll.user32.MessageBoxW(0, text, title, flags)  # type: ignore[union-attr]
            return
        except Exception as e:
            print(f"[UnifAI Guard] Message: {title}: {text} ({e})")
            return
    if IS_MAC:
        icon = "stop" if error else "note"
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
        script = f'display dialog "{safe_text}" with title "{safe_title}" with icon {icon} buttons {{"OK"}} default button 1'
        try:
            subprocess.run(["osascript", "-e", script], check=False, timeout=120)
            return
        except Exception as e:
            print(f"[UnifAI Guard] Message: {title}: {text} ({e})")
            return
    print(f"[UnifAI Guard] {title}: {text}")


def prompt_uninstall_key() -> str | None:
    if IS_WIN:
        script = r"""
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object System.Windows.Forms.Form
$form.Text = 'UnifAI Guard Uninstall'
$form.Size = New-Object System.Drawing.Size(420,160)
$form.StartPosition = 'CenterScreen'
$form.FormBorderStyle = 'FixedDialog'
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$label = New-Object System.Windows.Forms.Label
$label.Location = New-Object System.Drawing.Point(12,12)
$label.Size = New-Object System.Drawing.Size(380,30)
$label.Text = 'Enter company uninstall key (leave blank if not required):'
$form.Controls.Add($label)
$box = New-Object System.Windows.Forms.TextBox
$box.Location = New-Object System.Drawing.Point(12,50)
$box.Size = New-Object System.Drawing.Size(380,24)
$box.UseSystemPasswordChar = $true
$form.Controls.Add($box)
$ok = New-Object System.Windows.Forms.Button
$ok.Text = 'OK'
$ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
$ok.Location = New-Object System.Drawing.Point(220,90)
$form.Controls.Add($ok)
$cancel = New-Object System.Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$cancel.Location = New-Object System.Drawing.Point(310,90)
$form.Controls.Add($cancel)
$form.AcceptButton = $ok
$form.CancelButton = $cancel
$result = $form.ShowDialog()
if ($result -ne [System.Windows.Forms.DialogResult]::OK) { exit 3 }
[Console]::Out.Write($box.Text)
"""
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-STA", "-Command", script],
                capture_output=True,
                text=True,
                timeout=300,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            if completed.returncode == 3:
                return None
            return (completed.stdout or "").rstrip("\r\n")
        except Exception as e:
            print(f"[UnifAI Guard ERROR] Uninstall prompt failed: {e}")
            return None
    if IS_MAC:
        script = (
            'try\n'
            'set r to display dialog "Enter company uninstall key (leave blank if not required):" '
            'default answer "" with title "UnifAI Guard Uninstall" with hidden answer '
            'buttons {"Cancel", "OK"} default button "OK"\n'
            'return text returned of r\n'
            'on error\n'
            'return "__CANCEL__"\n'
            'end try'
        )
        try:
            completed = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            out = (completed.stdout or "").strip()
            if out == "__CANCEL__" or completed.returncode != 0:
                return None
            return out
        except Exception as e:
            print(f"[UnifAI Guard ERROR] Uninstall prompt failed: {e}")
            return None
    return ""


def ca_trusted(status_path: str) -> bool:
    try:
        if os.path.isfile(status_path):
            with open(status_path, "r", encoding="utf-8", errors="replace") as f:
                if f.read().strip().upper().startswith("OK"):
                    return True
    except Exception:
        pass
    if IS_WIN:
        try:
            completed = subprocess.run(
                ["certutil.exe", "-user", "-store", "Root"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
            out = ((completed.stdout or "") + (completed.stderr or "")).lower()
            return "mitmproxy" in out
        except Exception:
            return False
    if IS_MAC:
        try:
            completed = subprocess.run(
                ["security", "find-certificate", "-a", "-c", "mitmproxy", str(os.path.expanduser("~/Library/Keychains/login.keychain-db"))],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12,
                check=False,
            )
            out = ((completed.stdout or "") + (completed.stderr or "")).lower()
            if "mitmproxy" in out:
                return True
            # Fallback: any keychain
            completed2 = subprocess.run(
                ["security", "find-certificate", "-a", "-c", "mitmproxy"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12,
                check=False,
            )
            return "mitmproxy" in ((completed2.stdout or "") + (completed2.stderr or "")).lower()
        except Exception:
            return False
    return False


def install_ca_certificate(status_path: str) -> bool:
    """Install mitmproxy CA into the user trust store (Windows Root / macOS login keychain)."""
    try:
        from pathlib import Path
        from mitmproxy.certs import CertStore

        mitm_dir = Path(os.path.expanduser("~/.mitmproxy"))
        mitm_dir.mkdir(parents=True, exist_ok=True)
        CertStore.from_store(path=mitm_dir, basename="mitmproxy", key_size=2048)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not ensure mitm certs: {e}")

    mitm_dir = os.path.expanduser("~/.mitmproxy")
    candidates = [
        os.path.join(mitm_dir, "mitmproxy-ca-cert.pem"),
        os.path.join(mitm_dir, "mitmproxy-ca-cert.cer"),
        os.path.join(mitm_dir, "mitmproxy-ca-cert.crt"),
    ]
    target_cert = next((p for p in candidates if os.path.exists(p)), "")
    if not target_cert:
        msg = "CA cert file not found yet — HTTPS intercept will fail until cert exists."
        print(f"[UnifAI Guard ERROR] {msg}")
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                f.write("FAILED: " + msg + "\n")
        except Exception:
            pass
        return False

    try:
        if IS_WIN:
            print("[UnifAI Guard] Installing mitmproxy Root CA into Windows Trusted Root Store...")
            completed = subprocess.run(
                ["certutil.exe", "-user", "-addstore", "Root", target_cert],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=False,
            )
            out = ((completed.stdout or "") + (completed.stderr or "")).strip()
            if completed.returncode != 0 and "already in store" not in out.lower():
                print(f"[UnifAI Guard ERROR] CA install failed (code={completed.returncode}): {out}")
                with open(status_path, "w", encoding="utf-8") as f:
                    f.write(f"FAILED code={completed.returncode}\n{out}\n")
                return False
        elif IS_MAC:
            print("[UnifAI Guard] Installing mitmproxy CA into macOS login keychain...")
            keychain = os.path.expanduser("~/Library/Keychains/login.keychain-db")
            if not os.path.exists(keychain):
                keychain = os.path.expanduser("~/Library/Keychains/login.keychain")
            # -d = admin cert store path optional; user trust for SSL
            completed = subprocess.run(
                [
                    "security",
                    "add-trusted-cert",
                    "-d",
                    "-r",
                    "trustRoot",
                    "-p",
                    "ssl",
                    "-p",
                    "basic",
                    "-k",
                    keychain,
                    target_cert,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            out = ((completed.stdout or "") + (completed.stderr or "")).strip()
            # Already trusted often returns non-zero with "already exists"
            if completed.returncode != 0 and "already" not in out.lower() and "exists" not in out.lower():
                # Retry without -d (some macOS versions)
                completed2 = subprocess.run(
                    [
                        "security",
                        "add-trusted-cert",
                        "-r",
                        "trustRoot",
                        "-k",
                        keychain,
                        target_cert,
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                out2 = ((completed2.stdout or "") + (completed2.stderr or "")).strip()
                if completed2.returncode != 0 and "already" not in out2.lower():
                    print(f"[UnifAI Guard ERROR] CA install failed: {out or out2}")
                    print("[UnifAI Guard ERROR] You may need to approve the cert in Keychain Access (Trust → Always Trust).")
                    with open(status_path, "w", encoding="utf-8") as f:
                        f.write(f"FAILED\n{out}\n{out2}\n")
                    return False
        else:
            print("[UnifAI Guard WARNING] Auto CA install not supported on this OS — trust mitmproxy CA manually.")
            with open(status_path, "w", encoding="utf-8") as f:
                f.write("MANUAL\n")
            return False

        print("[UnifAI Guard] Certificate trust step completed.")
        with open(status_path, "w", encoding="utf-8") as f:
            f.write("OK\n")
        return True
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Could not auto-install CA Cert: {e}")
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                f.write(f"FAILED: {e}\n")
        except Exception:
            pass
        return False


def _mac_network_services() -> list[str]:
    try:
        completed = subprocess.run(
            ["networksetup", "-listallnetworkservices"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        services = []
        for line in (completed.stdout or "").splitlines():
            line = line.strip()
            if not line or line.startswith("An asterisk") or line.startswith("*"):
                # "*Ethernet" means disabled — skip disabled
                if line.startswith("*"):
                    continue
                continue
            if line.startswith("*"):
                continue
            services.append(line)
        # Also include lines that don't start with asterisk from first skip logic
        services = []
        for line in (completed.stdout or "").splitlines():
            s = line.strip()
            if not s or "asterisk" in s.lower():
                continue
            if s.startswith("*"):
                continue
            services.append(s)
        return services
    except Exception as e:
        print(f"[UnifAI Guard WARNING] list network services: {e}")
        return ["Wi-Fi", "Ethernet"]


def set_system_proxy_pac(enable: bool, pac_url: str, silent: bool = False) -> bool:
    """Enable/disable system PAC (Windows Internet Settings / macOS networksetup)."""
    if IS_WIN:
        return _set_windows_proxy_pac(enable, pac_url, silent)
    if IS_MAC:
        return _set_mac_proxy_pac(enable, pac_url, silent)
    print("[UnifAI Guard WARNING] System PAC not implemented for this OS.")
    return False


def _set_windows_proxy_pac(enable: bool, pac_url: str, silent: bool) -> bool:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)  # type: ignore
        if enable:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)  # type: ignore
            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, pac_url)  # type: ignore
            try:
                winreg.DeleteValue(key, "ProxyServer")  # type: ignore
            except FileNotFoundError:
                pass
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "localhost;127.0.0.1;<local>")  # type: ignore
            if not silent:
                print(f"[UnifAI Guard] Windows PAC ENABLED -> {pac_url}")
        else:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)  # type: ignore
            try:
                winreg.DeleteValue(key, "AutoConfigURL")  # type: ignore
            except FileNotFoundError:
                pass
            if not silent:
                print("[UnifAI Guard] Windows Proxy / PAC DISABLED.")
        winreg.CloseKey(key)  # type: ignore
        try:
            ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)  # type: ignore
            ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)  # type: ignore
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Failed to update Windows Proxy settings: {e}")
        return False


def _set_mac_proxy_pac(enable: bool, pac_url: str, silent: bool) -> bool:
    ok_any = False
    for service in _mac_network_services():
        try:
            if enable:
                subprocess.run(
                    ["networksetup", "-setautoproxyurl", service, pac_url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15,
                    check=False,
                )
                completed = subprocess.run(
                    ["networksetup", "-setautoproxystate", service, "on"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15,
                    check=False,
                )
            else:
                completed = subprocess.run(
                    ["networksetup", "-setautoproxystate", service, "off"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15,
                    check=False,
                )
            if completed.returncode == 0:
                ok_any = True
        except Exception as e:
            print(f"[UnifAI Guard WARNING] PAC on '{service}': {e}")
    if enable and not silent:
        print(f"[UnifAI Guard] macOS auto-proxy PAC {'ENABLED' if ok_any else 'FAILED'} -> {pac_url}")
    elif not enable and not silent:
        print("[UnifAI Guard] macOS auto-proxy PAC DISABLED.")
    return ok_any


def firefox_profiles_dirs() -> list[str]:
    dirs: list[str] = []
    if IS_WIN:
        roaming = os.environ.get("APPDATA") or ""
        base = os.path.join(roaming, "Mozilla", "Firefox") if roaming else ""
    elif IS_MAC:
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Firefox")
    else:
        base = os.path.join(os.path.expanduser("~"), ".mozilla", "firefox")
    if not base or not os.path.isdir(base):
        return dirs
    ini = os.path.join(base, "profiles.ini")
    if os.path.isfile(ini):
        try:
            with open(ini, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except Exception:
            lines = []
        current: dict[str, str] = {}

        def flush() -> None:
            path = current.get("Path")
            if not path:
                return
            is_rel = current.get("IsRelative", "1") != "0"
            full = path if not is_rel else os.path.join(base, path.replace("/", os.sep))
            if os.path.isdir(full):
                dirs.append(full)

        for raw in lines:
            line = raw.strip()
            if line.startswith("[") and line.endswith("]"):
                flush()
                current = {}
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                current[k.strip()] = v.strip()
        flush()
    profiles = os.path.join(base, "Profiles")
    if os.path.isdir(profiles):
        for name in os.listdir(profiles):
            p = os.path.join(profiles, name)
            if os.path.isdir(p):
                dirs.append(p)
    out: list[str] = []
    seen: set[str] = set()
    for d in dirs:
        n = os.path.normcase(os.path.abspath(d))
        if n not in seen:
            seen.add(n)
            out.append(d)
    return out


def register_autostart(exe_path: str) -> None:
    """Register Guard to start at user login."""
    if IS_WIN:
        try:
            key = winreg.OpenKey(  # type: ignore
                winreg.HKEY_CURRENT_USER,  # type: ignore
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,  # type: ignore
            )
            winreg.SetValueEx(key, "UnifAI_Guard", 0, winreg.REG_SZ, f'"{exe_path}"')  # type: ignore
            winreg.CloseKey(key)  # type: ignore
            print("[UnifAI Guard] Autostart registered (Windows Run key).")
        except Exception as e:
            print(f"[UnifAI Guard WARNING] Autostart register failed: {e}")
        return
    if IS_MAC:
        agents = os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents")
        os.makedirs(agents, exist_ok=True)
        plist_path = os.path.join(agents, "com.unifai.guard.plist")
        # Prefer .app Contents/MacOS binary when frozen as app bundle
        program = exe_path
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.unifai.guard</string>
  <key>ProgramArguments</key>
  <array>
    <string>{program}</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <false/>
  <key>StandardOutPath</key>
  <string>{os.path.join(data_dir(), "launchd.out.log")}</string>
  <key>StandardErrorPath</key>
  <string>{os.path.join(data_dir(), "launchd.err.log")}</string>
</dict>
</plist>
"""
        try:
            with open(plist_path, "w", encoding="utf-8") as f:
                f.write(plist)
            subprocess.run(["launchctl", "unload", plist_path], check=False, capture_output=True)
            subprocess.run(["launchctl", "load", plist_path], check=False, capture_output=True)
            print(f"[UnifAI Guard] Autostart registered (LaunchAgent): {plist_path}")
        except Exception as e:
            print(f"[UnifAI Guard WARNING] LaunchAgent register failed: {e}")


def clear_autostart() -> None:
    if IS_WIN:
        try:
            key = winreg.OpenKey(  # type: ignore
                winreg.HKEY_CURRENT_USER,  # type: ignore
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE,  # type: ignore
            )
            try:
                winreg.DeleteValue(key, "UnifAI_Guard")  # type: ignore
            except FileNotFoundError:
                pass
            winreg.CloseKey(key)  # type: ignore
        except Exception as e:
            print(f"[UnifAI Guard WARNING] Could not clear autostart: {e}")
        return
    if IS_MAC:
        plist_path = os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents", "com.unifai.guard.plist")
        try:
            subprocess.run(["launchctl", "unload", plist_path], check=False, capture_output=True)
            if os.path.isfile(plist_path):
                os.remove(plist_path)
            print("[UnifAI Guard] LaunchAgent removed.")
        except Exception as e:
            print(f"[UnifAI Guard WARNING] Could not clear LaunchAgent: {e}")


def os_label() -> str:
    return platform.platform()


def write_chrome_mac_proxy_policy(enable: bool, pac_url: str) -> None:
    """Best-effort Chrome managed preference on macOS (user Library)."""
    if not IS_MAC:
        return
    # Chrome reads policies from Managed Preferences when deployed via MDM;
    # for user installs, system PAC (networksetup) is the primary path.
    # Also drop a helper prefs note for support.
    note = os.path.join(data_dir(), "mac_browser_note.txt")
    try:
        with open(note, "w", encoding="utf-8") as f:
            f.write(
                "UnifAI Guard on macOS uses system Auto Proxy URL (networksetup).\n"
                "Chrome / Edge / Brave / Firefox typically follow system proxy.\n"
                "Fully quit & reopen browsers after install.\n"
                f"PAC: {pac_url if enable else '(cleared)'}\n"
            )
    except Exception:
        pass
