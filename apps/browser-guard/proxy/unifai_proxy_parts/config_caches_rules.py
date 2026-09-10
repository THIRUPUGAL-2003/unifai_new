# Part of UnifAI browser_ai_proxy — loaded via browser_ai_proxy.py into one shared namespace.
# Do not import this file directly.

#!/usr/bin/env python3
"""
UnifAI Browser AI Live Proxy Interceptor & DLP Guardrail Addon for mitmproxy.

Features:
- Real-time target domain fetching from UnifAI backend (/api/browser-ai/targets)
- Real-time DLP guard rule fetching from UnifAI backend (/api/browser-ai/rules)
- File upload detection and blocking
- WebSocket prompt interception
- SSE stream response injection for ChatGPT blocked prompts
- Telemetry and noise filtering
- Sends intercepted prompts to /api/browser-ai/intercept
"""

import asyncio
import base64
import io
import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from mitmproxy import http

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

# Backend URL (set by docker-compose environment variable)
UNIFAI_BACKEND_URL = os.getenv("UNIFAI_BACKEND_URL", "https://unifaiv2.dev-yp.com")
UNIFAI_AGENT_ID = os.getenv("UNIFAI_AGENT_ID", "")
UNIFAI_AGENT_HOSTNAME = os.getenv("UNIFAI_AGENT_HOSTNAME", "")
UNIFAI_AGENT_TYPE = (os.getenv("UNIFAI_AGENT_TYPE") or "").strip().lower()
UNIFAI_SERVER_MODE = (os.getenv("UNIFAI_SERVER_MODE") or "").strip().lower() in (
    "1", "true", "yes", "on", "server", "network",
)
if UNIFAI_AGENT_TYPE in ("server", "gateway", "corp", "shared"):
    UNIFAI_AGENT_TYPE = "network"
if not UNIFAI_AGENT_TYPE:
    UNIFAI_AGENT_TYPE = "network" if UNIFAI_SERVER_MODE else "endpoint"
if UNIFAI_AGENT_TYPE not in ("endpoint", "network"):
    UNIFAI_AGENT_TYPE = "endpoint"

# Stable network-proxy identity when Docker does not set UNIFAI_AGENT_ID.
if not UNIFAI_AGENT_ID and (UNIFAI_SERVER_MODE or UNIFAI_AGENT_TYPE == "network"):
    import socket as _socket
    UNIFAI_AGENT_ID = os.getenv("HOSTNAME") or _socket.gethostname() or "network-proxy"
    UNIFAI_AGENT_ID = f"network-{UNIFAI_AGENT_ID}".replace(" ", "-").lower()[:120]
if not UNIFAI_AGENT_HOSTNAME and (UNIFAI_SERVER_MODE or UNIFAI_AGENT_TYPE == "network"):
    import socket as _socket
    UNIFAI_AGENT_HOSTNAME = os.getenv("HOSTNAME") or _socket.gethostname() or "network-proxy"


def _agent_wire_fields() -> dict:
    return {
        "agent_id": UNIFAI_AGENT_ID,
        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
        "agent_type": UNIFAI_AGENT_TYPE,
    }


def _agent_metadata_fields() -> dict:
    return {
        "agent_id": UNIFAI_AGENT_ID,
        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
        "agent_type": UNIFAI_AGENT_TYPE,
    }


def _network_proxy_heartbeat_loop() -> None:
    """Register the shared/server proxy on the same Agents dashboard as laptop Guards."""
    if not (UNIFAI_SERVER_MODE or UNIFAI_AGENT_TYPE == "network"):
        return
    if not UNIFAI_BACKEND_URL or not UNIFAI_AGENT_ID:
        return
    import socket as _socket

    while True:
        try:
            payload = {
                "id": UNIFAI_AGENT_ID,
                "hostname": UNIFAI_AGENT_HOSTNAME or _socket.gethostname(),
                "username": "network-proxy",
                "ip_address": "",
                "os_version": "network-proxy",
                "agent_version": "mitm-addon",
                "agent_type": "network",
                "health_status": "ok",
                "health_detail": "shared network proxy",
                "status": "active",
            }
            req = urllib.request.Request(
                f"{UNIFAI_BACKEND_URL.rstrip('/')}/api/browser-ai/agents/heartbeat",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp.read()
        except Exception as e:
            print(f"[UnifAI Proxy WARNING] network heartbeat failed: {e}")
        time.sleep(30)


threading.Thread(target=_network_proxy_heartbeat_loop, daemon=True).start()

# Admin Monitor/Block toggles must feel instant.
# Background refresh uses a fixed 1s poll; rules refresh is coarser in the loop.
_BACKEND_FETCH_TIMEOUT = 45

# Empty by design — never seed product domains. Only admin Target Websites are monitored.
DEFAULT_TARGET_DOMAINS: dict = {}

# Generic upload path tokens — any admin-added domain, not a product list.
UPLOAD_ENDPOINTS = [
    "/files", "/file/", "/upload", "/uploads", "/attachment", "/attachments",
    "/v1/files", "/api/upload", "/file-upload", "/fileupload", "/process_upload",
    "/upload/", "/media/upload", "/resumable", "/filepush", "/pushfile",
    "/convert_document", "/upload_document", "/api/attachments",
    "/rest/uploads", "/file/upload",
]

_GENERIC_UPLOAD_PATH_MARKERS = (
    "/upload", "/uploads", "/files", "/file/", "/attachment", "/attachments",
    "/media/upload", "/convert_document", "/filepush",
    "/process_upload", "/file-upload", "/fileupload", "/resumable",
)

# Binary / document content-types used for local file attachments
UPLOAD_CONTENT_TYPES = (
    "multipart/form-data",
    "application/octet-stream",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-",
    "image/",
    "video/",
    "audio/",
)

# Paths to ignore (telemetry, analytics, pings, ChatGPT control-plane noise)
IGNORE_PATH_PATTERNS = [
    "/ces/v1/t", "/ces/", "/telemetry", "/analytics", "/segment",
    "/log", "/ping", "/tracking", "/monitoring",
    "/metrics", "/web-reports", "/title", "/rgstr", "/beacon", "/health",
    # ChatGPT / OpenAI non-prompt API calls
    "/sentinel/", "/conversation/init", "/generate_autocompletions",
    "/conversation/prepare", "/f/conversation/prepare",
    "/backend-api/conversation/prepare", "/backend-api/f/conversation/prepare",
    "/generate_autocompletions", "/conversation/implicit",
    "/connectors/", "/files/library",
    "/domainreliability/", "/service/update2",
    "/lat/r", "/backend-api/me", "/backend-api/accounts",
    "/backend-api/settings", "/backend-api/prompts",
    "/backend-api/shared_conversations", "/backend-api/gizmos",
    "/backend-api/system_hints", "/backend-api/conversation/init",
    # Cloudflare / bot challenges / fingerprint noise (NOT user prompts)
    "/cdn-cgi/", "/challenge-platform/", "/jsd/oneshot",
    "/api/v1/fm", "/cfm/", "/cf-challenge",
    # Perplexity / Claude noise endpoints
    "/search/v2/navigate", "/rest/rate_limits", "/api/event",
    "/api/telemetry", "/api/analytics", "/api/stats",
]

# Only these path markers are treated as real submitted chat prompts
CHAT_PATH_MARKERS = [
    "/conversation", "/completion", "/completions", "/chat/completions",
    "/messages", "/append_message", "/human_message", "/prompt",
    "/query", "/ask", "/generate", "/stream", "/batchexecute",
    "/backend-api/f/conversation", "/v1/messages", "/v1/chat",
    "/rest/prompts", "/api/chat", "/api/ask", "/api/query",
    "/api/openai/chat", "/perplexity_ask", "/rest/sse",
    "/api/copilot", "/chat", "/rest/thread", "/rest/entrypoint",
    "/computer/", "/rest/uploads",  # uploads still handled separately
    # Copilot / Bing Sydney
    "/sydney/", "/chatoverstream", "/getresponse", "/chathub", "/c/api/",
    "/api/v0/chat", "/api/v0/", "/backend-anon", "/turing/conversation",
    # Broader AI chat APIs (DeepSeek / Poe / HF / custom / enterprise bots)
    "/api/v1/chat", "/api/v2/chat", "/api/v3/chat", "/api/v4/chat",
    "/v1/completions", "/v2/completions", "/chat/api", "/ai/chat",
    "/llm/", "/aichat", "/send_message", "/send-message", "/submit",
    "/generate_response", "/generate-response", "/user_message",
    "/rpc/chat", "/gateway/chat", "/assistant", "/bots/", "/bot/",
    "/inference", "/predict", "/respond", "/reply",
    # Gemini generate APIs (StreamGenerate is the real chat submit; batchexecute is mostly RPC noise)
    "/streamgenerate", "/streamgeneratecontent", "/generatecontent", "/_$stream",
    "bardfrontendservice", "/bardchatui", "/_/bard",
]

GEMINI_CHAT_RPCS = {"hR32Ce", "vyAQhe", "wXbdQc", "BardFrontendService", "StreamGenerate"}

GEMINI_LOCALE_JUNK = {
    "en", "en-in", "en-us", "en-gb", "en-au", "ta-in", "hi-in",
    "es", "fr", "de", "it", "pt", "ja", "ko", "zh", "ru", "ar",
    "nl", "sv", "pl", "uk", "cs", "da", "fi", "el", "he", "th",
    "vi", "id", "ms", "bn", "te", "ml", "kn", "mr", "gu", "pa",
    "flash",
}

# Subdomains that are never chat UIs (analytics / CDN / challenges)
NOISE_HOST_PREFIXES = (
    "count.", "cdn.", "static.", "assets.", "telemetry.", "analytics.",
    "metrics.", "events.", "pixel.", "beacon.", "suggest.",
)

# Static asset noise (file extensions)
NOISE_EXTENSIONS = re.compile(
    r"\.(js|css|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|eot|map|webp)$",
    re.IGNORECASE
)

# Universal prompt field names — any admin-added domain, any JSON shape.
_UNIVERSAL_PROMPT_KEYS = (
    "query", "query_str", "prompt", "input", "input_text", "inputs", "text",
    "message", "question", "user_input", "last_query", "user_query",
    "rawUserQuery", "utterance", "userMessage", "content", "instruction",
    "search_query", "q", "follow_up_input", "user_message", "dsl_query",
    "search_focus", "user_text", "chat_input", "message_text", "entry",
    "followup", "follow_up", "search", "ask", "query_text",
    "prompt_text", "user_prompt", "userPrompt", "chat_message", "msg",
)

# Deduplicate identical events per domain within this window (seconds).
# Keep short so intentional same-text resends (~1s later) still predict;
# only collapses near-simultaneous browser double-submits.
DEDUPE_TTL = 4.0
# Longer window for upload/download blocks (ChatGPT fires many file API calls)
BLOCK_DEDUPE_TTL = 30
# Typing/request bursts (Grok/Copilot/…): Observe every keystroke request, Commit once.
# Same rule for ALL admin Target Websites — not per-domain hardcode.
COMPOSER_DRAFT_TTL = 0.55
COMPOSER_DRAFT_MAX_GROW = 8
# Adaptive quiet window before predict (keystroke HTTP looks like "Send" on many AIs).
COMPOSER_STABILITY_HOLD = 0.55
COMPOSER_STABILITY_HOLD_SHORT = 1.05  # len <= 12 (h→hi, digit drip)
COMPOSER_STABILITY_HOLD_TINY = 1.35   # len <= 3 (single chars / "hi")
COMPOSER_HOLD_MAX_LEN = 120
# If a longer prefix-related string appears within this window, shorter never commits.
COMPOSER_PREFIX_WINDOW = 2.5

# ─────────────────────────────────────────────
# In-memory Caches
# ─────────────────────────────────────────────

_cached_domains: dict = DEFAULT_TARGET_DOMAINS.copy()
_cached_blocked: dict = {}  # domain -> platform_name (full site lock)
_cached_roles: dict[str, str] = {}  # domain -> host_role (ui|chat|file|"")
# Admin Target Websites grouped for file-upload cache sharing (platform_name + parent_id).
_cached_families: dict[str, frozenset[str]] = {}
_cached_rules: list = []   # regex rules: {"name", "pattern", "regex", "action", "warning_message"}
_cached_rule_catalog: dict[str, dict] = {}  # all active rules by name — from admin UI only
_cached_has_ai_bot = False
_rules_fetch_ok = False  # True after at least one successful /rules fetch
_domains_fetched_at: float = 0
_rules_fetched_at: float = 0
_controls_fetched_at: float = 0
_controls_from_backend = False
_cache_lock = threading.RLock()
_bg_config_refresh_started = False
_recent_prompts: dict = {}  # key -> timestamp
# domain|prompt -> (ts, decision_tuple) so ChatGPT double-fire cannot bypass a BLOCK
_recent_decisions: dict = {}
_eval_inflight: dict = {}  # key -> threading.Event — coalesce parallel evaluates
_composer_draft: dict = {}  # domain -> (prompt, timestamp) — latest observed composer text
_composer_lock = threading.Lock()
_cached_controls: dict = {
    "enabled": False,
    "block_upload": False,
    "upload_warning": "",
}

_UPLOAD_FILE_CACHE: dict[str, dict] = {}
_UPLOAD_FILE_QUEUES: dict[str, list[dict]] = {}
_UPLOAD_FILE_CACHE_LOCK = threading.Lock()
_UPLOAD_FILE_CACHE_TTL = 15 * 60  # 15 minutes — keep bytes for View/Download
_UPLOAD_FILE_CACHE_MAX = 80
_UPLOAD_FILE_QUEUE_MAX = 32  # any count of files on one Send (images/docs/zips)
# Only treat "latest upload" as this Send's file if the upload was this recent.
# Prevents typed prompts from becoming "[FILE UPLOAD] attachment" after an old pick.
_UPLOAD_LATEST_MATCH_TTL = 10 * 60  # align with temp file View TTL / upload cache (was 5m)
_MULTI_FILE_VISION_MAX = 12  # images sent together to Guard Bot on one Send


def _fetch_json(url: str, timeout: float | None = None) -> dict | None:
    """Generic GET JSON fetch from backend."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout or _BACKEND_FETCH_TIMEOUT) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                if raw.lstrip().lower().startswith("<!doctype") or raw.lstrip().lower().startswith("<html"):
                    return None
                return json.loads(raw)
    except Exception as e:
        print(f"[UnifAI Proxy] backend GET failed | {url.split('?', 1)[0]} | {e}")
    return None


def _normalize_domain(raw: str) -> str:
    """Normalize admin Target domain values like 'https://example.com/' -> 'example.com'."""
    domain = (raw or "").strip().lower()
    if not domain:
        return ""
    # Strip scheme
    if "://" in domain:
        domain = domain.split("://", 1)[1]
    # Strip path/query/fragment and port
    domain = domain.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    if domain.startswith("[") and "]" in domain:
        domain = domain[1:domain.index("]")]
    elif ":" in domain:
        domain = domain.rsplit(":", 1)[0]
    # Strip leading www.
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _build_target_families(targets: list) -> dict[str, frozenset[str]]:
    """Group admin-added Target Websites for upload-cache sharing.

    Same platform_name, parent_id tree, or subdomain overlap → one family.
    No hardcoded product domain lists.
    """
    active: list[dict] = []
    for t in targets or []:
        d = _normalize_domain(t.get("domain", ""))
        if not d:
            continue
        if not (t.get("monitored") or t.get("block_site")):
            continue
        active.append({**t, "_domain": d})

    domains = [t["_domain"] for t in active]
    if not domains:
        return {}

    parent: dict[str, str] = {d: d for d in domains}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    id_to_domain = {t["id"]: t["_domain"] for t in active if t.get("id")}

    by_platform: dict[str, list[str]] = {}
    for t in active:
        d = t["_domain"]
        pname = (t.get("platform_name") or d).strip().lower()
        by_platform.setdefault(pname, []).append(d)
    for group in by_platform.values():
        for i in range(1, len(group)):
            union(group[0], group[i])

    for t in active:
        d = t["_domain"]
        pid = (t.get("parent_id") or "").strip()
        if pid and pid in id_to_domain:
            union(d, id_to_domain[pid])

    for d in domains:
        for other in domains:
            if d != other and (d.endswith("." + other) or other.endswith("." + d)):
                union(d, other)

    groups: dict[str, set[str]] = {}
    for d in domains:
        groups.setdefault(find(d), set()).add(d)

    return {d: frozenset(groups[find(d)]) for d in domains}


def _apply_targets_from_data(data: dict) -> None:
    """Update in-memory target maps from a successful backend payload."""
    global _cached_domains, _cached_blocked, _cached_roles, _cached_families, _domains_fetched_at
    targets = data.get("targets", []) if isinstance(data, dict) else []
    new_map = {}
    new_blocked = {}
    new_roles = {}
    for t in targets:
        domain = _normalize_domain(t.get("domain", ""))
        monitored = bool(t.get("monitored"))
        block_site = bool(t.get("block_site"))
        platform = t.get("platform_name") or domain or "AI Platform"
        role = (t.get("host_role") or "").strip().lower()
        if role not in ("ui", "chat", "file"):
            role = ""
        if domain and (monitored or block_site):
            new_map[domain] = platform
            new_roles[domain] = role
        if domain and block_site:
            new_blocked[domain] = platform
    with _cache_lock:
        _cached_domains = new_map
        _cached_blocked = new_blocked
        _cached_roles = new_roles
        _cached_families = _build_target_families(targets)
        _domains_fetched_at = time.time()
    print(
        f"[UnifAI Proxy] Refreshed {len(new_map)} target domains "
        f"({len(new_blocked)} full-site locks, {len(_cached_families)} upload families) from backend."
    )


def _refresh_targets_from_backend() -> None:
    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets?for=agent")
    if data is None:
        data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets")
    if data is not None:
        _apply_targets_from_data(data)
    elif not _cached_domains:
        print("[UnifAI Proxy] WARNING: target domains empty — monitoring idle until backend targets fetch succeeds.")


def _ensure_background_config_refresh() -> None:
    """Poll targets/rules/controls in a daemon thread — never block HTTPS request path.

    1594 targets × sync GET on every request made Monitor/Block feel broken and slow.
    Background 1s refresh = admin toggle applies within ~1s while proxy stays fast.
    """
    global _bg_config_refresh_started
    if _bg_config_refresh_started:
        return
    _bg_config_refresh_started = True

    def _loop() -> None:
        while True:
            try:
                _refresh_targets_from_backend()
            except Exception as e:
                print(f"[UnifAI Proxy] bg targets refresh: {e}")
            try:
                get_guard_rules(force_network=True)
            except Exception as e:
                print(f"[UnifAI Proxy] bg rules refresh: {e}")
            try:
                get_control_settings(force_network=True)
            except Exception as e:
                print(f"[UnifAI Proxy] bg controls refresh: {e}")
            time.sleep(1.0)

    threading.Thread(target=_loop, name="unifai-config-refresh", daemon=True).start()

    def _first_pull() -> None:
        try:
            _refresh_targets_from_backend()
        except Exception as e:
            print(f"[UnifAI Proxy] first targets pull: {e}")
        try:
            get_guard_rules(force_network=True)
        except Exception as e:
            print(f"[UnifAI Proxy] first rules pull: {e}")
        try:
            get_control_settings(force_network=True)
        except Exception as e:
            print(f"[UnifAI Proxy] first controls pull: {e}")

    # Immediate first pull — targets + rules + controls (avoid empty-regex cold start).
    threading.Thread(target=_first_pull, name="unifai-config-first-pull", daemon=True).start()


def get_target_domains() -> dict:
    """
    Instant in-memory Target map (Monitor + Block). Network refresh is background-only.
    """
    _ensure_background_config_refresh()
    # One-shot sync if we have never loaded (Guard just started).
    if _domains_fetched_at <= 0 and not _cached_domains:
        try:
            _refresh_targets_from_backend()
        except Exception:
            pass
    with _cache_lock:
        return _cached_domains


def detect_site_block(host: str) -> tuple[bool, str, str]:
    """Return (blocked, domain, platform) when admin enabled Block entire website."""
    get_target_domains()  # ensure bg refresh + memory maps
    host_lower = (host or "").lower().strip(".")
    with _cache_lock:
        blocked_map = dict(_cached_blocked)
    for domain, platform in blocked_map.items():
        if host_lower == domain or host_lower.endswith("." + domain):
            return True, domain, platform
    return False, "", ""


def make_site_blocked_response(flow: http.HTTPFlow, domain: str, platform: str) -> None:
    title = platform or domain or "this website"
    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Blocked by UnifAI Guard</title>
  <style>
    body {{ font-family: Segoe UI, system-ui, sans-serif; background:#0b1220; color:#e2e8f0;
           display:flex; align-items:center; justify-content:center; min-height:100vh; margin:0; }}
    .card {{ max-width:560px; padding:32px; border:1px solid #334155; border-radius:12px; background:#111827; }}
    h1 {{ margin:0 0 12px; font-size:22px; color:#f87171; }}
    p {{ margin:0 0 8px; line-height:1.5; color:#cbd5e1; }}
    code {{ background:#1e293b; padding:2px 6px; border-radius:4px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Website blocked by UnifAI Guard</h1>
    <p>Access to <strong>{title}</strong> (<code>{domain}</code>) is not allowed by your company policy.</p>
  </div>
</body>
</html>"""
    flow.response = http.Response.make(
        403,
        body.encode("utf-8"),
        {
            "Content-Type": "text/html; charset=utf-8",
            "Cache-Control": "no-store",
            "X-UnifAI-Blocked": "site",
        },
    )


def get_guard_rules(force_network: bool = False) -> list:
    """
    Fetch active DLP guard rules from UnifAI backend.
    Request path: memory only. Background thread uses force_network=True (~1s).
    Never falls back to hardcoded patterns.
    """
    global _cached_rules, _cached_rule_catalog, _cached_has_ai_bot, _rules_fetched_at, _rules_fetch_ok
    _ensure_background_config_refresh()
    now = time.time()
    if not force_network and _rules_fetched_at > 0:
        return _cached_rules

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/rules?for=agent")
    if data is None:
        data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/rules")
    if data is not None:
        rules = data.get("rules", [])
        compiled = []
        catalog: dict[str, dict] = {}
        # Top-level flag from lite API, else detect from rows
        has_ai_bot = bool(data.get("has_ai_bot"))
        for r in rules:
            # Agent lite always sends active=true; full API may include inactive.
            if "active" in r and not r.get("active", False):
                continue
            name = (r.get("name") or "").strip()
            rule_type = str(r.get("rule_type") or "regex").strip().lower()
            action = (r.get("action") or "BLOCK").upper()
            if action == "WARN":
                action = "REDACT"
            if name:
                catalog[name] = {
                    "name": name,
                    "rule_type": rule_type,
                    "action": action,
                    "warning_message": (r.get("warning_message") or "").strip(),
                    "pattern": (r.get("pattern") or "").strip(),
                }
            if rule_type == "ai_bot":
                has_ai_bot = True
            pattern = (r.get("pattern") or "").strip()
            if not pattern:
                continue
            try:
                compiled.append({
                    "name": name or "Unknown Rule",
                    "pattern": pattern,
                    "regex": _compile_guard_regex(pattern),
                    "action": action,
                    "severity": r.get("severity", "HIGH"),
                    "warning_message": (r.get("warning_message") or "").strip(),
                })
            except re.error as e:
                print(f"[UnifAI Proxy] WARNING: invalid regex skipped | {name!r} | {e}")
        with _cache_lock:
            _cached_rules = compiled
            _cached_rule_catalog = catalog
            _cached_has_ai_bot = has_ai_bot
            _rules_fetch_ok = True
            _rules_fetched_at = time.time()
        print(f"[UnifAI Proxy] Refreshed {len(compiled)} regex rules, {len(catalog)} active rules from backend.")
        return _cached_rules

    # Backend unreachable: keep last cache. Do NOT stamp success time — cold-start can retry.
    if not _cached_rules and not _rules_fetch_ok:
        print("[UnifAI Proxy] WARNING: guard rules empty — regex DLP idle until backend rules fetch succeeds.")
    return _cached_rules


def has_ai_bot_rules() -> bool:
    get_guard_rules()
    return bool(_cached_has_ai_bot)


def _prompt_decision_key(domain: str, prompt: str) -> str:
    return f"{(domain or '').strip().lower()}|{(prompt or '').strip().lower()}"


def remember_guard_decision(domain: str, prompt: str, decision: tuple) -> None:
    key = _prompt_decision_key(domain, prompt)
    _recent_decisions[key] = (time.time(), decision)
    # Bound memory
    if len(_recent_decisions) > 4000:
        cutoff = time.time() - BLOCK_DEDUPE_TTL
        dead = [k for k, (ts, _) in _recent_decisions.items() if ts < cutoff]
        for k in dead[:2000]:
            _recent_decisions.pop(k, None)


def get_remembered_guard_decision(domain: str, prompt: str, ttl: float = BLOCK_DEDUPE_TTL) -> tuple | None:
    key = _prompt_decision_key(domain, prompt)
    item = _recent_decisions.get(key)
    if not item:
        return None
    ts, decision = item
    if time.time() - ts > ttl:
        return None
    return decision


def evaluate_prompt_coalesced(
    platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str,
) -> tuple[bool, str, str, str, str]:
    """One evaluate per domain+prompt; parallel ChatGPT retries reuse the same decision."""
    cached = get_remembered_guard_decision(domain, prompt)
    if cached is not None:
        return cached

    key = _prompt_decision_key(domain, prompt)
    wait_ev = _eval_inflight.get(key)
    if wait_ev is not None:
        wait_ev.wait(timeout=100)
        cached = get_remembered_guard_decision(domain, prompt)
        if cached is not None:
            return cached
        # First call failed to publish — still enforce local regex (never silent allow).
        local = decide_prompt_locally(prompt)
        remember_guard_decision(domain, prompt, local if (not local[0] or (local[2] or "").lower() == "blocked" or local[2] in ("Redacted", "Warned")) else local)
        return local

    ev = threading.Event()
    _eval_inflight[key] = ev
    try:
        decision = evaluate_prompt(platform, domain, prompt, client_ip, url, method)
        remember_guard_decision(domain, prompt, decision)
        return decision
    finally:
        ev.set()
        _eval_inflight.pop(key, None)


def evaluate_prompt(platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str) -> tuple[bool, str, str, str, str]:
    """Regex (local, instant) + AI Guard Bot (backend) when needed; strictest action wins.

    At 1000+ rules/domains: regex BLOCK returns immediately (no LLM wait).
    AI bot runs only when local regex did not already block.
    """
    get_guard_rules()
    local = decide_prompt_locally(prompt)
    local_allowed, local_rt, local_action, local_fwd, local_reply = local

    # Instant path — do not wait on AI Guard Bot (up to ~95s) when regex already blocked.
    if (not local_allowed) or (local_action or "").lower() == "blocked":
        def _log_local_block() -> None:
            try:
                payload = json.dumps({
                    "platform": platform,
                    "prompt": prompt,
                    "client_ip": client_ip,
                    **_agent_wire_fields(),
                    "metadata": {
                        "domain": domain,
                        "url": url,
                        "method": method,
                        "is_blocked": True,
                        "blocked_reason": local_rt or "Guard Rule",
                        **_agent_metadata_fields(),
                    },
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=3)
            except Exception:
                pass

        threading.Thread(target=_log_local_block, daemon=True).start()
        return False, local_rt, local_action or "Blocked", local_fwd, local_reply

    # Sync backend when AI bots exist, or rules cache never loaded (do not fail-open).
    need_backend = has_ai_bot_rules() or (not _rules_fetch_ok)

    if need_backend:
        allowed, rt, action, forward, reply, eval_err = send_to_backend(platform, domain, prompt, client_ip, url, method)
        if eval_err:
            print(f"[UnifAI Proxy] AI Guard Bot prompt eval failed | {eval_err}")
            # Bot hang/timeout must not erase local regex — re-check before fail-open.
            local2 = decide_prompt_locally(prompt)
            if (not local2[0]) or (local2[2] or "").lower() == "blocked" or local2[2] in ("Redacted", "Warned"):
                return local2
        merged = _merge_guard_decisions(local, (allowed, rt, action, forward, reply))
        return merged

    if local_action in ("Redacted", "Warned"):
        log_prompt_async(platform, domain, prompt, client_ip, url, method)
        return local_allowed, local_rt, local_action, local_fwd, local_reply

    log_prompt_async(platform, domain, prompt, client_ip, url, method)
    return True, "", "Allowed", prompt, ""


def _fail_open() -> bool:
    return os.getenv("UNIFAI_FAIL_OPEN", "").strip() in ("1", "true", "TRUE", "yes", "YES")


def get_control_settings(force_network: bool = False) -> dict:
    """Fetch browser interaction controls. Request path = memory; bg poller force_network."""
    global _cached_controls, _controls_fetched_at, _controls_from_backend
    _ensure_background_config_refresh()
    if not force_network and _controls_fetched_at > 0:
        return _cached_controls

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/controls")
    if data and isinstance(data.get("controls"), dict):
        c = data["controls"]
        with _cache_lock:
            _cached_controls = {
                "enabled": bool(c.get("enabled", False)),
                "block_upload": bool(c.get("block_upload", False)),
                "upload_warning": (c.get("upload_warning") or "").strip(),
            }
            _controls_from_backend = True
            _controls_fetched_at = time.time()
        print(
            "[UnifAI Proxy] Controls refreshed | "
            f"enabled={_cached_controls['enabled']} "
            f"upload={_cached_controls['block_upload']}"
        )
    # Failure: do not stamp _controls_fetched_at — next force_network / cold path can retry.
    return _cached_controls


def controls_active(key: str) -> bool:
    """True when master enable is on and the named control is enabled.

    If controls were never loaded from the backend, do NOT invent policies
    (especially block_upload) — fail open until admin settings are fetched.
    """
    c = get_control_settings()
    if not _controls_from_backend:
        return False
    return bool(c.get("enabled")) and bool(c.get(key))


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────

def _compile_guard_regex(pattern: str):
    """Compile admin regex once. Strip nested (?i) so IGNORECASE is applied cleanly."""
    p = (pattern or "").strip()
    low = p[:4].lower()
    if low == "(?i)":
        p = p[4:]
    elif p[:5].lower() == "(?-i)":
        p = p[5:]
    return re.compile(p, re.IGNORECASE)


def rule_matches_prompt(rule: dict, prompt: str) -> bool:
    """True only when the admin-configured regex matches. No hardcoded DLP heuristics."""
    regex = rule.get("regex")
    if regex is None or not prompt:
        return False
    return bool(regex.search(prompt))


def _redacted_forward(prompt: str, warning_message: str = "") -> str:
    """ChatGPT receives full original prompt + redact notice. Logs keep original only."""
    w = (warning_message or "").strip() or "This prompt triggered a UnifAI Guard redaction policy."
    body = (prompt or "").rstrip()
    if body:
        return f"{body}\n\n[UNIFAI REDACTED] {w}"
    return f"[UNIFAI REDACTED] {w}"


def _redact_notice_for_rule(rule_name: str) -> str:
    """Build chat redaction notice from admin rule config only."""
    w = _warning_for_rule_name(rule_name)
    return _redacted_forward("", w).strip()


def _action_rank(action: str) -> int:
    a = (action or "").upper()
    if a in ("BLOCKED", "BLOCK"):
        return 3
    if a in ("REDACTED", "REDACT", "WARNED", "WARN"):
        return 2
    return 1


def _file_scan_guard_metadata(
    scanned: str,
    upload_images: list[str],
    rule_hit: bool,
    rule_name: str,
    rule_action: str,
    *,
    scan_evaluated: bool = False,
    scan_eval_error: str = "",
) -> dict:
    """Proxy scan decision for backend log — avoids duplicate guard evaluation."""
    has_content = bool((scanned or "").strip() or upload_images)
    if not has_content:
        return {}
    # Bot/backend failed — do NOT stamp security OK; backend will re-run AI Guard Bot.
    if (scan_eval_error or "").strip():
        return {
            "scan_guard_decided": True,
            "scan_guard_action": "Allowed",
            "scan_guard_eval_error": (scan_eval_error or "").strip()[:300],
        }
    if not scan_evaluated and not rule_hit:
        return {}
    meta: dict = {"scan_guard_decided": True}
    act = (rule_action or "").upper()
    if rule_hit and act == "BLOCK":
        meta["scan_guard_action"] = "Blocked"
    elif rule_hit and act in ("REDACT", "WARN"):
        meta["scan_guard_action"] = "Redacted"
    else:
        meta["scan_guard_action"] = "Allowed"
    if rule_hit and (rule_name or "").strip():
        meta["scan_rule_triggered"] = rule_name.strip()
        w = _warning_for_rule_name(rule_name)
        if w:
            meta["scan_warning_message"] = w
    return meta


def _merge_file_scan_backend(
    rule_hit: bool,
    rule_name: str,
    rule_action: str,
    allowed: bool,
    rt_name: str,
    action: str,
) -> tuple[bool, str, str]:
    """Merge backend file-scan result (regex + bot) into local rule decision."""
    rt = (rt_name or "").strip()
    if not rt:
        return rule_hit, rule_name, rule_action
    act = (action or "").upper()
    if (not allowed or act in ("BLOCKED", "BLOCK")) and act not in ("REDACTED", "REDACT", "WARNED", "WARN"):
        if _action_rank("BLOCK") >= _action_rank(rule_action):
            return True, rt, "BLOCK"
    elif act in ("REDACTED", "REDACT", "WARNED", "WARN"):
        if _action_rank("REDACT") >= _action_rank(rule_action):
            return True, rt, "REDACT"
    elif not allowed:
        if _action_rank("BLOCK") >= _action_rank(rule_action):
            return True, rt, "BLOCK"
    return rule_hit, rule_name, rule_action


def _merge_guard_decisions(
    local: tuple[bool, str, str, str, str],
    backend: tuple[bool, str, str, str, str] | None,
) -> tuple[bool, str, str, str, str]:
    """Merge regex (local) + AI bot (backend). BLOCK beats REDACT beats ALLOW."""
    allowed_l, rule_l, action_l, forward_l, reply_l = local
    if backend is None:
        return local
    allowed_b, rule_b, action_b, forward_b, reply_b = backend
    rank_l = _action_rank(action_l)
    rank_b = _action_rank(action_b)
    if not allowed_l:
        rank_l = max(rank_l, 3)
    if not allowed_b:
        rank_b = max(rank_b, 3)
    if rank_l >= rank_b:
        pick = (allowed_l, rule_l, action_l, forward_l, reply_l)
    else:
        pick = (allowed_b, rule_b, action_b, forward_b, reply_b)
    allowed, rule, action, forward, reply = pick
    if _action_rank(action) >= 3:
        allowed = False
        action = "Blocked"
    elif _action_rank(action) >= 2 and action not in ("Redacted",):
        action = "Redacted"
    return allowed, rule, action, forward, reply


def decide_prompt_locally(prompt: str) -> tuple[bool, str, str, str, str]:
    """Apply admin-added regex rules only; strictest action wins (BLOCK > REDACT)."""
    rules = list(get_guard_rules())

    def _prio(r: dict) -> tuple:
        action = (r.get("action") or "BLOCK").upper()
        if action == "WARN":
            action = "REDACT"
        # BLOCK before REDACT — admin rules only.
        return (0 if action == "BLOCK" else 1,)

    rules.sort(key=_prio)

    best_redact = None
    for r in rules:
        if not rule_matches_prompt(r, prompt):
            continue
        rule_action = (r.get("action") or "BLOCK").upper()
        if rule_action == "WARN":
            rule_action = "REDACT"
        if rule_action == "BLOCK":
            return False, r["name"], "Blocked", prompt, _security_reply_text(r["name"], r.get("warning_message", ""))
        if rule_action == "REDACT" and best_redact is None:
            best_redact = r

    if best_redact is not None:
        r = best_redact
        return True, r["name"], "Redacted", _redacted_forward(prompt, r.get("warning_message", "")), ""

    # No built-in / hardcoded DLP patterns — only admin-added rules above.
    return True, "", "Allowed", prompt, ""


def log_prompt_async(platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str) -> None:
    def _run() -> None:
        try:
            send_to_backend(platform, domain, prompt, client_ip, url, method)
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()


def is_noise_host(host: str) -> bool:
    """Skip analytics / CDN / challenge hosts that share a parent AI domain."""
    h = (host or "").lower().strip(".")
    if not h:
        return True
    # Explicit noise hosts
    if h.startswith(NOISE_HOST_PREFIXES):
        return True
    if "cdn-cgi" in h or h.startswith("count."):
        return True
    return False


def _path_has_ignore_pattern(path: str) -> bool:
    """Match ignore tokens as path segments, not substrings (/event must not match /event-stream)."""
    p = (path or "").lower().split("?", 1)[0]
    if not p:
        return False
    for n in IGNORE_PATH_PATTERNS:
        n = (n or "").lower()
        if not n:
            continue
        if n.endswith("/"):
            if n in p:
                return True
            continue
        idx = 0
        while True:
            idx = p.find(n, idx)
            if idx < 0:
                break
            before_ok = idx == 0 or p[idx - 1] == "/"
            after_idx = idx + len(n)
            after_ok = after_idx >= len(p) or p[after_idx] in "/?"
            if before_ok and after_ok:
                return True
            idx += 1
    return False


def _is_chatgpt_style_path(path: str) -> bool:
    """ChatGPT/OpenAI-style API paths — hostname not required."""
    p = (path or "").lower().split("?", 1)[0]
    if "prepare" in p or "autocomplet" in p or "implicit" in p:
        return False
    return (
        "/conversation" in p
        or "/messages" in p
        or "/chat/completions" in p
        or "/backend-api/" in p
        or "/backend-anon/" in p
    )


def _path_has_chat_marker(path: str) -> bool:
    """True when path matches a generic chat-submit marker (any monitored domain)."""
    p = (path or "").lower().split("?", 1)[0]
    if not p:
        return False
    for marker in CHAT_PATH_MARKERS:
        if marker.lower() in p:
            return True
    return False


def _looks_like_chatgpt_body(text: str, body_bytes: bytes = b"") -> bool:
    """ChatGPT/OpenAI conversation JSON or protobuf — detected from body, not hostname."""
    t = (text or "").strip()
    if t:
        if '"conversation_id"' in t or '"parent_message_id"' in t:
            return True
        if '"messages"' in t and any(x in t for x in ('"author"', '"content_type"', '"parts"')):
            return True
    data = body_bytes or b""
    if len(data) >= 8 and data[0] < 32 and data[0] not in (10, 13):
        return True
    return False


def is_chat_path(path: str, host: str = "", body: str = "") -> bool:
    """True when URL path/body looks like a chat/prompt submit on an admin-monitored domain.

    No product hostname lists — only path markers and request body shape.
    Caller must already have verified the host via detect_target().
    """
    p = (path or "").lower().split("?", 1)[0]
    body = body or ""
    if _path_has_ignore_pattern(p):
        return False
    if p and NOISE_EXTENSIONS.search(p):
        return False
    if "prepare" in p or "autocomplet" in p or "implicit" in p:
        return False

    if is_gemini_chat_submit(p, body) or "f.req=" in body[:500]:
        return True
    if is_copilot_chat_submit(p, body):
        return True
    if is_perplexity_chat_submit(p, body):
        return True
    if _is_chatgpt_style_path(p) or _looks_like_chatgpt_body(body):
        return True
    if _path_has_chat_marker(p):
        return True

    # Custom / unknown AI site: structured user send payload only — not every POST.
    if body.strip() and body.lstrip().startswith("{"):
        try:
            data = json.loads(body)
            if _body_has_user_send_payload(data):
                return True
        except Exception:
            pass
    return False


def is_gemini_chat_submit(path: str, body: str = "") -> bool:
    """True only for the HTTP call that carries the user's typed Gemini prompt.

    StreamGenerate / GenerateContent / BardFrontendService / BardChatUi batchexecute.
    Plain telemetry batchexecute without a prompt-shaped payload is rejected.
    """
    path_l = (path or "").lower()
    compact = path_l.replace("_", "")
    if "streamgenerate" in compact or "generatecontent" in compact:
        return True
    if "bardfrontendservice" in path_l:
        return True
    # clients6.google.com /_/BardChatUi/data/batchexecute (RPC ids rotate often)
    if "bardchatu" in compact or "bardchatui" in path_l:
        if "batchexecute" in path_l or "streamgenerate" in compact:
            return True
    if "batchexecute" in path_l and body:
        if any(rpc in body for rpc in GEMINI_CHAT_RPCS) or "StreamGenerate" in body:
            return True
        # Typed prompt slot: [["user text",0, ...
        if re.search(r'\[\s*\[\s*"(?:[^"\\]|\\.)+?"\s*,\s*0\s*,', body):
            return True
        if re.search(r'\\"(?:[^"\\]|\\.)+?\\"\s*,\s*0\s*,', body):
            return True
    return False


def _is_google_wire_blob(text: str) -> bool:
    """True for Gemini/Bard encoded tokens — not normal user-typed text."""
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith("gAAAA") or '"p":"gAAAA' in t:
        return True
    # CAMShQ8... / CAES... protobuf-ish conversation blobs
    if re.match(r"^CA[A-Z][A-Za-z0-9_-]{10,}", t):
        return True
    if " " in t or "\n" in t:
        return False
    # Opaque tokens with punctuation (session ids), not Hello123 / passwords
    if re.search(r"[)(\]\[{}|;]", t) and len(t) >= 8:
        return True
    # Long mixed-case alnum session ids only (keep short typed tokens like Hello123)
    if len(t) >= 16 and re.fullmatch(r"[A-Za-z0-9_-]+", t):
        has_u = any(c.isupper() for c in t)
        has_l = any(c.islower() for c in t)
        has_d = any(c.isdigit() for c in t)
        if has_u and has_l and has_d:
            return True
    if len(t) >= 24 and re.fullmatch(r"[A-Za-z0-9_\-+/=]+", t):
        if any(c.isupper() for c in t) and any(c.islower() for c in t):
            if "/" in t or "+" in t or "-" in t or "_" in t or t.endswith("="):
                return True
    return False


def _is_digit_heavy_user_text(text: str) -> bool:
    """Mostly digits (OTP / ID / number+light separators) — always treat as user prompt."""
    t = (text or "").strip()
    if not t:
        return False
    digits = sum(1 for c in t if c.isdigit())
    if digits < 1:
        return False
    return digits / len(t) >= 0.55


def _is_typed_numeric_prompt(text: str) -> bool:
    """User-typed digits / numeric IDs — keep as prompts (do not classify as opaque wire)."""
    t = (text or "").strip()
    if not t:
        return False
    if t.isdigit():
        return True
    if _is_digit_heavy_user_text(t):
        return True
    # Formatted numbers: +91 98765-43210, (555) 123-4567, 12-=-34
    if re.fullmatch(r"[\d\s\-+().=/]{3,200}", t):
        digits = sum(1 for c in t if c.isdigit())
        return digits >= 3
    return False


def _is_clear_protocol_junk(text: str) -> bool:
    """True only for multipart / challenge / IDE binary — not normal typed chat."""
    t = (text or "").strip()
    if not t:
        return True
    low_head = t[:80].lower()
    if (
        "webkitformboundary" in low_head
        or t.startswith("------")
        or "content-disposition: form-data" in t[:500].lower()
        or "multipart/form-data" in t[:200].lower()
    ):
        return True
    if t.startswith("gAAAA") or '"p":"gAAAA' in t:
        return True
    if _is_ai_chrome_url(t):
        return True
    if _looks_like_filename_only(t):
        return True
    # Real binary/IDE soup — but never reject digit-heavy user strings.
    if _is_digit_heavy_user_text(t) or _is_typed_numeric_prompt(t):
        return False
    if _looks_like_binary_or_wire_garbage(t):
        return True
    return False


def _is_opaque_wire_blob(text: str) -> bool:
    """Encoded wire/session tokens (Copilot/Bing base64url, Gemini blobs) — not typed chat."""
    t = (text or "").strip()
    if _is_typed_numeric_prompt(t) or _is_digit_heavy_user_text(t):
        return False
    if _is_google_wire_blob(text):
        return True
    if not t or len(t) < 8:
        return False
    # Single-token opaque blobs (no whitespace)
    if " " not in t and "\n" not in t and len(t) >= 20:
        if re.fullmatch(r"[A-Za-z0-9_\-+/=]+", t):
            # Mostly-digit IDs / number+separator prompts are user text.
            if t.isdigit() or sum(1 for c in t if c.isdigit()) >= int(len(t) * 0.55):
                return False
            if "/" in t or "+" in t or t.endswith("="):
                return True
            if len(t) >= 32 and not re.search(r"[aeiouAEIOU]{2}", t):
                return True
    return _looks_like_binary_or_wire_garbage(t)


def _looks_like_binary_or_wire_garbage(text: str) -> bool:
    """Reject Cursor/IDE/binary decode soup that is not a real user-typed prompt.

    Examples that must NOT enter Prompt Logs:
      Rp];$u\\OVoT]xy 9+)*wlTP-
      X*L$( rF2D:TvJxf<
      Cursor.exe*@c8df43df32fdc3daf238c2dba17c9acbfa6a6066…
      (Intel(R) Core(TM) i7-8850H CPU @ 2.60GHz
    """
    t = (text or "").strip()
    if not t:
        return True
    low = t.lower()

    # Cursor / IDE exe attestation + content hashes (not typed chat)
    if "cursor.exe" in low or re.search(r"(?i)\b[\w.-]+\.exe\*@", t):
        return True
    if ".exe" in low and "@" in t and re.search(r"@[a-f0-9]{24,}", t, re.I):
        return True
    # Hardware / agent telemetry fragments
    if "intel(r)" in low or "core(tm)" in low:
        return True
    if "cpu @" in low and "ghz" in low:
        return True
    if re.search(r"(?i)\b(?:amd|intel|qualcomm|apple)\b.+\b(?:cpu|gpu|mhz|ghz)\b", t) and len(t) < 120:
        return True
    # Long *@hex blobs (even without .exe)
    if "*" in t and "@" in t and len(t) >= 40:
        hexish = sum(1 for c in t if c in "0123456789abcdefABCDEF")
        if hexish / len(t) >= 0.5:
            return True

    # Control characters (except tab / LF / CR)
    if any(ord(c) < 9 or (10 < ord(c) < 32 and ord(c) != 13) or ord(c) == 127 for c in t):
        return True
    # Dense high-bit / mojibake on short strings
    if len(t) < 100:
        high = sum(1 for c in t if ord(c) > 127)
        if high / len(t) >= 0.12:
            return True

    alnum = sum(1 for c in t if c.isalnum())
    space = sum(1 for c in t if c.isspace())
    other = len(t) - alnum - space
    specials = {c for c in t if not c.isalnum() and not c.isspace()}

    # Short / medium strings with symbol soup (IDE wire frames, encrypted chunks)
    if len(t) <= 96:
        if other >= 4 and len(specials) >= 4 and other / len(t) >= 0.28:
            return True
        if other / len(t) >= 0.42 and other >= 3:
            return True
        letters = sum(1 for c in t if c.isalpha())
        vowels = sum(1 for c in t.lower() if c in "aeiou")
        if letters >= 4 and other >= 5 and vowels <= 1:
            return True
        # Very few alnum relative to punctuation
        if alnum > 0 and other >= alnum and len(specials) >= 5:
            return True

    # Backslash + brackets + dollar heavy fragments (common binary-as-text)
    if len(t) <= 80:
        weird = sum(t.count(ch) for ch in "\\]$^*`~|{};<>")
        if weird >= 3 and other / max(len(t), 1) >= 0.25:
            return True
    return False


def _is_ide_non_chat_noise(text: str, platform: str = "", domain: str = "") -> bool:
    """Cursor/IDE host noise that must never be evaluated or logged as a prompt."""
    if _looks_like_binary_or_wire_garbage(text):
        return True
    t = (text or "").strip()
    plat = (platform or "").lower()
    dom = (domain or "").lower()
    ide = "cursor" in plat or "cursor." in dom or dom.endswith("cursor.sh") or dom.endswith("cursor.com") or dom.endswith("cursor.so")
    if not ide:
        return False
    # Single-character / tiny fragments from IDE wire — not a real chat Send
    if len(t) <= 2 and " " not in t:
        return True
    return False


def _looks_like_document_body_dump(text: str) -> bool:
    """True when extracted chat text is likely full file/resume content, not a user caption."""
    t = (text or "").strip()
    if not t:
        return False
    if len(t) >= 500:
        return True
    if t.count("\n") >= 4:
        return True
    low = t.lower()
    # PDF / doc dumps often embed credentials or multiple emails — not a user caption.
    if re.search(r"password\s*[:=]", low) and re.search(r"@\S+\.\S+", t):
        return True
    if t.count("@") >= 2 and len(t) >= 60:
        return True
    resume_markers = (
        "account details", "work experience", "education", "curriculum vitae",
        "objective", "professional summary", "skills", "certification",
        "report information", "account number", "category policy",
    )
    hits = sum(1 for m in resume_markers if m in low)
    return hits >= 2 or (hits >= 1 and len(t) >= 180)


_NON_USER_CONTENT_PART_TYPES = frozenset({
    "document", "image", "file", "input_image", "input_file",
    "audio", "input_audio", "voice", "tool_result", "tool_use", "image_url",
})


def _is_file_content_part(part: dict) -> bool:
    """True for Claude/ChatGPT multimodal blocks that carry file bytes or extracted doc text."""
    if not isinstance(part, dict):
        return False
    ptype = str(part.get("type") or "").lower()
    if ptype in _NON_USER_CONTENT_PART_TYPES:
        return True
    ct = str(part.get("content_type") or "").lower()
    if ct in ("file", "image", "audio", "video", "document"):
        return True
    if part.get("extracted_content"):
        return True
    if part.get("file_id") or part.get("asset_pointer"):
        return True
    src = part.get("source")
    if isinstance(src, dict) and str(src.get("type") or "").lower() in ("base64", "url", "file", "content"):
        if ptype in ("document", "image", "file", "") or src.get("media_type"):
            return True
    return False


def is_copilot_chat_submit(path: str, body: str = "") -> bool:
    """True only for Copilot/Bing/Edge chat submit — not telemetry or sync frames."""
    path_l = (path or "").lower().split("?", 1)[0]
    body_l = (body or "").lower()
    if not path_l:
        if not body_l:
            return False
        return (
            '"event":"send"' in body_l
            or '"event": "send"' in body_l
            or '"target":"chat"' in body_l
            or '"target": "chat"' in body_l
            or (('"type":4' in body_l or '"type": 4' in body_l) and "chat" in body_l)
        )
    markers = (
        "chathub", "sydney", "chatoverstream", "getresponse", "/c/api/",
        "copilot", "turing/conversation", "createconversation", "/api/copilot",
        "edgesvc", "edgechat",
    )
    if any(m in path_l for m in markers):
        return True
    if "/chat" in path_l and "telemetry" not in path_l and "analytics" not in path_l:
        return True
    if body_l and (
        '"event":"send"' in body_l
        or '"event": "send"' in body_l
        or '"target":"chat"' in body_l
        or '"target": "chat"' in body_l
    ):
        return True
    return False


def is_perplexity_chat_submit(path: str, body: str = "") -> bool:
    """True only for Perplexity chat submit — not feed, auth, or telemetry."""
    path_l = (path or "").lower().split("?", 1)[0]
    if any(
        marker in path_l
        for marker in (
            "perplexity_ask", "/rest/sse", "/rest/thread", "/rest/entrypoint",
            "/rest/search", "/rest/chat", "/api/chat", "/search",
            "/socket", "/graphql", "/generative", "/completion", "/ask",
            "/query", "/copilot", "/server-sent-events",
        )
    ):
        return True
    if path_l.endswith("/chat") or "/api/chat" in path_l:
        return True
    body_l = (body or "").lower()
    if body_l and any(k in body_l for k in ('"query_str"', '"query"', '"user_query"', '"last_query"')):
        if not any(x in body_l for x in ('"event":"ping"', '"type":"ping"', '"heartbeat"')):
            return True
    if body and body.lstrip().startswith("{"):
        try:
            data = json.loads(body)
        except Exception:
            data = None
        if isinstance(data, dict):
            if isinstance(data.get("query_str"), str) and data["query_str"].strip():
                return True
            params = data.get("params")
            if isinstance(params, dict):
                for key in ("query_str", "dsl_query", "query"):
                    val = params.get(key)
                    if isinstance(val, str) and val.strip():
                        return True
    return False
