"""First-run UX, uninstall flows, and native message wrappers."""

from __future__ import annotations

import os

from agent_config import AGENT_VERSION, UNIFAI_BACKEND_URL
from agent_health import first_run_path
from agent_http import _http_json
from agent_identity import get_or_create_agent_id
from agent_pac_orchestration import clear_guard_runtime
from guard_platform import (
    IS_MAC,
    log_hint_path,
    prompt_uninstall_key as platform_prompt_uninstall_key,
    show_message as platform_show_message,
)


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
