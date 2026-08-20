#!/usr/bin/env python3
"""
UnifAI Enterprise Security Guard Agent (Desktop)
================================================
Employee laptop agent for company deployments.

- Talks only to the UnifAI backend HTTPS API (no direct DB).
- Enables Windows PAC proxy for monitored Target Websites only.
- Registers heartbeat + agent identity in Browser AI (unifai_new).
- Runs without a console window; logs to %LOCALAPPDATA%\\UnifAI\\Guard\\
- Installer registers autostart at user login.
- Uninstall: UnifAI_Guard.exe --uninstall "KEY"
"""

from __future__ import annotations

import ctypes
import http.server
import json
import os
import platform
import re
import signal
import socket
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import uuid
import winreg

from mitmproxy.tools.main import mitmdump

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

DEFAULT_BACKEND = "https://unifai.dev-yp.com"
AGENT_VERSION = "1.2.13"
HEARTBEAT_SECONDS = 30
PAC_HTTP_HOST = "127.0.0.1"
PAC_HTTP_PORT = 18085


def exe_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def data_dir() -> str:
    """Writable per-user data (PAC, logs) — safe under Program Files installs."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(base, "UnifAI", "Guard")
    os.makedirs(path, exist_ok=True)
    return path


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not read {path}: {e}")
        return {}


def load_runtime_config() -> dict:
    """
    Priority: ENV > exe-dir config > %LOCALAPPDATA% config > defaults.
    """
    file_cfg: dict = {}
    candidates = [
        os.path.join(exe_dir(), "unifai_guard_config.json"),
        os.path.join(data_dir(), "unifai_guard_config.json"),
    ]
    loaded_from = ""
    for cfg_path in candidates:
        if os.path.isfile(cfg_path):
            file_cfg = _read_json(cfg_path)
            loaded_from = cfg_path
            break
    if loaded_from:
        print(f"[UnifAI Guard] Loaded config: {loaded_from}")

    def pick(env_key: str, file_key: str, default: str) -> str:
        if os.environ.get(env_key):
            return os.environ[env_key].strip()
        val = file_cfg.get(file_key)
        if val is not None and str(val).strip():
            return str(val).strip()
        return default

    backend = pick("UNIFAI_BACKEND_URL", "backend_url", DEFAULT_BACKEND).rstrip("/")
    proxy_addr = pick("UNIFAI_PROXY_ADDR", "proxy_addr", "127.0.0.1:8085")
    pac_url = pick("UNIFAI_PAC_URL", "pac_url", f"{backend}/api/browser-ai/pac")
    sync_secs = pick("UNIFAI_PAC_SYNC_SECONDS", "pac_sync_seconds", "1")

    os.environ["UNIFAI_BACKEND_URL"] = backend
    os.environ["UNIFAI_PROXY_ADDR"] = proxy_addr
    os.environ["UNIFAI_PAC_URL"] = pac_url
    os.environ["UNIFAI_PAC_SYNC_SECONDS"] = str(sync_secs)

    # Keep a copy in data_dir so logs/support can see active config
    try:
        with open(os.path.join(data_dir(), "unifai_guard_config.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "backend_url": backend,
                    "proxy_addr": proxy_addr,
                    "pac_url": pac_url,
                    "pac_sync_seconds": int(sync_secs),
                },
                f,
                indent=2,
            )
    except Exception:
        pass

    return {
        "backend_url": backend,
        "proxy_addr": proxy_addr,
        "pac_url": pac_url,
        "pac_sync_seconds": int(sync_secs),
    }


_CFG = load_runtime_config()
UNIFAI_BACKEND_URL = _CFG["backend_url"]
PAC_URL = _CFG["pac_url"]
PROXY_ADDR = _CFG["proxy_addr"]
PAC_SYNC_SECONDS = _CFG["pac_sync_seconds"]


# ---------------------------------------------------------------------------
# Agent identity / heartbeat / uninstall
# ---------------------------------------------------------------------------

def agent_id_path() -> str:
    return os.path.join(data_dir(), "agent_id.txt")


def get_or_create_agent_id() -> str:
    path = agent_id_path()
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read().strip()
            if existing:
                return existing
    except Exception:
        pass
    new_id = str(uuid.uuid4())
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_id)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not persist agent_id: {e}")
    return new_id


def detect_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return ""


def guid_from_transport(raw: str) -> str:
    """Keep only {xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx}; drop \\Device\\Tcpip_."""
    m = re.search(
        r"\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}",
        raw or "",
    )
    return m.group(0).upper() if m else ""


def detect_mac_and_transport() -> tuple[str, str]:
    """Active NIC Physical Address + adapter GUID (not the Tcpip_ prefix)."""
    try:
        completed = subprocess.run(
            ["getmac"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            check=False,
        )
        lines = (completed.stdout or "").splitlines()
        for line in lines:
            raw = line.strip()
            if not raw or raw.lower().startswith("physical") or set(raw) <= {"=", " ", "-"}:
                continue
            if "media disconnected" in raw.lower():
                continue
            parts = raw.split()
            if len(parts) < 2:
                continue
            mac = parts[0].strip().upper()
            transport = guid_from_transport(raw[len(parts[0]) :].strip())
            if mac.count("-") == 5 or mac.count(":") == 5:
                return mac, transport
    except Exception as e:
        print(f"[UnifAI Guard WARNING] getmac failed: {e}")
    try:
        node = uuid.getnode()
        mac = "-".join(f"{(node >> ele) & 0xFF:02X}" for ele in range(40, -1, -8))
        return mac, ""
    except Exception:
        return "", ""


def collect_agent_info(agent_id: str, status: str = "active") -> dict:
    hostname = socket.gethostname()
    username = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    mac, transport = detect_mac_and_transport()
    return {
        "id": agent_id,
        "hostname": hostname,
        "username": username,
        "ip_address": detect_local_ip(),
        "mac_address": mac,
        "transport_name": transport,
        "os_version": platform.platform(),
        "agent_version": AGENT_VERSION,
        "status": status or "active",
    }


def _http_json(method: str, url: str, payload: dict | None = None, timeout: int = 12) -> tuple[int, dict | None]:
    data = None
    headers = {"Accept": "application/json", "User-Agent": f"UnifAI-Guard/{AGENT_VERSION}"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body) if body else {}
            except Exception:
                return resp.status, None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", errors="replace")
            parsed = json.loads(body) if body else None
        except Exception:
            parsed = None
        return e.code, parsed
    except Exception as e:
        print(f"[UnifAI Guard WARNING] HTTP {method} {url} failed: {e}")
        return 0, None


def send_heartbeat(agent_id: str, status: str = "active") -> dict | None:
    info = collect_agent_info(agent_id, status=status)
    code, data = _http_json("POST", f"{UNIFAI_BACKEND_URL}/api/browser-ai/agents/heartbeat", info)
    if code == 200:
        print(f"[UnifAI Guard] Heartbeat OK ({info.get('hostname')} / {info.get('ip_address')} / {info.get('mac_address')} / {status})")
        return data if isinstance(data, dict) else {}
    print(f"[UnifAI Guard WARNING] Heartbeat failed status={code} body={data}")
    return None


def heartbeat_wants_uninstall(data: dict | None) -> bool:
    if not isinstance(data, dict):
        return False
    if str(data.get("command") or "").strip().lower() == "uninstall":
        return True
    agent = data.get("agent") if isinstance(data.get("agent"), dict) else {}
    status = str(agent.get("status") or "").strip().lower()
    return bool(agent.get("uninstall_requested")) or status == "uninstall_pending"


def apply_admin_uninstall(agent_id: str) -> None:
    """Admin requested uninstall from Browser AI. No employee key required."""
    print("[UnifAI Guard] Admin remote uninstall received — stopping Guard.")
    _http_json(
        "POST",
        f"{UNIFAI_BACKEND_URL}/api/browser-ai/agents/uninstall-ack",
        {"agent_id": agent_id},
    )
    clear_guard_runtime()
    os._exit(0)


def heartbeat_loop(agent_id: str, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        data = send_heartbeat(agent_id, status="active")
        if heartbeat_wants_uninstall(data):
            apply_admin_uninstall(agent_id)
            return
        # Sleep/wake must not drop PAC. Re-assert on every beat until uninstall.
        set_windows_proxy_pac(enable=True, pac_url=pac_http_url(), silent=True)
        set_browser_quic(enable_quic=False)
        stop_event.wait(HEARTBEAT_SECONDS)


def clear_guard_runtime() -> None:
    set_windows_proxy_pac(enable=False)
    set_browser_quic(enable_quic=True)
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, "UnifAI_Guard")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not clear autostart: {e}")


def prompt_uninstall_key() -> str | None:
    """Show a Windows input dialog; return None if cancelled."""
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
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if completed.returncode == 3:
            return None
        return (completed.stdout or "").rstrip("\r\n")
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Uninstall prompt failed: {e}")
        return None


def run_uninstall(key: str) -> int:
    """Verify company uninstall key, mark agent uninstalled, clear local proxy.

    Exit codes: 0=ok, 2=bad key, 3=cancelled (prompt), 1=other.
    Backend unreachable / 5xx does not clear PAC — company key must be verified.
    """
    agent_id = get_or_create_agent_id()
    status, data = _http_json(
        "POST",
        f"{UNIFAI_BACKEND_URL}/api/browser-ai/agents/uninstall",
        {"agent_id": agent_id, "key": key or ""},
    )
    if status == 200:
        print("[UnifAI Guard] Uninstall authorized by backend.")
        clear_guard_runtime()
        return 0
    if status == 403:
        print("[UnifAI Guard ERROR] Invalid uninstall key.")
        return 2
    if status == 0:
        print("[UnifAI Guard ERROR] Backend unreachable — uninstall key not verified. PAC left on.")
        return 1
    print(f"[UnifAI Guard ERROR] Uninstall rejected status={status} body={data}")
    return 1


def run_uninstall_prompt() -> int:
    key = prompt_uninstall_key()
    if key is None:
        print("[UnifAI Guard] Uninstall cancelled by user.")
        return 3
    return run_uninstall(key)


# ---------------------------------------------------------------------------
# Logging / single instance
# ---------------------------------------------------------------------------

class _Tee:
    """File-like stdout/stderr. mitmdump calls isatty(); missing it kills the proxy."""

    closed = False
    errors = "replace"
    name = "<unifai-guard-log>"
    mode = "w"

    def __init__(self, stream, log_file):
        self._stream = stream
        self._log = log_file
        self.encoding = getattr(stream, "encoding", None) or "utf-8"

    def write(self, data):
        try:
            if self._stream is not None:
                self._stream.write(data)
                self._stream.flush()
        except Exception:
            pass
        try:
            self._log.write(data)
            self._log.flush()
        except Exception:
            pass
        return len(data) if data is not None else 0

    def flush(self):
        try:
            if self._stream is not None:
                self._stream.flush()
        except Exception:
            pass
        try:
            self._log.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        return False

    def readable(self) -> bool:
        return False

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def fileno(self):
        raise OSError(9, "Tee has no fileno")

    def reconfigure(self, *args, **kwargs):
        fn = getattr(self._stream, "reconfigure", None)
        if callable(fn):
            return fn(*args, **kwargs)
        return None


def setup_file_logging() -> str:
    log_path = os.path.join(data_dir(), "unifai_guard.log")
    log_f = open(log_path, "a", encoding="utf-8", buffering=1)
    sys.stdout = _Tee(sys.stdout, log_f)
    sys.stderr = _Tee(sys.stderr, log_f)
    return log_path


def ensure_single_instance() -> bool:
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, "Global\\UnifAI_Guard_Agent")
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        return False
    ensure_single_instance._handle = handle  # type: ignore[attr-defined]
    return True


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def local_pac_path() -> str:
    return os.path.join(data_dir(), "proxy.pac")


_PAC_HTTP_URL = f"http://{PAC_HTTP_HOST}:{PAC_HTTP_PORT}/proxy.pac"


def pac_http_url() -> str:
    return _PAC_HTTP_URL


class _PACRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = (self.path or "/").split("?", 1)[0]
        if path not in ("/proxy.pac", "/pac", "/"):
            self.send_error(404)
            return
        body = (
            b"function FindProxyForURL(url, host) { return \"DIRECT\"; }\n"
        )
        try:
            with open(local_pac_path(), "rb") as f:
                body = f.read() or body
        except Exception:
            pass
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ns-proxy-autoconfig")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def start_local_pac_http_server() -> str:
    """Chrome ignores file:// PAC. Serve it over HTTP on localhost instead."""
    global _PAC_HTTP_URL
    last_err = None
    for port in (PAC_HTTP_PORT, PAC_HTTP_PORT + 1, PAC_HTTP_PORT + 2):
        try:
            httpd = http.server.ThreadingHTTPServer((PAC_HTTP_HOST, port), _PACRequestHandler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            _PAC_HTTP_URL = f"http://{PAC_HTTP_HOST}:{port}/proxy.pac"
            print(f"[UnifAI Guard] Local PAC HTTP server: {_PAC_HTTP_URL}")
            return _PAC_HTTP_URL
        except Exception as e:
            last_err = e
    print(f"[UnifAI Guard ERROR] Could not bind local PAC HTTP server: {last_err}")
    return _PAC_HTTP_URL


# ---------------------------------------------------------------------------
# Windows proxy / browser policy
# ---------------------------------------------------------------------------

def _notify_wininet() -> None:
    ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
    ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)


def _set_reg_dword(root, path: str, name: str, value: int) -> bool:
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def set_browser_quic(enable_quic: bool) -> None:
    value = 1 if enable_quic else 0
    ok = False
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for path in (
            r"Software\Policies\Google\Chrome",
            r"Software\Policies\Microsoft\Edge",
            r"Software\Google\Chrome",
            r"Software\Microsoft\Edge",
        ):
            if _set_reg_dword(root, path, "QuicAllowed", value):
                ok = True
    if not ok and not enable_quic:
        print("[UnifAI Guard WARNING] Could not disable Chrome/Edge HTTP/3 (QUIC). ChatGPT/Gemini may bypass the proxy.")


def set_browser_pac_policy(enable: bool, pac_url: str | None = None) -> None:
    """Force Chrome/Edge to use the Guard PAC even when they ignore Windows Internet Settings."""
    if pac_url is None:
        pac_url = pac_http_url()
    for path in (
        r"Software\Policies\Google\Chrome",
        r"Software\Policies\Microsoft\Edge",
    ):
        try:
            key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE)
            if enable:
                winreg.SetValueEx(key, "ProxyMode", 0, winreg.REG_SZ, "pac_script")
                winreg.SetValueEx(key, "ProxyPacUrl", 0, winreg.REG_SZ, pac_url)
            else:
                for name in ("ProxyMode", "ProxyPacUrl"):
                    try:
                        winreg.DeleteValue(key, name)
                    except FileNotFoundError:
                        pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[UnifAI Guard WARNING] Could not set browser PAC policy on {path}: {e}")


def set_windows_proxy_pac(enable: bool, pac_url: str | None = None, silent: bool = False) -> bool:
    if pac_url is None:
        pac_url = pac_http_url()
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enable:
            # PAC only. ProxyEnable=1 (manual proxy) makes Chrome ignore AutoConfigURL.
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, pac_url)
            try:
                winreg.DeleteValue(key, "ProxyServer")
            except FileNotFoundError:
                pass
            winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "localhost;127.0.0.1;<local>")
            if not silent:
                print(f"[UnifAI Guard] Windows PAC ENABLED -> {pac_url}")
        else:
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            try:
                winreg.DeleteValue(key, "AutoConfigURL")
            except FileNotFoundError:
                pass
            if not silent:
                print("[UnifAI Guard] Windows Proxy / PAC DISABLED.")
        winreg.CloseKey(key)
        set_browser_pac_policy(enable=enable, pac_url=pac_url)
        _notify_wininet()
        return True
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Failed to update Windows Proxy settings: {e}")
        return False


# ---------------------------------------------------------------------------
# Backend PAC / targets
# ---------------------------------------------------------------------------

def _http_get_text(url: str, accept: str, timeout: int = 10) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": f"UnifAI-Guard/{AGENT_VERSION}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            low = body.lstrip().lower()
            if low.startswith("<!doctype") or low.startswith("<html"):
                print(f"[UnifAI Guard WARNING] Got HTML instead of API from {url} (backend missing Browser AI routes).")
                return None
            return body
    except Exception as e:
        print(f"[UnifAI Guard WARNING] HTTP get failed {url}: {e}")
        return None


def check_backend() -> bool:
    """Return True only when Browser AI API is reachable (not just /health)."""
    targets = _http_get_text(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets", "application/json", timeout=8)
    if targets and ("targets" in targets or targets.strip().startswith("{")):
        print(f"[UnifAI Guard] Backend Browser AI API OK: {UNIFAI_BACKEND_URL}")
        return True
    health = _http_get_text(f"{UNIFAI_BACKEND_URL}/health", "application/json", timeout=8)
    if health and '"status"' in health:
        print("[UnifAI Guard WARNING] /health OK but /api/browser-ai/targets failed — Browser AI may be missing on this deploy.")
    print(f"[UnifAI Guard ERROR] Cannot reach Browser AI API at {UNIFAI_BACKEND_URL}")
    print("[UnifAI Guard ERROR] Deploy latest UnifAI with /api/browser-ai/* routes, then restart Guard.")
    return False


def build_pac_from_targets(proxy_addr: str) -> str | None:
    body = _http_get_text(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets", "application/json")
    if not body:
        return None
    try:
        data = json.loads(body)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] targets JSON parse failed: {e}")
        return None

    targets = data.get("targets") if isinstance(data, dict) else None
    if not isinstance(targets, list):
        return None

    hosts: list[str] = []
    seen: set[str] = set()
    for t in targets:
        if not isinstance(t, dict):
            continue
        monitored = bool(t.get("monitored"))
        block_site = bool(t.get("block_site"))
        if not monitored and not block_site:
            continue
        d = str(t.get("domain") or "").strip().lower().lstrip(".")
        if not d or d in seen:
            continue
        seen.add(d)
        hosts.append(d)

    hosts.sort()
    lines = [
        "// UnifAI Browser AI Guard — built on agent from Target Websites",
        "function FindProxyForURL(url, host) {",
        "    host = host.toLowerCase();",
        "    var aiHosts = [",
    ]
    for d in hosts:
        lines.append(f'        "{d}",')
    lines += [
        "    ];",
        "    for (var i = 0; i < aiHosts.length; i++) {",
        "        var d = aiHosts[i];",
        '        if (host === d || dnsDomainIs(host, "." + d) || shExpMatch(host, "*." + d)) {',
        f'            return "PROXY {proxy_addr}";',
        "        }",
        "    }",
        '    return "DIRECT";',
        "}",
        "",
    ]
    return "\n".join(lines)


def fetch_proxy_pac() -> str | None:
    urls = [
        f"{PAC_URL}?proxy={PROXY_ADDR}",
        f"{UNIFAI_BACKEND_URL}/api/browser-ai/pac?proxy={PROXY_ADDR}",
        f"{UNIFAI_BACKEND_URL}/api/browser-ai/proxy.pac?proxy={PROXY_ADDR}",
    ]
    seen = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        body = _http_get_text(url, "application/x-ns-proxy-autoconfig,*/*")
        if body and "FindProxyForURL" in body:
            return body
    print("[UnifAI Guard] Server PAC unavailable — building PAC from /api/browser-ai/targets")
    return build_pac_from_targets(PROXY_ADDR)


def write_local_pac(content: str) -> None:
    path = local_pac_path()
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"[UnifAI Guard] Wrote local proxy.pac ({path})")
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not write local proxy.pac: {e}")


def sync_pac_loop(stop_event: threading.Event) -> None:
    last = ""
    while not stop_event.is_set():
        pac = fetch_proxy_pac()
        if pac and pac != last:
            write_local_pac(pac)
            last = pac
            set_windows_proxy_pac(enable=True, pac_url=pac_http_url())
            n = pac.count('",') if "aiHosts" in pac else 0
            print(f"[UnifAI Guard] PAC refreshed (~{n} domain entries).")
        stop_event.wait(PAC_SYNC_SECONDS)


# ---------------------------------------------------------------------------
# Certs / proxy engine
# ---------------------------------------------------------------------------

def ensure_mitm_certs() -> None:
    """Create mitmproxy CA in ~/.mitmproxy if missing."""
    try:
        from pathlib import Path
        from mitmproxy.certs import CertStore

        mitm_dir = Path(os.path.expanduser("~/.mitmproxy"))
        mitm_dir.mkdir(parents=True, exist_ok=True)
        CertStore.from_store(path=mitm_dir, basename="mitmproxy", key_size=2048)
        print(f"[UnifAI Guard] mitmproxy cert store ready: {mitm_dir}")
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not ensure mitm certs: {e}")


def install_ca_certificate() -> bool:
    ensure_mitm_certs()
    mitm_dir = os.path.expanduser("~/.mitmproxy")
    cert_cer = os.path.join(mitm_dir, "mitmproxy-ca-cert.cer")
    cert_crt = os.path.join(mitm_dir, "mitmproxy-ca-cert.crt")
    target_cert = cert_cer if os.path.exists(cert_cer) else cert_crt
    status_path = os.path.join(data_dir(), "ca_install_status.txt")
    if not os.path.exists(target_cert):
        msg = "CA cert file not found yet — HTTPS intercept will fail until cert exists."
        print(f"[UnifAI Guard ERROR] {msg}")
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                f.write("FAILED: " + msg + "\n")
        except Exception:
            pass
        return False
    try:
        print("[UnifAI Guard] Installing mitmproxy Root CA into Windows Trusted Root Store...")
        completed = subprocess.run(
            ["certutil.exe", "-user", "-addstore", "Root", target_cert],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            check=False,
        )
        out = ((completed.stdout or "") + (completed.stderr or "")).strip()
        if completed.returncode != 0 and "already in store" not in out.lower():
            print(f"[UnifAI Guard ERROR] CA install failed (code={completed.returncode}): {out}")
            print("[UnifAI Guard ERROR] Browsers will show certificate warnings; intercept may not work.")
            try:
                with open(status_path, "w", encoding="utf-8") as f:
                    f.write(f"FAILED code={completed.returncode}\n{out}\n")
            except Exception:
                pass
            return False
        print("[UnifAI Guard] Certificate trust step completed.")
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                f.write("OK\n")
        except Exception:
            pass
        return True
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Could not auto-install CA Cert: {e}")
        try:
            with open(status_path, "w", encoding="utf-8") as f:
                f.write(f"FAILED: {e}\n")
        except Exception:
            pass
        return False


def run_proxy_server(addon_script: str, port: int = 8085) -> None:
    args = [
        "-p", str(port),
        "-s", addon_script,
        "--set", "block_global=false",
        "--set", "ssl_insecure=true",
    ]
    try:
        print(f"[UnifAI Guard] Launching MitM Security Interceptor on Port {port}...")
        mitmdump(args)
    except SystemExit as e:
        print(f"[UnifAI Guard WARNING] Proxy engine exited ({e})")
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Proxy engine stopped: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # CLI: UnifAI_Guard.exe --uninstall "KEY"  |  --uninstall-prompt
    if len(sys.argv) >= 2 and sys.argv[1] in ("--uninstall", "/uninstall", "--uninstall-prompt"):
        setup_file_logging()
        if sys.argv[1] == "--uninstall-prompt":
            code = run_uninstall_prompt()
        else:
            key = sys.argv[2] if len(sys.argv) >= 3 else ""
            code = run_uninstall(key)
        sys.exit(code)

    log_path = setup_file_logging()
    if not ensure_single_instance():
        print("[UnifAI Guard] Already running. Exit.")
        return

    agent_id = get_or_create_agent_id()
    info = collect_agent_info(agent_id)
    os.environ["UNIFAI_AGENT_ID"] = agent_id
    os.environ["UNIFAI_AGENT_HOSTNAME"] = info["hostname"]

    print("==========================================================")
    print(f"   UnifAI Enterprise Desktop Security Guard Agent v{AGENT_VERSION}")
    print("==========================================================")
    print(f"[UnifAI Guard] Log file: {log_path}")
    print(f"[UnifAI Guard] Data dir: {data_dir()}")
    print(f"[UnifAI Guard] Agent ID: {agent_id}")
    print(f"[UnifAI Guard] Hostname: {info['hostname']} / User: {info['username']}")
    print(f"[UnifAI Guard] MAC: {info.get('mac_address') or '—'} / Transport: {info.get('transport_name') or '—'}")

    addon_script = get_resource_path("browser_ai_proxy.py")
    if not os.path.exists(addon_script):
        addon_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "browser_ai_proxy.py"))

    print(f"[UnifAI Guard] Proxy Addon: {addon_script}")
    print(f"[UnifAI Guard] Backend URL: {UNIFAI_BACKEND_URL}")
    print(f"[UnifAI Guard] Local proxy: {PROXY_ADDR}")

    check_backend()
    hb = send_heartbeat(agent_id)
    if heartbeat_wants_uninstall(hb):
        apply_admin_uninstall(agent_id)
        return

    pac = fetch_proxy_pac()
    if pac:
        write_local_pac(pac)
    else:
        write_local_pac(
            "// UnifAI — waiting for backend Target Websites\n"
            'function FindProxyForURL(url, host) { return "DIRECT"; }\n'
        )

    start_local_pac_http_server()
    set_windows_proxy_pac(enable=True, pac_url=pac_http_url())
    set_browser_quic(enable_quic=False)
    print("[UnifAI Guard] Chrome/Edge HTTP/3 (QUIC) disabled so Target Websites use the proxy.")
    if not install_ca_certificate():
        print("[UnifAI Guard ERROR] CA trust failed — open %LOCALAPPDATA%\\UnifAI\\Guard\\ca_install_status.txt")
        print("[UnifAI Guard ERROR] Without CA trust, browsers will not accept MITM HTTPS. Fix cert then restart Guard.")

    stop_event = threading.Event()
    threading.Thread(target=sync_pac_loop, args=(stop_event,), daemon=True).start()
    threading.Thread(target=heartbeat_loop, args=(agent_id, stop_event), daemon=True).start()

    def cleanup_and_exit(signum=None, frame=None):
        print("\n[UnifAI Guard] Shutting down agent...")
        stop_event.set()
        clear_guard_runtime()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    print("[UnifAI Guard] Agent is active. Sleep/shutdown keep monitoring; only uninstall stops Guard.")
    port = int(PROXY_ADDR.rsplit(":", 1)[-1] or "8085")
    try:
        while not stop_event.is_set():
            set_windows_proxy_pac(enable=True, pac_url=pac_http_url(), silent=True)
            run_proxy_server(addon_script, port=port)
            if stop_event.is_set():
                break
            print("[UnifAI Guard] Proxy stopped — staying Active, restarting in 2s (sleep/wake safe).")
            stop_event.wait(2)
    finally:
        stop_event.set()
        clear_guard_runtime()


if __name__ == "__main__":
    main()
