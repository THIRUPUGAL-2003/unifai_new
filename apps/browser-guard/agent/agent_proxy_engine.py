"""MitM proxy engine launcher for UnifAI Guard."""

from __future__ import annotations

import signal

from mitmproxy.tools.main import mitmdump

from agent_config import LISTEN_HOST, PROXY_ADDR, SERVER_MODE


def run_proxy_server(addon_script: str, port: int = 8085) -> None:
    # Endpoint mode stays on 127.0.0.1 so only this PC is intercepted.
    # Server/network mode binds 0.0.0.0 (or UNIFAI_LISTEN_HOST) for corp PAC.
    listen_host = (LISTEN_HOST or "127.0.0.1").strip() or "127.0.0.1"
    if not SERVER_MODE:
        # Force IPv4 localhost. On some Windows setups mitm binds [::]:port only;
        # PAC/Chrome use 127.0.0.1 → connect timeout → health fail-open DIRECT.
        listen_host = "127.0.0.1"
        try:
            cfg_host = (PROXY_ADDR or "").rsplit(":", 1)[0].strip()
            if cfg_host and cfg_host not in ("0.0.0.0", "*", "::"):
                listen_host = cfg_host
        except Exception:
            pass
    elif listen_host in ("*",):
        listen_host = "0.0.0.0"
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
