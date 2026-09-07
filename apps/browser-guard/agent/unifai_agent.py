#!/usr/bin/env python3
"""
UnifAI Enterprise Security Guard Agent (Desktop)
================================================
Employee laptop agent for company deployments (Windows + macOS).

- Talks only to the UnifAI backend HTTPS API (no direct DB).
- Enables system PAC proxy for monitored Target Websites only.
- Registers heartbeat + agent identity in Browser AI.
- Logs to per-user UnifAI/Guard data dir.
- Autostart: Windows Run key / macOS LaunchAgent.
- Uninstall: UnifAI_Guard --uninstall "KEY"
"""

from __future__ import annotations

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
import time
import urllib.error
import urllib.request
import uuid

from mitmproxy.tools.main import mitmdump

from guard_platform import (
    IS_MAC,
    IS_WIN,
    ca_trusted as platform_ca_trusted,
    clear_autostart,
    data_dir,
    detect_mac_and_transport,
    ensure_single_instance as platform_ensure_single_instance,
    firefox_profiles_dirs,
    install_ca_certificate as platform_install_ca,
    log_hint_path,
    prompt_uninstall_key as platform_prompt_uninstall_key,
    register_autostart,
    set_system_proxy_pac,
    show_message as platform_show_message,
    write_chrome_mac_proxy_policy,
)

if IS_WIN:
    import ctypes
    import winreg
else:
    ctypes = None  # type: ignore
    winreg = None  # type: ignore

# ---------------------------------------------------------------------------
# Paths / config
# ---------------------------------------------------------------------------

DEFAULT_BACKEND = "https://unifaiv2.dev-yp.com"
AGENT_VERSION = "1.6.19"
HEARTBEAT_SECONDS = 30
HEALTH_SECONDS = 45
PAC_HTTP_HOST = "127.0.0.1"
PAC_HTTP_PORT = 18085
_FIRST_RUN_FLAG = "first_run_done.flag"
_LAST_PAC_BUST = ""
_HEALTH_LOCK = threading.Lock()
_LAST_HEALTH: dict = {}


def exe_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


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
    Priority: ENV > exe-dir config > user data-dir config > defaults.
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
    # Default 3s: Monitor/Block host list enters PAC same few seconds (not 10–30s wait).
    sync_secs = pick("UNIFAI_PAC_SYNC_SECONDS", "pac_sync_seconds", "3")
    try:
        sync_i = int(float(sync_secs))
    except Exception:
        sync_i = 3
    # Floor 2s — 1s PAC churn felt like connection cuts; 2–3s still feels instant.
    sync_secs = str(max(2, min(sync_i, 600)))

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


def collect_agent_info(agent_id: str, status: str = "active") -> dict:
    hostname = socket.gethostname()
    username = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    mac, transport = detect_mac_and_transport()
    health = _LAST_HEALTH if isinstance(_LAST_HEALTH, dict) else {}
    hs = str(health.get("status") or "").strip()
    details = health.get("details") if isinstance(health.get("details"), list) else []
    detail_s = "; ".join(str(x) for x in details[:6])
    pac_mode = str(health.get("pac_mode") or "")
    if pac_mode and pac_mode not in detail_s:
        detail_s = f"pac={pac_mode}" + (f"; {detail_s}" if detail_s else "")
    return {
        "id": agent_id,
        "hostname": hostname,
        "username": username,
        "ip_address": detect_local_ip(),
        "mac_address": mac,
        "transport_name": transport,
        "os_version": platform.platform(),
        "agent_version": AGENT_VERSION,
        "health_status": hs or "unknown",
        "health_detail": detail_s,
        "pac_mode": pac_mode or "unknown",
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
    ticks = 0
    while not stop_event.is_set():
        data = send_heartbeat(agent_id, status="active")
        if heartbeat_wants_uninstall(data):
            apply_admin_uninstall(agent_id)
            return
        ticks += 1
        # Re-assert PAC only every ~2 min — every-30s registry poke can drop tunnels on Windows.
        if ticks % 4 == 1:
            ensure_pac_still_on(silent=True)
        set_browser_quic(enable_quic=False)
        stop_event.wait(HEARTBEAT_SECONDS)


def health_path() -> str:
    return os.path.join(data_dir(), "health.json")


def first_run_path() -> str:
    return os.path.join(data_dir(), _FIRST_RUN_FLAG)


def port_open(host: str, port: int, timeout: float = 0.6) -> bool:
    """True if TCP connect works. On Windows, also try ::1 when host is 127.0.0.1
    (mitm can briefly bind IPv6-only; PAC still uses 127.0.0.1 after listen-host fix)."""
    candidates = [host]
    if host in ("127.0.0.1", "localhost"):
        candidates.append("::1")
    for h in candidates:
        try:
            with socket.create_connection((h, port), timeout=timeout):
                return True
        except Exception:
            continue
    return False


def ca_trusted() -> bool:
    return platform_ca_trusted(os.path.join(data_dir(), "ca_install_status.txt"))


def _detect_pac_mode() -> str:
    """strict_proxy | fail_open_direct | bypass_chain | unknown — from local PAC file."""
    try:
        with open(local_pac_path(), "r", encoding="utf-8", errors="replace") as f:
            body = f.read()
    except Exception:
        return "unknown"
    if not body or "FindProxyForURL" not in body:
        return "unknown"
    upper = body.upper()
    # Health-loop all-DIRECT while :8085 is down
    if 'RETURN "DIRECT"' in upper.replace(" ", "") and "PROXY " not in upper:
        return "fail_open_direct"
    if "PROXY " in upper and "; DIRECT" in upper:
        return "bypass_chain"  # sticky DIRECT risk — should be stripped
    if "PROXY " in upper:
        return "strict_proxy"
    return "unknown"


def run_health_check(proxy_port: int | None = None) -> dict:
    """Probe backend, PAC, local proxy, CA — write health.json for support."""
    global _LAST_HEALTH
    if proxy_port is None:
        try:
            proxy_port = int(PROXY_ADDR.rsplit(":", 1)[-1] or "8085")
        except Exception:
            proxy_port = 8085

    checks: dict[str, bool] = {}
    details: list[str] = []

    targets = _http_get_text(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets?for=agent", "application/json", timeout=45)
    checks["backend_targets"] = bool(targets and "targets" in targets)
    if not checks["backend_targets"]:
        targets = _http_get_text(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets", "application/json", timeout=45)
        checks["backend_targets"] = bool(targets and "targets" in targets)
    if not checks["backend_targets"]:
        details.append("backend targets unreachable")

    pac_ok = False
    try:
        pac_body = _http_get_text(pac_http_url(), "application/x-ns-proxy-autoconfig,*/*", timeout=3)
        pac_ok = bool(pac_body and "FindProxyForURL" in pac_body)
    except Exception:
        pac_ok = False
    checks["local_pac"] = pac_ok
    if not pac_ok:
        details.append("local PAC HTTP not serving")

    checks["proxy_port"] = port_open("127.0.0.1", proxy_port)
    if not checks["proxy_port"]:
        details.append(f"proxy :{proxy_port} not listening")

    checks["ca_trusted"] = ca_trusted()
    if not checks["ca_trusted"]:
        details.append("CA trust missing or not OK")

    addon = get_resource_path("browser_ai_proxy.py")
    if not os.path.exists(addon):
        addon = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proxy", "browser_ai_proxy.py"))
    checks["proxy_script"] = os.path.isfile(addon)
    if not checks["proxy_script"]:
        details.append("browser_ai_proxy.py missing")

    pac_mode = _detect_pac_mode()
    checks["pac_strict"] = pac_mode == "strict_proxy" or (
        pac_mode == "fail_open_direct" and not checks.get("proxy_port")
    )
    if pac_mode == "bypass_chain":
        details.append("PAC still has PROXY;DIRECT bypass chain — traffic may skip Guard")
    elif pac_mode == "fail_open_direct" and checks.get("proxy_port"):
        details.append("PAC is all-DIRECT while proxy is up — browsers bypass Guard (Prompt Logs stay 0)")
        checks["pac_strict"] = False

    critical = ("backend_targets", "local_pac", "proxy_script")
    if (
        all(checks.get(k) for k in critical)
        and checks.get("ca_trusted")
        and checks.get("proxy_port")
        and pac_mode == "strict_proxy"
    ):
        status = "ok"
    elif checks.get("backend_targets") and checks.get("proxy_script"):
        status = "degraded"
    else:
        status = "error"

    report = {
        "status": status,
        "agent_version": AGENT_VERSION,
        "backend_url": UNIFAI_BACKEND_URL,
        "proxy_addr": PROXY_ADDR,
        "pac_mode": pac_mode,
        "checks": checks,
        "details": details,
        "updated_at": time_iso(),
    }
    with _HEALTH_LOCK:
        _LAST_HEALTH = report
    try:
        with open(health_path(), "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not write health.json: {e}")
    print(f"[UnifAI Guard] Health={status} checks={checks}")
    return report


def time_iso() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def health_loop(stop_event: threading.Event, proxy_port: int) -> None:
    # First check after proxy has had time to bind
    stop_event.wait(4)
    proxy_was_down = False
    fail_streak = 0
    while not stop_event.is_set():
        try:
            report = run_health_check(proxy_port)
            checks = report.get("checks") if isinstance(report, dict) else {}
            proxy_up = bool(checks.get("proxy_port"))
            # Require several misses before all-DIRECT — one blip must not sticky-bypass forever.
            if not proxy_up:
                fail_streak += 1
                # Faster fail-open: 2 misses (~90s) — PROXY-only PAC causes hard
                # ERR_PROXY_CONNECTION_FAILED while :8085 is restarting.
                if fail_streak >= 2:
                    write_local_pac(
                        "// UnifAI Guard — local proxy down; fail open until proxy returns.\n"
                        'function FindProxyForURL(url, host) { return "DIRECT"; }\n'
                    )
                    apply_pac_with_bust(silent=True, force_new=True)
                    proxy_was_down = True
                    print("[UnifAI Guard] Proxy port down x2 — PAC fail-open DIRECT (browsers stay online).")
            else:
                if fail_streak > 0 or proxy_was_down:
                    pac = fetch_proxy_pac()
                    if pac:
                        write_local_pac(pac)
                    apply_pac_with_bust(silent=True, force_new=True)
                    print("[UnifAI Guard] Proxy healthy again — PAC restored (forced browser refetch).")
                    proxy_was_down = False
                else:
                    # Healthy steady-state: do NOT rotate ?v= (avoids mid-session disconnects).
                    ensure_pac_still_on(silent=True)
                fail_streak = 0
                # Keep CA trust healthy without DB — retry install if missing.
                if not ca_trusted():
                    print("[UnifAI Guard] CA not trusted — retrying certificate install…")
                    install_ca_certificate()
            set_browser_quic(enable_quic=False)
        except Exception as e:
            print(f"[UnifAI Guard WARNING] Health loop: {e}")
        stop_event.wait(HEALTH_SECONDS)


def show_message(title: str, text: str, flags: int = 0x40) -> None:
    """Native dialog (Windows MessageBox / macOS AppleScript). flags 0x10 = error."""
    platform_show_message(title, text, error=(flags & 0x10) != 0)


def maybe_first_run_prompt() -> None:
    path = first_run_path()
    if os.path.isfile(path):
        return
    browsers = (
        "Chrome, Edge, Brave, Opera, Vivaldi, Firefox, Safari"
        if IS_MAC
        else "Chrome, Edge, Brave, Opera, Vivaldi, Firefox"
    )
    show_message(
        "UnifAI Guard installed",
        "UnifAI Guard is running.\n\n"
        "For Browser AI monitoring & predict to work:\n"
        f"1) Fully quit every browser you use ({browsers})\n"
        "2) Reopen the browser and visit a monitored AI site\n"
        "3) Send a test prompt\n\n"
        f"Version {AGENT_VERSION}\n"
        f"Backend: {UNIFAI_BACKEND_URL}\n"
        f"Logs: {log_hint_path()}",
    )
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(AGENT_VERSION + "\n")
    except Exception:
        pass


def apply_pac_with_bust(silent: bool = False, force_new: bool = False) -> bool:
    """Enable PAC. Change AutoConfigURL only when PAC content changes or force_new=True.

    Frequent ?v= rotation (old 30s time-slice) forced browsers to rebind proxy and
    dropped live ChatGPT/Claude tunnels — felt like random connection cuts.
    """
    global _LAST_PAC_BUST
    try:
        content = ""
        path = local_pac_path()
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        content_hash = abs(hash(content or PROXY_ADDR)) % 1000000007
        if force_new:
            bust = (content_hash + int(time.time() * 1000)) % 1000000007
        else:
            bust = content_hash
        pac_url = f"{pac_http_url()}?v={bust}"
        if not force_new and _LAST_PAC_BUST == pac_url:
            return ensure_pac_still_on(silent=silent)
        _LAST_PAC_BUST = pac_url
        return set_system_proxy_pac_and_browsers(enable=True, pac_url=pac_url, silent=silent)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] PAC apply failed: {e}")
        return set_system_proxy_pac_and_browsers(enable=True, pac_url=pac_http_url(), silent=silent)


def ensure_pac_still_on(silent: bool = True) -> bool:
    """Keep PAC enabled with the last URL — no cache-bust churn."""
    url = _LAST_PAC_BUST or pac_http_url()
    try:
        return set_system_proxy_pac_and_browsers(enable=True, pac_url=url, silent=silent)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] PAC re-assert failed: {e}")
        return False


def pac_fail_open_direct(reason: str = "") -> None:
    """Temporary all-DIRECT so browsers stay online while local proxy restarts."""
    note = reason or "local proxy restarting"
    write_local_pac(
        f"// UnifAI Guard — {note}\n"
        'function FindProxyForURL(url, host) { return "DIRECT"; }\n'
    )
    apply_pac_with_bust(silent=True, force_new=True)
    print(f"[UnifAI Guard] PAC fail-open DIRECT ({note})")


def pac_restore_strict_proxy() -> None:
    pac = fetch_proxy_pac()
    if pac:
        write_local_pac(pac)
    else:
        built = build_pac_from_targets(PROXY_ADDR)
        if built:
            write_local_pac(built)
    apply_pac_with_bust(silent=True, force_new=True)
    print("[UnifAI Guard] PAC restored to strict PROXY (monitored hosts).")


def clear_guard_runtime() -> None:
    set_system_proxy_pac_and_browsers(enable=False)
    set_browser_quic(enable_quic=True)
    clear_autostart()


def prompt_uninstall_key() -> str | None:
    return platform_prompt_uninstall_key()


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
    return platform_ensure_single_instance()


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
        if path in ("/status", "/health"):
            report = _LAST_HEALTH if isinstance(_LAST_HEALTH, dict) and _LAST_HEALTH else {"status": "starting", "agent_version": AGENT_VERSION}
            body = json.dumps(report, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/", "/status.html"):
            report = _LAST_HEALTH if isinstance(_LAST_HEALTH, dict) else {}
            st = html_escape(str(report.get("status") or "starting"))
            ver = html_escape(AGENT_VERSION)
            backend = html_escape(UNIFAI_BACKEND_URL)
            checks = report.get("checks") if isinstance(report.get("checks"), dict) else {}
            rows = "".join(
                f"<tr><td>{html_escape(k)}</td><td>{'OK' if v else 'FAIL'}</td></tr>" for k, v in checks.items()
            )
            details = report.get("details") if isinstance(report.get("details"), list) else []
            det = "<br/>".join(html_escape(str(d)) for d in details) or "—"
            html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/><title>UnifAI Guard</title>
<style>body{{font-family:Segoe UI,sans-serif;background:#0b1220;color:#e2e8f0;padding:24px}}
.card{{background:#111827;border:1px solid #334155;border-radius:12px;padding:20px;max-width:720px}}
h1{{margin:0 0 8px;font-size:20px}} .ok{{color:#34d399}} .bad{{color:#f87171}} .deg{{color:#fbbf24}}
table{{width:100%;border-collapse:collapse;margin-top:12px}} td,th{{border-bottom:1px solid #334155;padding:8px;text-align:left;font-size:13px}}
</style></head><body><div class="card">
<h1>UnifAI Guard {ver}</h1>
<p>Status: <strong class="{'ok' if st=='ok' else 'deg' if st=='degraded' else 'bad'}">{st}</strong></p>
<p>PAC mode: <code>{html_escape(str(report.get("pac_mode") or "unknown"))}</code> (strict_proxy = intercepts; fail_open_direct / bypass_chain = Prompt Logs stay 0)</p>
<p>Backend: <code>{backend}</code></p>
<p>Local status API: <code>/status</code></p>
<table><thead><tr><th>Check</th><th>Result</th></tr></thead><tbody>{rows}</tbody></table>
<p style="margin-top:16px;font-size:12px;color:#94a3b8">Details: {det}</p>
<p style="font-size:12px;color:#94a3b8">Chrome, Edge, Brave, Opera, Vivaldi, and Firefox use the same Guard PAC. Fully quit &amp; reopen after install. Safari is macOS-only (not supported by Windows Guard).</p>
</div></body></html>"""
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path not in ("/proxy.pac", "/pac"):
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


def html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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

# Chromium-family policy keys (PAC + QuicAllowed). Safari is macOS-only — not on Windows Guard.
_CHROMIUM_POLICY_PATHS = (
    r"Software\Policies\Google\Chrome",
    r"Software\Policies\Google\Chrome Beta",
    r"Software\Policies\Google\Chrome Dev",
    r"Software\Policies\Google\Chrome SxS",
    r"Software\Policies\Microsoft\Edge",
    r"Software\Policies\Microsoft\Edge Beta",
    r"Software\Policies\Microsoft\Edge Dev",
    r"Software\Policies\Microsoft\Edge SxS",
    r"Software\Policies\BraveSoftware\Brave",
    r"Software\Policies\BraveSoftware\Brave-Browser",
    r"Software\Policies\Opera Software\Opera",
    r"Software\Policies\Opera Software\Opera Stable",
    r"Software\Policies\Opera Software\Opera GX",
    r"Software\Policies\Vivaldi",
    r"Software\Policies\Chromium",
    r"Software\Google\Chrome",
    r"Software\Microsoft\Edge",
    r"Software\BraveSoftware\Brave",
    r"Software\Opera Software\Opera",
    r"Software\Vivaldi",
)

_FIREFOX_PREF_MARKER_BEGIN = "// --- UnifAI Guard BEGIN ---"
_FIREFOX_PREF_MARKER_END = "// --- UnifAI Guard END ---"


def _notify_wininet() -> None:
    if not IS_WIN or ctypes is None:
        return
    try:
        ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
        ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)
    except Exception:
        pass


def _set_reg_dword(root, path: str, name: str, value: int) -> bool:
    if not IS_WIN or winreg is None:
        return False
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _set_reg_sz(root, path: str, name: str, value: str) -> bool:
    if not IS_WIN or winreg is None:
        return False
    try:
        key = winreg.CreateKeyEx(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def _delete_reg_value(root, path: str, name: str) -> None:
    if not IS_WIN or winreg is None:
        return
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except Exception:
        pass


def _apply_chromium_browser_policies(enable: bool, pac_url: str | None = None) -> int:
    """Apply the same PAC + QUIC/DoH settings Chrome uses to every Chromium-family browser."""
    if not IS_WIN or winreg is None:
        return 0
    if pac_url is None:
        pac_url = pac_http_url()
    applied = 0
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for path in _CHROMIUM_POLICY_PATHS:
            try:
                if enable:
                    if _set_reg_sz(root, path, "ProxyMode", "pac_script"):
                        applied += 1
                    _set_reg_sz(root, path, "ProxyPacUrl", pac_url)
                    _set_reg_dword(root, path, "QuicAllowed", 0)
                    # Keep DNS-over-HTTPS off so Edge/Brave/Opera route like Chrome through PAC.
                    _set_reg_sz(root, path, "DnsOverHttpsMode", "off")
                else:
                    for name in ("ProxyMode", "ProxyPacUrl", "DnsOverHttpsMode"):
                        _delete_reg_value(root, path, name)
            except Exception as e:
                print(f"[UnifAI Guard WARNING] Could not update browser policy on {path}: {e}")
    return applied


def set_browser_quic(enable_quic: bool) -> None:
    if not IS_WIN:
        return
    value = 1 if enable_quic else 0
    ok = False
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for path in _CHROMIUM_POLICY_PATHS:
            if _set_reg_dword(root, path, "QuicAllowed", value):
                ok = True
    if not ok and not enable_quic:
        print("[UnifAI Guard WARNING] Could not disable browser HTTP/3 (QUIC). Some sites may bypass the proxy.")


def set_browser_pac_policy(enable: bool, pac_url: str | None = None) -> None:
    """Force browsers onto the same Guard PAC (Windows Chromium policies + Firefox profiles on all OS)."""
    if pac_url is None:
        pac_url = pac_http_url()
    applied = _apply_chromium_browser_policies(enable=enable, pac_url=pac_url)
    set_firefox_proxy_policy(enable=enable, pac_url=pac_url)
    if IS_MAC:
        write_chrome_mac_proxy_policy(enable=enable, pac_url=pac_url)
    if enable:
        if IS_WIN:
            if applied:
                print(
                    "[UnifAI Guard] PAC applied to Chrome, Edge, Brave, Opera, Vivaldi (+ Firefox profiles). "
                    "Fully quit & reopen each browser once."
                )
            else:
                print("[UnifAI Guard WARNING] Could not set Chromium PAC policy — try restarting Guard as admin.")
        else:
            print(
                "[UnifAI Guard] System auto-proxy PAC + Firefox prefs applied. "
                "Fully quit & reopen Chrome/Safari/Firefox once."
            )
    else:
        print("[UnifAI Guard] Browser PAC policies cleared.")


def _firefox_profiles_dirs() -> list[str]:
    return firefox_profiles_dirs()


def _firefox_guard_pref_block(pac_url: str) -> str:
    # network.proxy.type 2 = PAC / autoconfig URL
    esc = pac_url.replace("\\", "\\\\").replace('"', '\\"')
    return "\n".join(
        [
            _FIREFOX_PREF_MARKER_BEGIN,
            f'user_pref("network.proxy.type", 2);',
            f'user_pref("network.proxy.autoconfig_url", "{esc}");',
            'user_pref("network.proxy.share_proxy_settings", true);',
            'user_pref("security.enterprise_roots.enabled", true);',
            'user_pref("network.http.http3.enable", false);',
            'user_pref("network.http.http3.enable_0rtt", false);',
            _FIREFOX_PREF_MARKER_END,
            "",
        ]
    )


def _strip_firefox_guard_block(text: str) -> str:
    begin = text.find(_FIREFOX_PREF_MARKER_BEGIN)
    if begin < 0:
        return text
    end = text.find(_FIREFOX_PREF_MARKER_END, begin)
    if end < 0:
        return text[:begin].rstrip() + "\n"
    end += len(_FIREFOX_PREF_MARKER_END)
    while end < len(text) and text[end] in "\r\n":
        end += 1
    return (text[:begin].rstrip() + "\n" + text[end].lstrip()) if text[end:] else text[:begin].rstrip() + "\n"


def _write_firefox_user_js(profile_dir: str, enable: bool, pac_url: str) -> bool:
    path = os.path.join(profile_dir, "user.js")
    try:
        existing = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                existing = f.read()
        cleaned = _strip_firefox_guard_block(existing)
        if enable:
            cleaned = cleaned.rstrip() + "\n" + _firefox_guard_pref_block(pac_url)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(cleaned if cleaned.endswith("\n") else cleaned + "\n")
        return True
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Firefox user.js update failed ({profile_dir}): {e}")
        return False


def _write_firefox_policies_json(enable: bool, pac_url: str) -> None:
    """Best-effort enterprise policies.json next to Firefox installs (needs write access)."""
    policy = {
        "policies": {
            "Proxy": {
                "Mode": "autoConfig",
                "AutoConfigURL": pac_url,
                "Locked": True,
            },
            "Certificates": {"ImportEnterpriseRoots": True},
            "Preferences": {
                "network.http.http3.enable": {"Value": False, "Status": "locked"},
                "security.enterprise_roots.enabled": {"Value": True, "Status": "locked"},
            },
        }
    }
    roots: list[str] = []
    if IS_WIN:
        roots = [
            os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Mozilla Firefox"),
            os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Mozilla Firefox"),
        ]
        local = os.environ.get("LOCALAPPDATA") or ""
        if local:
            roots.append(os.path.join(local, "Mozilla Firefox"))
    elif IS_MAC:
        roots = [
            "/Applications/Firefox.app/Contents/Resources",
            os.path.expanduser("~/Applications/Firefox.app/Contents/Resources"),
        ]
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        dist = os.path.join(root, "distribution")
        path = os.path.join(dist, "policies.json")
        try:
            if not enable:
                if os.path.isfile(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                        proxy = ((existing or {}).get("policies") or {}).get("Proxy") or {}
                        if str(proxy.get("AutoConfigURL") or "").startswith("http://127.0.0.1:"):
                            os.remove(path)
                    except Exception:
                        pass
                continue
            os.makedirs(dist, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(policy, f, indent=2)
            print(f"[UnifAI Guard] Firefox policies.json -> {path}")
        except Exception:
            pass


def set_firefox_proxy_policy(enable: bool, pac_url: str | None = None) -> None:
    """Point Firefox at Guard PAC (+ Windows enterprise roots for MITM CA)."""
    if pac_url is None:
        pac_url = pac_http_url()
    profiles = _firefox_profiles_dirs()
    ok = 0
    for p in profiles:
        if _write_firefox_user_js(p, enable=enable, pac_url=pac_url):
            ok += 1
    _write_firefox_policies_json(enable=enable, pac_url=pac_url)
    if IS_WIN and winreg is not None:
        try:
            key = winreg.CreateKeyEx(
                winreg.HKEY_CURRENT_USER,
                r"Software\Policies\Mozilla\Firefox",
                0,
                winreg.KEY_SET_VALUE,
            )
            if enable:
                winreg.SetValueEx(key, "ImportEnterpriseRoots", 0, winreg.REG_DWORD, 1)
            else:
                try:
                    winreg.DeleteValue(key, "ImportEnterpriseRoots")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[UnifAI Guard WARNING] Firefox registry policy: {e}")
    if enable:
        if ok:
            print(f"[UnifAI Guard] Firefox PAC applied to {ok} profile(s). Fully quit & reopen Firefox.")
        else:
            print("[UnifAI Guard] Firefox not found yet — open Firefox once, then restart Guard to apply PAC.")
    else:
        print("[UnifAI Guard] Firefox Guard prefs cleared (restart Firefox).")


def set_system_proxy_pac_and_browsers(enable: bool, pac_url: str | None = None, silent: bool = False) -> bool:
    """System PAC (Windows Internet Settings / macOS networksetup) + browser policies."""
    if pac_url is None:
        pac_url = pac_http_url()
    ok = set_system_proxy_pac(enable=enable, pac_url=pac_url, silent=silent)
    set_browser_pac_policy(enable=enable, pac_url=pac_url)
    if IS_WIN:
        _notify_wininet()
    return ok


def set_windows_proxy_pac(enable: bool, pac_url: str | None = None, silent: bool = False) -> bool:
    return set_system_proxy_pac_and_browsers(enable=enable, pac_url=pac_url, silent=silent)


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
    targets = _http_get_text(
        f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets?for=agent",
        "application/json",
        timeout=45,
    )
    if not (targets and ("targets" in targets or targets.strip().startswith("{"))):
        targets = _http_get_text(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets",
            "application/json",
            timeout=45,
        )
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
    body = _http_get_text(
        f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets?for=agent",
        "application/json",
        timeout=45,
    )
    if not body:
        body = _http_get_text(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets",
            "application/json",
            timeout=45,
        )
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
    # Collapse children covered by a parent already in the list (no product hardcoding).
    host_set = set(hosts)
    minimized: list[str] = []
    for d in hosts:
        parts = d.split(".")
        covered = False
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in host_set:
                covered = True
                break
        if not covered:
            minimized.append(d)
    hosts = minimized

    lines = [
        "// UnifAI Browser AI Guard — admin Target Websites from dashboard only.",
        "// Parent domains preferred when children are covered by subdomain match.",
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
        "            // Strict: monitored hosts MUST use Guard. Fail-open is health_loop all-DIRECT only.",
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
            return ensure_pac_strict_proxy(body)
    print("[UnifAI Guard] Server PAC unavailable — building PAC from /api/browser-ai/targets")
    return build_pac_from_targets(PROXY_ADDR)


def ensure_pac_strict_proxy(pac: str) -> str:
    """Monitored hosts use PROXY only while Guard is healthy.

    ``PROXY …; DIRECT`` caused silent bypass (sites work, Prompt Logs stay 0).
    When the local listener is down, health_loop rewrites PAC to all-DIRECT instead.
    """
    import re

    if not pac or "FindProxyForURL" not in pac:
        return pac

    # Normalize any "PROXY host:port; DIRECT" → "PROXY host:port"
    pac = re.sub(
        r'return\s*"\s*PROXY\s+([^";]+?)\s*;\s*DIRECT\s*"',
        lambda m: f'return "PROXY {m.group(1).strip()}"',
        pac,
        flags=re.IGNORECASE,
    )
    return pac


def write_local_pac(content: str) -> None:
    path = local_pac_path()
    try:
        # Never persist PROXY;DIRECT except intentional all-DIRECT fail-open from health_loop.
        if content and "PROXY " in content.upper():
            content = ensure_pac_strict_proxy(content)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"[UnifAI Guard] Wrote local proxy.pac ({path})")
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Could not write local proxy.pac: {e}")


def sync_pac_loop(stop_event: threading.Event) -> None:
    """Pull Target Website PAC from backend. Only rebind browsers when content actually changes.

    Rebinding AutoConfigURL drops live HTTPS tunnels (ChatGPT/Claude) — never do it on a timer alone.
    """
    last = ""
    while not stop_event.is_set():
        pac = fetch_proxy_pac()
        if pac and pac != last:
            write_local_pac(pac)
            # First load or real domain-list change only.
            apply_pac_with_bust(silent=False, force_new=(last != ""))
            last = pac
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
    status_path = os.path.join(data_dir(), "ca_install_status.txt")
    return platform_install_ca(status_path)


def run_proxy_server(addon_script: str, port: int = 8085) -> None:
    # Force IPv4 localhost. On some Windows setups mitm binds [::]:port only;
    # PAC/Chrome use 127.0.0.1 → connect timeout → health fail-open DIRECT (no Monitor/Block).
    listen_host = "127.0.0.1"
    try:
        cfg_host = (PROXY_ADDR or "").rsplit(":", 1)[0].strip()
        if cfg_host and cfg_host not in ("0.0.0.0", "*", "::"):
            listen_host = cfg_host
    except Exception:
        pass
    args = [
        "--listen-host", listen_host,
        "-p", str(port),
        "-s", addon_script,
        "--set", "block_global=false",
        "--set", "ssl_insecure=true",
    ]
    # mitmdump registers signal handlers; when launched from a supervise thread
    # Python raises ValueError ("signal only works in main thread") and the
    # proxy dies → PAC fail-open → Monitor/Block/predict all stop.
    _orig_signal = signal.signal

    def _thread_safe_signal(sig, handler):  # type: ignore[no-untyped-def]
        try:
            return _orig_signal(sig, handler)
        except ValueError:
            return None

    try:
        print(f"[UnifAI Guard] Launching MitM Security Interceptor on {listen_host}:{port}...")
        signal.signal = _thread_safe_signal  # type: ignore[assignment]
        mitmdump(args)
    except SystemExit as e:
        print(f"[UnifAI Guard WARNING] Proxy engine exited ({e})")
    except Exception as e:
        print(f"[UnifAI Guard ERROR] Proxy engine stopped: {e}")
    finally:
        signal.signal = _orig_signal  # type: ignore[assignment]


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
        addon_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "proxy", "browser_ai_proxy.py"))

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
    # Do NOT apply PAC until local mitmproxy is listening — otherwise browsers
    # hit PROXY;DIRECT, fail once, and stick on DIRECT (Claude works, logs stay 0).
    set_browser_quic(enable_quic=False)
    if IS_WIN:
        print("[UnifAI Guard] Browser HTTP/3 (QUIC) disabled for Chromium browsers so Target Websites use the proxy.")
        print("[UnifAI Guard] PAC policies: Chrome, Edge, Brave, Opera, Vivaldi + Firefox.")
    elif IS_MAC:
        print("[UnifAI Guard] macOS system Auto Proxy URL set; Safari/Chrome/Firefox follow system proxy.")
    if not install_ca_certificate():
        print(f"[UnifAI Guard ERROR] CA trust failed — open {log_hint_path()}/ca_install_status.txt")
        print("[UnifAI Guard ERROR] Without CA trust, browsers will not accept MITM HTTPS. Fix cert then restart Guard.")
        show_message(
            "UnifAI Guard — CA trust failed",
            "Certificate install failed.\nHTTPS intercept / predict may not work until CA is trusted.\n\n"
            f"See {log_hint_path()}/ca_install_status.txt",
            0x10,
        )

    try:
        if getattr(sys, "frozen", False):
            register_autostart(sys.executable)
    except Exception as e:
        print(f"[UnifAI Guard WARNING] Autostart: {e}")

    maybe_first_run_prompt()

    stop_event = threading.Event()
    port = int(PROXY_ADDR.rsplit(":", 1)[-1] or "8085")

    def proxy_supervise_loop() -> None:
        while not stop_event.is_set():
            try:
                run_proxy_server(addon_script, port=port)
            except Exception as e:
                print(f"[UnifAI Guard WARNING] Proxy crashed: {e}")
            if stop_event.is_set():
                break
            # Known restart window: fail-open FIRST so browsers do not get ERR_PROXY.
            pac_fail_open_direct("proxy engine restarting")
            print("[UnifAI Guard] Proxy stopped — staying Active, restarting in 2s (sleep/wake safe).")
            stop_event.wait(2)

    threading.Thread(target=proxy_supervise_loop, daemon=True).start()

    proxy_ready = False
    for _ in range(75):  # ~15s
        if port_open("127.0.0.1", port):
            proxy_ready = True
            break
        time.sleep(0.2)
    if proxy_ready:
        print(f"[UnifAI Guard] Local proxy listening on {PROXY_ADDR} — applying PAC now.")
        apply_pac_with_bust(silent=False, force_new=True)
    else:
        print("[UnifAI Guard WARNING] Proxy port not open yet — PAC deferred; health loop will apply when ready.")

    def proxy_ready_watch() -> None:
        """After a supervise restart, restore strict PROXY once :8085 is listening again."""
        was_up = proxy_ready
        while not stop_event.is_set():
            up = port_open("127.0.0.1", port)
            if up and not was_up:
                pac_restore_strict_proxy()
            was_up = up
            stop_event.wait(1)

    threading.Thread(target=proxy_ready_watch, daemon=True).start()
    # Cap AI Guard Bot hold so browsers do not drop the request (felt as connection cut).
    os.environ.setdefault("UNIFAI_EVAL_TIMEOUT", "18")
    threading.Thread(target=sync_pac_loop, args=(stop_event,), daemon=True).start()
    threading.Thread(target=heartbeat_loop, args=(agent_id, stop_event), daemon=True).start()
    threading.Thread(target=health_loop, args=(stop_event, port), daemon=True).start()

    def cleanup_and_exit(signum=None, frame=None):
        print("\n[UnifAI Guard] Shutting down agent...")
        stop_event.set()
        clear_guard_runtime()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup_and_exit)
    signal.signal(signal.SIGTERM, cleanup_and_exit)

    print("[UnifAI Guard] Agent is active. Sleep/shutdown keep monitoring; only uninstall stops Guard.")
    print("[UnifAI Guard] IMPORTANT: Fully quit Chrome/Edge (all windows) then reopen for PAC to stick.")
    try:
        while not stop_event.is_set():
            stop_event.wait(3600)
    finally:
        stop_event.set()
        clear_guard_runtime()


if __name__ == "__main__":
    main()
