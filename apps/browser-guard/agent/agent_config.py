"""Runtime configuration and module-level config globals for UnifAI Guard."""

from __future__ import annotations

import json
import os
import sys

from guard_platform import data_dir

DEFAULT_BACKEND = ""  # Set UNIFAI_BACKEND_URL or SERVER_DOMAIN / unifai_guard_config.json backend_url
AGENT_VERSION = "1.6.25"
HEARTBEAT_SECONDS = 30
HEALTH_SECONDS = 45
_HEALTH_WHEN_PROXY_DOWN_SECONDS = 8
PAC_HTTP_HOST = "127.0.0.1"
PAC_HTTP_PORT = 18085
_FIRST_RUN_FLAG = "first_run_done.flag"


def exe_dir() -> str:
    """Directory for config next to the Guard binary / .app.

    Frozen layouts:
    - Windows: folder containing UnifAI_Guard.exe
    - macOS .app: Contents/Resources (preferred) or folder containing UnifAI_Guard.app
    """
    if getattr(sys, "frozen", False):
        d = os.path.dirname(os.path.abspath(sys.executable))
        norm = d.replace("\\", "/")
        if norm.endswith("/Contents/MacOS"):
            resources = os.path.abspath(os.path.join(d, "..", "Resources"))
            if os.path.isdir(resources):
                return resources
            # Parent of UnifAI_Guard.app (portable zip next to .app)
            return os.path.abspath(os.path.join(d, "..", "..", ".."))
        return d
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

    backend = pick("UNIFAI_BACKEND_URL", "backend_url", "").rstrip("/")
    if not backend:
        backend = (os.environ.get("SERVER_DOMAIN") or DEFAULT_BACKEND or "").strip().rstrip("/")
    if not backend:
        print(
            "[UnifAI Guard ERROR] backend_url missing — set UNIFAI_BACKEND_URL / SERVER_DOMAIN "
            "or backend_url in unifai_guard_config.json"
        )
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

    server_mode_raw = pick("UNIFAI_SERVER_MODE", "server_mode", "0").lower()
    server_mode = server_mode_raw in ("1", "true", "yes", "on", "server", "network")
    agent_type = pick("UNIFAI_AGENT_TYPE", "agent_type", "network" if server_mode else "endpoint").lower()
    if agent_type in ("server", "gateway", "corp", "shared"):
        agent_type = "network"
    if agent_type not in ("endpoint", "network"):
        agent_type = "network" if server_mode else "endpoint"
    listen_host = pick(
        "UNIFAI_LISTEN_HOST",
        "listen_host",
        "0.0.0.0" if server_mode else "127.0.0.1",
    )
    pac_advertise = pick("UNIFAI_PAC_ADVERTISE_ADDR", "pac_advertise_addr", "")
    if not pac_advertise:
        # Endpoint: PAC points at local bind. Network: prefer proxy_addr if it is a
        # reachable hostname; otherwise leave empty so IT sets advertise explicitly.
        if not server_mode:
            pac_advertise = proxy_addr
        elif proxy_addr and not proxy_addr.startswith(("0.0.0.0:", "*:")):
            pac_advertise = proxy_addr

    os.environ["UNIFAI_BACKEND_URL"] = backend
    os.environ["UNIFAI_PROXY_ADDR"] = proxy_addr
    os.environ["UNIFAI_PAC_URL"] = pac_url
    os.environ["UNIFAI_PAC_SYNC_SECONDS"] = str(sync_secs)
    os.environ["UNIFAI_SERVER_MODE"] = "1" if server_mode else "0"
    os.environ["UNIFAI_AGENT_TYPE"] = agent_type
    os.environ["UNIFAI_LISTEN_HOST"] = listen_host
    if pac_advertise:
        os.environ["UNIFAI_PAC_ADVERTISE_ADDR"] = pac_advertise

    # Keep a copy in data_dir so logs/support can see active config
    try:
        with open(os.path.join(data_dir(), "unifai_guard_config.json"), "w", encoding="utf-8") as f:
            json.dump(
                {
                    "backend_url": backend,
                    "proxy_addr": proxy_addr,
                    "pac_url": pac_url,
                    "pac_sync_seconds": int(sync_secs),
                    "server_mode": server_mode,
                    "agent_type": agent_type,
                    "listen_host": listen_host,
                    "pac_advertise_addr": pac_advertise,
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
        "server_mode": server_mode,
        "agent_type": agent_type,
        "listen_host": listen_host,
        "pac_advertise_addr": pac_advertise,
    }


_CFG = load_runtime_config()
UNIFAI_BACKEND_URL = _CFG["backend_url"]
PAC_URL = _CFG["pac_url"]
PROXY_ADDR = _CFG["proxy_addr"]
PAC_SYNC_SECONDS = _CFG["pac_sync_seconds"]
SERVER_MODE = bool(_CFG.get("server_mode"))
AGENT_TYPE = str(_CFG.get("agent_type") or "endpoint")
LISTEN_HOST = str(_CFG.get("listen_host") or "127.0.0.1")
PAC_ADVERTISE_ADDR = str(_CFG.get("pac_advertise_addr") or PROXY_ADDR)
