"""Backend heartbeat, fleet config merge, and admin uninstall handling."""

from __future__ import annotations

import json
import os
import threading

import agent_config
from agent_browser_policy import set_browser_quic
from agent_config import HEARTBEAT_SECONDS, SERVER_MODE, UNIFAI_BACKEND_URL
from agent_http import _http_json
from agent_identity import collect_agent_info
from agent_pac_orchestration import clear_guard_runtime, ensure_pac_still_on
from guard_platform import data_dir


def send_heartbeat(agent_id: str, status: str = "active") -> dict | None:
    info = collect_agent_info(agent_id, status=status)
    code, data = _http_json("POST", f"{UNIFAI_BACKEND_URL}/api/browser-ai/agents/heartbeat", info)
    if code == 200:
        print(f"[UnifAI Guard] Heartbeat OK ({info.get('hostname')} / {info.get('ip_address')} / {info.get('mac_address')} / {status})")
        apply_fleet_config_from_heartbeat(data if isinstance(data, dict) else None)
        return data if isinstance(data, dict) else {}
    print(f"[UnifAI Guard WARNING] Heartbeat failed status={code} body={data}")
    return None


def apply_fleet_config_from_heartbeat(data: dict | None) -> None:
    """Merge company fleet defaults from Postgres (via heartbeat) into this process."""
    if not isinstance(data, dict):
        return
    fleet = data.get("fleet_config")
    if not isinstance(fleet, dict):
        return
    try:
        sync = int(fleet.get("pac_sync_seconds") or 0)
        if sync >= 2:
            agent_config.PAC_SYNC_SECONDS = min(sync, 600)
            os.environ["UNIFAI_PAC_SYNC_SECONDS"] = str(agent_config.PAC_SYNC_SECONDS)
    except Exception:
        pass
    adv = str(fleet.get("pac_advertise_addr") or "").strip()
    if adv and SERVER_MODE:
        agent_config.PAC_ADVERTISE_ADDR = adv
        os.environ["UNIFAI_PAC_ADVERTISE_ADDR"] = adv
    # Persist a copy for support under data_dir
    try:
        path = os.path.join(data_dir(), "fleet_config_from_db.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(fleet, f, indent=2)
    except Exception:
        pass


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
