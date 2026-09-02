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

# Cache refresh interval in seconds (targets / rules / controls)
CACHE_TTL = 1

# Default fallback domains if backend is temporarily unreachable
# Default fallback is EMPTY — only admin-added Target Websites are monitored.
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

# Upload payload field indicators
UPLOAD_PAYLOAD_KEYS = [
    '"file_name"', '"file_id"', '"file_size"', '"filename"', '"fileName"',
    '"mime_type"', '"mimeType"', '"asset_pointer"', '"attachment"',
    '"fileData"', '"inline_data"', '"inlineData"',
    "application/vnd.openxmlformats", "application/msword",
    "application/pdf", ".docx", ".xlsx", ".pptx",
]

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
DEDUPE_TTL = 0.5
# Longer window for upload/download blocks (ChatGPT fires many file API calls)
BLOCK_DEDUPE_TTL = 30

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
_domains_fetched_at: float = 0
_rules_fetched_at: float = 0
_recent_prompts: dict = {}  # key -> timestamp
_composer_draft: dict = {}  # domain -> (prompt, timestamp) while user is still typing
_cached_controls: dict = {
    "enabled": False,
    "block_upload": False,
    "upload_warning": "",
}
_controls_fetched_at: float = 0
_controls_from_backend = False

# File bytes cached at upload-time; Prompt Log + allow/block happen only on chat Send.
_UPLOAD_FILE_CACHE: dict[str, dict] = {}
_UPLOAD_FILE_QUEUES: dict[str, list[dict]] = {}
_UPLOAD_FILE_CACHE_LOCK = threading.Lock()
_UPLOAD_FILE_CACHE_TTL = 15 * 60  # 15 minutes — keep bytes for View/Download
_UPLOAD_FILE_CACHE_MAX = 40
_UPLOAD_FILE_QUEUE_MAX = 12  # multiple files per chat Send → one log row each
# Only treat "latest upload" as this Send's file if the upload was this recent.
# Prevents typed prompts from becoming "[FILE UPLOAD] attachment" after an old pick.
_UPLOAD_LATEST_MATCH_TTL = 5 * 60  # 5 min — upload then Send without matching id still binds


def _fetch_json(url: str) -> dict | None:
    """Generic GET JSON fetch from backend."""
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                raw = resp.read().decode("utf-8")
                if raw.lstrip().lower().startswith("<!doctype") or raw.lstrip().lower().startswith("<html"):
                    return None
                return json.loads(raw)
    except Exception:
        pass
    return None


def _normalize_domain(raw: str) -> str:
    """Normalize backend domain values like 'https://chatgpt.com/' -> 'chatgpt.com'."""
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


def get_target_domains() -> dict:
    """
    Fetch target domains from UnifAI backend every CACHE_TTL seconds.
    Returns dict of {domain: platform_name} for PAC/monitor routing
    (monitored OR block_site). Also refreshes _cached_blocked for full-site lock
    and _cached_families for upload-cache sharing across admin-added related hosts.
    """
    global _cached_domains, _cached_blocked, _cached_roles, _cached_families, _domains_fetched_at
    now = time.time()
    if now - _domains_fetched_at < CACHE_TTL:
        return _cached_domains

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets")
    if data is not None:
        targets = data.get("targets", [])
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
        _cached_domains = new_map
        _cached_blocked = new_blocked
        _cached_roles = new_roles
        _cached_families = _build_target_families(targets)
        _domains_fetched_at = now
        print(
            f"[UnifAI Proxy] Refreshed {len(new_map)} target domains "
            f"({len(new_blocked)} full-site locks, {len(_cached_families)} upload families) from backend."
        )

    return _cached_domains


def detect_site_block(host: str) -> tuple[bool, str, str]:
    """Return (blocked, domain, platform) when admin enabled Block entire website."""
    get_target_domains()  # refresh caches
    host_lower = (host or "").lower().strip(".")
    for domain, platform in _cached_blocked.items():
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


def get_guard_rules() -> list:
    """
    Fetch active DLP guard rules from UnifAI backend every CACHE_TTL seconds.
    Returns only admin-created rules. Empty list means nothing is matched.
    Never falls back to hardcoded patterns.
    """
    global _cached_rules, _cached_rule_catalog, _cached_has_ai_bot, _rules_fetched_at
    now = time.time()
    if now - _rules_fetched_at < CACHE_TTL:
        return _cached_rules

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/rules")
    if data is not None:
        rules = data.get("rules", [])
        compiled = []
        catalog: dict[str, dict] = {}
        has_ai_bot = False
        for r in rules:
            if not r.get("active", False):
                continue
            name = (r.get("name") or "").strip()
            rule_type = str(r.get("rule_type") or "").strip().lower()
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
                    "regex": re.compile(pattern, re.IGNORECASE),
                    "action": action,
                    "severity": r.get("severity", "HIGH"),
                    "warning_message": (r.get("warning_message") or "").strip(),
                })
            except re.error:
                pass
        _cached_rules = compiled
        _cached_rule_catalog = catalog
        _cached_has_ai_bot = has_ai_bot
        _rules_fetched_at = now
        print(f"[UnifAI Proxy] Refreshed {len(compiled)} regex rules, {len(catalog)} active rules from backend.")
        return _cached_rules

    # Backend unreachable: keep last cache (may be empty). Do not invent rules.
    return _cached_rules


def has_ai_bot_rules() -> bool:
    get_guard_rules()
    return bool(_cached_has_ai_bot)


def evaluate_prompt(platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str) -> tuple[bool, str, str, str, str]:
    """Regex (local) + AI Guard Bot (backend) — both run when bot rules exist; strictest action wins."""
    local = decide_prompt_locally(prompt)
    if has_ai_bot_rules():
        backend = send_to_backend(platform, domain, prompt, client_ip, url, method)
        return _merge_guard_decisions(local, backend)

    allowed, rule_triggered, action, redacted_prompt, reply_text = local
    if action == "Blocked" or not allowed:
        def _log_local_block() -> None:
            try:
                payload = json.dumps({
                    "platform": platform,
                    "prompt": prompt,
                    "client_ip": client_ip,
                    "agent_id": UNIFAI_AGENT_ID,
                    "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                    "metadata": {
                        "domain": domain,
                        "url": url,
                        "method": method,
                        "is_blocked": True,
                        "blocked_reason": rule_triggered or "Guard Rule",
                        "agent_id": UNIFAI_AGENT_ID,
                        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
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
        return False, rule_triggered, action or "Blocked", redacted_prompt, reply_text

    if action in ("Redacted", "Warned"):
        log_prompt_async(platform, domain, prompt, client_ip, url, method)
        return allowed, rule_triggered, action, redacted_prompt, reply_text

    log_prompt_async(platform, domain, prompt, client_ip, url, method)
    return True, "", "Allowed", prompt, ""


def _fail_open() -> bool:
    return os.getenv("UNIFAI_FAIL_OPEN", "").strip() in ("1", "true", "TRUE", "yes", "YES")


def get_control_settings() -> dict:
    """Fetch browser interaction controls from backend every CACHE_TTL seconds."""
    global _cached_controls, _controls_fetched_at, _controls_from_backend
    now = time.time()
    if now - _controls_fetched_at < CACHE_TTL and _cached_controls:
        return _cached_controls

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/controls")
    if data and isinstance(data.get("controls"), dict):
        c = data["controls"]
        _cached_controls = {
            "enabled": bool(c.get("enabled", False)),
            "block_upload": bool(c.get("block_upload", False)),
            "upload_warning": (c.get("upload_warning") or "").strip(),
        }
        _controls_fetched_at = now
        _controls_from_backend = True
        print(
            "[UnifAI Proxy] Controls refreshed | "
            f"enabled={_cached_controls['enabled']} "
            f"upload={_cached_controls['block_upload']}"
        )
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

def looks_like_secret_token(text: str) -> bool:
    t = (text or "").strip()
    return bool(re.match(r"^(sk-|sk-ant-|sk-proj-|sk-admin-|ghp_|gho_|github_pat_|AKIA|AIzaSy|pcsk_)", t, re.I))


def is_phone_like_rule(name: str, pattern: str = "") -> bool:
    n = (name or "").lower()
    p = (pattern or "").lower()
    if any(x in n for x in ("phone", "mobile", "cell")):
        return True
    return any(x in p for x in (r"\d{8", r"\d{9", r"\d{10", r"\d{11", "[0-9]{10"))


def rule_matches_prompt(rule: dict, prompt: str) -> bool:
    regex = rule.get("regex")
    if regex is None or not prompt:
        return False
    m = regex.search(prompt)
    if not m:
        return False
    if is_phone_like_rule(rule.get("name", ""), rule.get("pattern", "")) and looks_like_secret_token(prompt):
        return False
    if m.start() >= 3 and prompt[m.start() - 3 : m.start()].lower() == "sk-":
        return False
    return True


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


def _warned_forward(prompt: str, warning_message: str = "") -> str:
    return _redacted_forward(prompt, warning_message)


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
) -> dict:
    """Proxy scan decision for backend log — avoids duplicate guard evaluation."""
    has_content = bool((scanned or "").strip() or upload_images)
    if not has_content:
        return {}
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
    rules = sorted(
        get_guard_rules(),
        key=lambda r: 1 if is_phone_like_rule(r.get("name", ""), r.get("pattern", "")) else 0,
    )
    for r in rules:
        if not rule_matches_prompt(r, prompt):
            continue
        rule_action = (r.get("action") or "BLOCK").upper()
        if rule_action == "WARN":
            rule_action = "REDACT"
        if rule_action == "BLOCK":
            return False, r["name"], "Blocked", prompt, _security_reply_text(r["name"], r.get("warning_message", ""))
        if rule_action == "REDACT":
            return True, r["name"], "Redacted", _redacted_forward(prompt, r.get("warning_message", "")), ""
    if looks_like_secret_token(prompt):
        for r in rules:
            n = (r.get("name") or "").lower()
            if any(x in n for x in ("phone", "mobile")):
                continue
            if any(x in n for x in ("api", "key", "secret", "token", "openai")):
                return False, r["name"], "Blocked", prompt, _security_reply_text(r["name"], r.get("warning_message", ""))
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
        # Allow a.claude.ai? Actually a.claude.ai was challenge - keep blocked
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


def _is_opaque_wire_blob(text: str) -> bool:
    """Encoded wire/session tokens (Copilot/Bing base64url, Gemini blobs) — not typed chat."""
    if _is_google_wire_blob(text):
        return True
    t = (text or "").strip()
    if not t or " " in t or "\n" in t or len(t) < 20:
        return False
    # Copilot / Sydney / Edge often ship conversation tokens as base64url (with / + =).
    if re.fullmatch(r"[A-Za-z0-9_\-+/=]+", t):
        if "/" in t or "+" in t or t.endswith("="):
            return True
        if len(t) >= 32 and not re.search(r"[aeiouAEIOU]{2}", t):
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


def _is_claude_api_shape(path: str, body: str) -> bool:
    """Detect Claude / Anthropic chat submit from request path or JSON body — not hostname."""
    path_l = (path or "").lower()
    if any(x in path_l for x in ("/v1/messages", "chat_conversations", "append_message", "/completion")):
        return True
    if not body or not body.lstrip().startswith("{"):
        return False
    try:
        data = json.loads(body)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    if "max_tokens" in data and isinstance(data.get("messages"), list):
        return True
    if isinstance(data.get("prompt"), str) and str(data.get("prompt", "")).strip():
        return True
    return False


def is_copilot_noise_content(content: str) -> bool:
    """Copilot SignalR / Sydney frames that are not a user chat submit."""
    if not content:
        return True
    cl = content.lower()
    if '"target":"metrics"' in cl or '"target": "metrics"' in cl:
        return True
    if '"type":6' in cl or '"type": 6' in cl:
        return True
    if '"event":"typing"' in cl or '"event": "typing"' in cl:
        return True
    if '"event":"ping"' in cl or '"event": "ping"' in cl:
        return True
    if "messagetype\":\"internal" in cl or "messagetype\": \"internal" in cl:
        return True
    if '"event":"send"' not in cl and '"event": "send"' not in cl:
        if '"target":"chat"' not in cl and '"target": "chat"' not in cl:
            if ('"type":4' not in cl and '"type": 4' not in cl) or "chat" not in cl:
                if len(content) > 40 and _is_opaque_wire_blob(content.strip()):
                    return True
    return False


def _parse_signalr_frames(text: str) -> list:
    """Split SignalR JSON frames (0x1e record separator)."""
    out = []
    for part in re.split(r"\x1e", text or ""):
        part = part.strip()
        if not part or part[0] not in "{[":
            continue
        try:
            out.append(json.loads(part))
        except Exception:
            continue
    return out


def extract_copilot_prompt(content: str) -> str:
    """Extract user-typed text from Copilot / Bing Sydney / Edge / M365 SignalR payloads."""

    def _pick_text(val: str) -> str:
        if not val or not isinstance(val, str):
            return ""
        got = val.strip()
        if not got or _is_opaque_wire_blob(got):
            return ""
        if looks_like_user_prompt(got):
            return got
        return ""

    def _from_message_dict(msg: dict) -> str:
        if not isinstance(msg, dict):
            return ""
        author = str(msg.get("author") or msg.get("role") or "").lower()
        if author and author not in ("user", "human", "customer", "client", "sender"):
            return ""
        for key in ("text", "hiddenText", "rawText", "input", "query", "prompt", "utterance"):
            got = _pick_text(msg.get(key) or "")
            if got:
                return got
        return ""

    def _from_obj(obj) -> str:
        if isinstance(obj, str):
            return _pick_text(obj)
        if not isinstance(obj, dict):
            return ""

        # SignalR StreamInvocation: type 4, target chat
        if obj.get("type") == 4 and str(obj.get("target", "")).lower() == "chat":
            for arg in obj.get("arguments") or []:
                if not isinstance(arg, dict):
                    continue
                got = _from_message_dict(arg.get("message") or {})
                if got:
                    return got
                for key in ("text", "query", "prompt", "rawUserQuery", "utterance", "userMessage"):
                    got = _pick_text(arg.get(key) or "")
                    if got:
                        return got

        event = str(obj.get("event", "")).lower()
        if event in ("send", "message", "chat"):
            got = _from_message_dict(obj.get("message") or {})
            if got:
                return got
            for key in ("text", "query", "prompt", "rawUserQuery", "utterance", "userMessage"):
                got = _pick_text(obj.get(key) or "")
                if got:
                    return got
            return ""

        got = _from_message_dict(obj.get("message") or {})
        if got:
            return got
        for key in ("text", "query", "prompt", "rawUserQuery", "utterance", "userMessage", "input"):
            got = _pick_text(obj.get(key) or "")
            if got:
                return got
        for nest in ("arguments", "params", "payload", "data", "body", "request"):
            nested = obj.get(nest)
            if isinstance(nested, list):
                for item in nested:
                    got = _from_obj(item)
                    if got:
                        return got
            elif isinstance(nested, dict):
                got = _from_obj(nested)
                if got:
                    return got
        return ""

    if not content:
        return ""

    if "\x1e" in content:
        for frame in reversed(_parse_signalr_frames(content)):
            got = _from_obj(frame)
            if got:
                return got

    try:
        data = json.loads(content)
        got = _from_obj(data)
        if got:
            return got
    except Exception:
        pass

    for line in (content or "").splitlines():
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            got = _from_obj(json.loads(line))
            if got:
                return got
        except Exception:
            continue
    return ""


def _is_ai_chrome_url(text: str) -> bool:
    """True when the string is a Gemini/Bard/ChatGPT page URL, not typed chat."""
    t = (text or "").strip()
    if not re.match(r"^https?://", t, re.I):
        return False
    try:
        u = urllib.parse.urlparse(t)
    except Exception:
        return False
    host = (u.hostname or "").lower()
    path = (u.path or "").lower()
    query = (u.query or "").lower()
    # Page/navigation URLs on an admin-monitored host — not typed chat text.
    if detect_target(host)[0] and (path in ("", "/", "/app") or "hl=" in query):
        return True
    return False


_FILE_EXTENSION_RE = re.compile(
    r"\.(?:pdf|docx?|xlsx?|pptx?|csv|txt|png|jpe?g|gif|webp|zip|rar|7z|"
    r"mp3|mp4|wav|m4a|mov|avi|json|xml|html?|md|rtf|odt|ods|ppt)(?:\s|$)",
    re.IGNORECASE,
)


def _looks_like_filename_only(text: str) -> bool:
    """True when extracted text is only an attachment filename — not user chat."""
    t = (text or "").strip()
    if not t or " " in t or "\n" in t or len(t) > 240:
        return False
    if not re.search(r"\.[a-z0-9]{2,8}$", t, re.IGNORECASE):
        return False
    if _FILE_EXTENSION_RE.search(t):
        return True
    return bool(re.fullmatch(r"[\w\-.]+\.[a-z0-9]{2,8}", t, re.IGNORECASE))


def _send_carries_attachment(raw_text: str) -> bool:
    """True when this chat Send references an uploaded/attached file."""
    return bool(
        chat_carries_attachment(raw_text)
        or chatgpt_carries_file(raw_text)
        or bool(extract_attachment_filename_from_send(raw_text))
    )


def looks_like_user_prompt(text: str) -> bool:
    """
    Save any user-typed prompt: any language, numbers, symbols, code, one word or long text.
    Do not save protocol junk (Gemini request ids, RPC tokens, f.req blobs).
    """
    if not text or not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 1:
        return False
    # Never treat multipart / raw HTTP file bodies as chat prompts
    low_head = t[:80].lower()
    if (
        "webkitformboundary" in low_head
        or t.startswith("------")
        or "content-disposition: form-data" in t[:500].lower()
        or "multipart/form-data" in t[:200].lower()
    ):
        return False
    if _is_ai_chrome_url(t):
        return False
    if _is_opaque_wire_blob(t):
        return False
    if _is_internal_wire_text(t):
        return False
    if t.startswith("gAAAA") or '"p":"gAAAA' in t:
        return False
    if t.startswith("[FILE UPLOAD") or t.startswith("[FILE DOWNLOAD") or t.startswith("[FILE CONTENT") or t.startswith("[SITE BLOCKED"):
        return True
    if _looks_like_filename_only(t):
        return False
    if len(t) == 1 and t in "/.\\|#@":
        return False

    # Reject raw urlencoded wire parameters or batch execute bodies
    if any(wire in t for wire in ("count=", "&ofs=", "req0___data__", "f.req=", "soc-app=", "soc-platform=", "___data__=")):
        return False

    low = t.lower()
    if low in GEMINI_LOCALE_JUNK or re.fullmatch(r"[a-z]{2}-[a-z]{2,3}", low):
        return False
    if low in {
        "null", "undefined", "generic", "batchexecute", "wrb.fr",
        "bard activity enabled", "activity enabled", "streamgenerate",
        "co.in", "com.au", "co.uk", "com.br", "co.jp", "co.kr",
    }:
        return False
    if "bard activity" in low and len(t) < 30:
        return False
    # Domain / public-suffix crumbs that Gemini embeds in wire payloads (not typed chat)
    if re.fullmatch(r"[a-z0-9]{1,8}\.(?:co\.)?[a-z]{2,3}", low):
        return False

    # Filter tokens and RPC IDs when text has no spaces.
    # Digit-only text is a valid user prompt (phone, IDs, math). Do not drop it.
    if " " not in t:
        # Gemini session / client tokens: _05Zravx, _a1B2c3d4
        if re.fullmatch(r"_[0-9A-Za-z]{4,24}", t):
            return False
        if t.startswith("_") and 5 <= len(t) <= 32 and re.fullmatch(r"[0-9A-Za-z_]+", t):
            return False
        # Google conversation/response tokens: r_653a..., c_44a8..., v_7f45..., rc_...
        if re.fullmatch(r"[rcv][_\.][0-9a-fA-F]{6,}", t, re.IGNORECASE):
            return False
        # Hex hashes that contain a-f (not digit-only numbers the user typed)
        if len(t) >= 12 and re.fullmatch(r"[0-9a-fA-F]{12,64}", t) and re.search(r"[a-fA-F]", t):
            return False
        # Google batchexecute RPC IDs (4-8 mixed case alphanumeric, e.g. ESY5D, L5adhe, VxUbXb, qpEbW, aPya6c)
        if 4 <= len(t) <= 8 and re.fullmatch(r"[A-Za-z0-9]+", t):
            # Mixed-case RPC id e.g. ESY5D, VxUbXb — keep all-lower words (hi, hello, tamil…)
            if any(ch.isupper() for ch in t) and any(ch.islower() for ch in t):
                return False
            if sum(1 for ch in t if ch.isupper()) >= 2 and any(ch.isdigit() for ch in t):
                return False

    return True


# Extra product hosts are not auto-applied. Admin must add them in Target Websites.

def detect_target(host: str) -> tuple[bool, str, str]:
    """Check if host matches any monitored domain. Returns (is_target, domain, platform)."""
    domains_map = get_target_domains()
    host_lower = (host or "").lower().strip(".")
    best_domain = ""
    best_platform = ""
    best_len = -1
    for domain, platform in domains_map.items():
        if host_lower == domain or host_lower.endswith("." + domain):
            if len(domain) > best_len:
                best_len = len(domain)
                best_domain = domain
                best_platform = platform
    if best_domain:
        return True, best_domain, best_platform
    return False, "", ""


def resolve_host_role(host: str) -> str:
    """Admin-assigned role from dashboard (ui | chat | file | auto).

    Auto ("") inherits the nearest parent domain's explicit role so related hosts
    under e.g. perplexity.ai (chat) behave as chat without per-host labeling.
    """
    get_target_domains()
    host_lower = (host or "").lower().strip(".")
    best_role = ""
    best_len = -1
    matched_domain = ""
    for domain, role in _cached_roles.items():
        if host_lower == domain or host_lower.endswith("." + domain):
            if len(domain) > best_len:
                best_len = len(domain)
                best_role = role or ""
                matched_domain = domain
    if best_role in ("ui", "chat", "file"):
        return best_role
    # Inherit from registrable parent targets (www.perplexity.ai → perplexity.ai).
    if matched_domain:
        parts = matched_domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            pr = _cached_roles.get(parent, "")
            if pr in ("ui", "chat", "file"):
                return pr
    return ""


def _is_internal_wire_text(text: str) -> bool:
    """Internal RPC ids, pubsub actions, and wire fragments — not user-typed chat."""
    t = (text or "").strip()
    if not t:
        return True
    low = t.lower()
    if low in {
        "turn exchange complete", "fetch socket url", "ping", "pong",
        "heartbeat", "keepalive", "keep alive", "connection established",
        "stream complete", "message complete", "typing", "presence",
    }:
        return True
    # pubsub.fetch-socket-url, client.create, etc.
    if " " not in t and re.fullmatch(r"[a-z][a-z0-9_.-]*(?:\.[a-z][a-z0-9_.-]+)+", low):
        return True
    if " " not in t and re.fullmatch(r"[a-z]+(?:_[a-z0-9]+){2,}", low):
        return True
    # Short wire fragments: B-mvY..., J12'54M, U}2T), 7cZ.
    if len(t) <= 14 and " " not in t:
        special = sum(1 for c in t if not c.isalnum() and c not in "._-'")
        if special >= 1 and len(t) <= 10:
            return True
        if special >= 2:
            return True
        letters = sum(1 for c in t if c.isalpha())
        digits = sum(1 for c in t if c.isdigit())
        if letters and digits and special and len(t) <= 12:
            return True
    return False


def _body_has_user_send_payload(data) -> bool:
    """True when JSON body carries an explicit user message/query — not sync/telemetry."""
    if not isinstance(data, dict):
        return False
    event = str(data.get("event") or data.get("type") or "").lower()
    if event in ("ping", "pong", "typing", "presence", "heartbeat", "metrics", "internal"):
        return False
    if str(data.get("command") or "").lower() in ("ping", "pong", "metrics"):
        return False
    msgs = data.get("messages")
    if isinstance(msgs, list):
        for msg in reversed(msgs):
            if isinstance(msg, dict) and _extract_from_message_obj(msg):
                return True
    for key in (
        "query", "query_str", "prompt", "input", "message", "question",
        "user_input", "user_query", "rawUserQuery", "utterance",
    ):
        val = data.get(key)
        if isinstance(val, str) and val.strip() and looks_like_user_prompt(val.strip()):
            return True
    return False


def _is_clear_chat_submit(path: str, host: str, raw_text: str, raw_bytes: bytes = b"") -> bool:
    """Finished chat Send on an admin-monitored host — not typing/telemetry/CDN."""
    path_l = (path or "").lower().split("?", 1)[0]
    body = raw_text or ""
    if _path_has_ignore_pattern(path_l):
        return False
    if path_l and NOISE_EXTENSIONS.search(path_l):
        return False
    if "prepare" in path_l or "autocomplet" in path_l or "implicit_hint" in path_l:
        return False
    if is_unsubmitted_chat_body(path, body):
        return False
    if is_copilot_noise_content(body):
        return False
    if (
        is_perplexity_chat_submit(path, body)
        or is_gemini_chat_submit(path, body)
        or is_copilot_chat_submit(path, body)
        or _is_claude_api_shape(path, body)
    ):
        return True
    if _is_chatgpt_style_path(path_l) or _looks_like_chatgpt_body(body, raw_bytes):
        return True
    if _path_has_chat_marker(path_l):
        if is_noise(path, body):
            return False
        return True
    if body.lstrip().startswith("{"):
        try:
            data = json.loads(body)
            if _body_has_user_send_payload(data):
                return True
        except Exception:
            pass
    return False


def _is_confident_chat_send(path: str, raw_text: str, raw_bytes: bytes = b"") -> bool:
    """True when request is very likely a finished user Send (platform body shapes)."""
    if _is_clear_chat_submit(path, "", raw_text, raw_bytes):
        return True
    path_l = (path or "").lower()
    body = raw_text or ""
    if _looks_like_chatgpt_body(body, raw_bytes) and (
        _is_chatgpt_style_path(path_l) or _path_has_chat_marker(path_l)
    ):
        return True
    if is_perplexity_chat_submit(path, body):
        return True
    if _is_claude_api_shape(path, body):
        return True
    return False


_CHAT_METADATA_JUNK = frozenset({
    "user", "assistant", "system", "auto", "text", "message", "role", "content",
    "parts", "author", "metadata", "recipient", "client", "server", "ping", "pong",
    "null", "undefined", "true", "false", "default", "model", "parent", "child",
    "chatgpt", "gpt-4", "gpt-4o", "gpt-3.5", "o1", "o3", "thinking", "standard",
})


def _is_chat_metadata_token(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return True
    if t in _CHAT_METADATA_JUNK:
        return True
    if re.fullmatch(r"gpt[-\d\.]+[a-z]*", t):
        return True
    return False


def _pick_best_user_text(candidates: list[str]) -> str | None:
    """Choose the best user-typed string from protobuf/JSON fragments (any domain)."""
    best = None
    best_score = -1
    for s in reversed(candidates):
        if not s:
            continue
        got = _clean_prompt_text(s)
        if not got or not looks_like_user_prompt(got):
            continue
        if _is_opaque_wire_blob(got) or _is_internal_wire_text(got) or _is_chat_metadata_token(got):
            continue
        score = len(got)
        if " " in got:
            score += 24
        if got.isdigit():
            score += 16
        if 1 <= len(got) <= 4 and got.isalpha():
            score += 12
        if re.search(r"[a-zA-Z]", got) and re.search(r"\d", got):
            score += 4
        if score > best_score:
            best_score = score
            best = got
    return best


def _extract_chatgpt_parts_prompt(blob: str) -> str | None:
    """Last ChatGPT/OpenAI parts[] slot — the finished user Send text."""
    if not blob:
        return None
    last: str | None = None
    patterns = (
        r'"parts"\s*:\s*\[\s*"((?:[^"\\]|\\.)*)"',
        r'"content"\s*:\s*\{\s*"content_type"\s*:\s*"text"\s*,\s*"parts"\s*:\s*\[\s*"((?:[^"\\]|\\.)*)"',
        r'"input_text"\s*:\s*"((?:[^"\\]|\\.)*)"',
    )
    for pat in patterns:
        for m in re.finditer(pat, blob):
            raw = m.group(1)
            cand = _clean_prompt_text(
                raw.encode("utf-8").decode("unicode_escape", errors="ignore")
                if "\\" in raw
                else raw
            )
            if (
                cand
                and looks_like_user_prompt(cand)
                and not _is_opaque_wire_blob(cand)
                and not _is_internal_wire_text(cand)
                and not _is_chat_metadata_token(cand)
            ):
                last = cand
    return last


def _is_typing_or_draft_path(path: str, raw_text: str = "") -> bool:
    """Autocomplete / prepare / in-progress only — not a finished Send."""
    path_l = (path or "").lower()
    if path_l.endswith("/prepare") or "/prepare" in path_l:
        return True
    if "autocomplet" in path_l or "implicit_hint" in path_l:
        return True
    if "partial_query" in (raw_text or "") and '"query_str"' not in (raw_text or ""):
        return True
    return is_unsubmitted_chat_body(path, raw_text)


def _is_static_asset_request(path: str) -> bool:
    """Static CDN assets — never chat submits."""
    path_l = (path or "").lower().split("?", 1)[0]
    return bool(path_l and NOISE_EXTENSIONS.search(path_l))


def _should_intercept_extracted_prompt(
    prompt: str | None,
    path: str,
    raw_text: str,
    domain: str,
    host: str = "",
    raw_bytes: bytes = b"",
) -> bool:
    """Only finished chat Send with real user text — not telemetry/sync/internal RPC."""
    if not prompt or not isinstance(prompt, str):
        return False
    text = prompt.strip()
    if len(text) < 1:
        return False
    if not looks_like_user_prompt(text):
        return False
    if _is_opaque_wire_blob(text):
        return False
    if _is_internal_wire_text(text):
        return False
    if text.startswith("[FILE UPLOAD"):
        return False
    if _looks_like_filename_only(text):
        return False
    # File Send bodies embed PDF/doc text — only short user captions belong in Prompt Logs.
    if _send_carries_attachment(raw_text):
        if _looks_like_document_body_dump(text) or len(text) > 320:
            return False
    if _is_typing_or_draft_path(path, raw_text):
        return False
    if not _is_confident_chat_send(path, raw_text, raw_bytes):
        return False
    # Only skip ultra-fast single-keystroke drafts on prepare/autocomplete paths.
    path_l = (path or "").lower()
    if ("prepare" in path_l or "autocomplet" in path_l) and is_composer_typing_draft(domain, text):
        return False
    if is_duplicate_event(domain, text, ttl=DEDUPE_TTL, mark=False):
        return False
    return True


def _extract_interceptable_prompt(
    raw_bytes: bytes,
    content_type: str,
    host: str,
    url: str,
    path: str,
    raw_text: str,
    domain: str,
) -> str | None:
    """Domain-add-only: extract user text from any monitored-domain request body."""
    if _is_static_asset_request(path):
        return None
    prompt = extract_prompt_universal(raw_bytes, content_type, host=host, url=url)
    if _should_intercept_extracted_prompt(prompt, path, raw_text, domain, host=host, raw_bytes=raw_bytes):
        return prompt
    return None


def is_noise(path: str, content: str = "") -> bool:
    """Filter telemetry, analytics, static assets and background noise."""
    path_lower = path.lower().split("?", 1)[0]

    if NOISE_EXTENSIONS.search(path_lower):
        return True

    if _path_has_ignore_pattern(path_lower):
        return True

    # Partial typing / autocomplete — not a submitted prompt
    if path_lower.endswith("/prepare") or "/prepare" in path_lower or "partial_query" in (content or ""):
        return True
    if "autocomplet" in path_lower or "implicit_hint" in path_lower:
        return True

    if content:
        if content.startswith('{"counters":') or content.startswith('{"view":') or content.startswith('{"events":'):
            return True
        if '{"prepare_token":' in content or '"prepare_token"' in content:
            return True
        # ChatGPT encrypted sentinel / challenge blobs — not user text
        if '"p":"gAAAA' in content or content.strip().startswith('{"p":"gAAAA'):
            return True
        if '"requested_default_model"' in content and '"messages"' not in content:
            return True
        if 'AttributionReporting' in content or 'googletagmanager' in content:
            return True
        if 'columnNumber' in content and 'lineNumber' in content and 'sourceFile' in content:
            return True
        if 'com.google.android.gms' in content:
            return True
        if '"presence"' in content and '"messages"' not in content and '"parts"' not in content:
            return True
        if content.startswith('{"id":') and '"command":' in content and '"messages"' not in content:
            return True
        # Protobuf / binary chat submit — do not drop as noise when path/body looks like chat.
        path_l = (path or "").lower()
        chat_submit = (
            _is_chatgpt_style_path(path_l)
            or is_perplexity_chat_submit(path_l, content)
            or is_gemini_chat_submit(path_l, content)
            or is_copilot_chat_submit(path_l, content)
            or _path_has_chat_marker(path_l)
        )
        if (
            len(content) > 0
            and ord(content[0]) < 32
            and ord(content[0]) not in (10, 13)
            and not chat_submit
        ):
            return True
        # Gemini / form chat bodies are valid (f.req=...)
        cl = content.lstrip()
        if cl.startswith("f.req=") or "f.req=" in cl[:120]:
            return False
        # Copilot websocket send events
        if '"event":"send"' in content or '"event": "send"' in content:
            return False
        # Copilot SignalR / sync noise — not user prompts
        if is_copilot_noise_content(content):
            return True
        # Cloudflare challenge bodies (non-JSON)
        if not cl.startswith(("{", "[")) and not looks_like_user_prompt(content[:200]):
            if len(content) > 40 and content.count(" ") < 2 and not any(ch.isdigit() for ch in content):
                return True

    return False


def _clean_prompt_text(text: str) -> str | None:
    """Normalize extracted text; reject empty / challenge blobs."""
    if not text or not isinstance(text, str):
        return None
    cleaned = text.strip()
    if len(cleaned) < 1:
        return None
    if cleaned.startswith("gAAAA") or '"p":"gAAAA' in cleaned:
        return None
    if cleaned.lower() in ("null", "undefined"):
        return None
    if not looks_like_user_prompt(cleaned):
        return None
    return cleaned


def is_duplicate_event(domain: str, event_key: str, ttl: float = DEDUPE_TTL, *, mark: bool = True) -> bool:
    """Return True if the same event was already logged for this domain recently.

    mark=False only peeks (does not stamp) — use before a backend write, then
    call mark_duplicate_event after success so failed posts can retry.
    """
    now = time.time()
    expired = [k for k, ts in _recent_prompts.items() if now - ts > max(DEDUPE_TTL, BLOCK_DEDUPE_TTL)]
    for k in expired:
        _recent_prompts.pop(k, None)

    key = f"{domain}|{event_key.strip().lower()}"
    prev = _recent_prompts.get(key)
    if prev is not None and (now - prev) <= ttl:
        return True
    if mark:
        _recent_prompts[key] = now
    return False


def mark_duplicate_event(domain: str, event_key: str) -> None:
    """Stamp dedupe key after a successful backend log."""
    key = f"{domain}|{(event_key or '').strip().lower()}"
    _recent_prompts[key] = time.time()


def is_duplicate_prompt(domain: str, prompt: str) -> bool:
    """Return True if the same prompt was already logged for this domain recently."""
    return is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL)


def chatgpt_carries_file(raw_text: str) -> bool:
    """ChatGPT multimodal sends use content_type:file / file_id — not always attachments[]."""
    if not raw_text:
        return False
    low = raw_text.lower()
    if re.search(r'"content_type"\s*:\s*"file"', low):
        return True
    if "sediment://" in low or "file-service://" in low:
        return True
    if re.search(r'"file_id"\s*:\s*"file-[a-zA-Z0-9_-]+"', low):
        return True
    if re.search(r'"content_type"\s*:\s*"multimodal_text"', low):
        if re.search(
            r'"(?:file_id|asset_pointer|file-service://|sediment://|mime_type|file_name|filename)"',
            low,
        ):
            return True
        if re.search(
            r'"name"\s*:\s*"[^"]+\.(?:pdf|docx?|xlsx?|pptx?|png|jpe?g|gif|webp|csv|txt|zip)"',
            low,
        ):
            return True
    if re.search(
        r'"parts"\s*:\s*\[[\s\S]{0,4000}?"content_type"\s*:\s*"file"',
        low,
    ):
        return True
    return False


def detect_chatgpt_file_upload(
    host: str,
    path: str,
    method: str,
    content_type: str,
    body_len: int,
    raw: bytes,
) -> tuple[bool, str]:
    """Catch file uploads on admin-monitored domains (path/body — no product hostname list)."""
    if not detect_target(host or "")[0]:
        return False, ""
    if (method or "").upper() not in ("POST", "PUT", "PATCH"):
        return False, ""
    path_l = (path or "").lower().split("?", 1)[0]
    ct = (content_type or "").lower()
    data = raw or b""

    if any(x in path_l for x in _GENERIC_UPLOAD_PATH_MARKERS):
        if body_len >= 8:
            return True, f"File API ({path_l[:80]})"
    if "/backend-api/" in path_l:
        if any(x in path_l for x in ("/sentinel/", "/prepare", "/autocomplet", "/me", "/settings")):
            return False, ""
        if body_len >= 64 and (
            any(p in ct for p in UPLOAD_CONTENT_TYPES)
            or data[:5] == b"%PDF-"
            or (len(data) >= 2 and data[:2] == b"PK")
            or b"filename=" in data[:16000].lower()
        ):
            return True, f"Binary upload ({path_l[:80]})"
    return False, ""


def _path_looks_like_upload(path: str) -> bool:
    """True for generic file-upload URL paths on any monitored domain."""
    p = (path or "").lower().split("?", 1)[0]
    if not p:
        return False
    return any(m in p for m in _GENERIC_UPLOAD_PATH_MARKERS)


def is_unsubmitted_chat_body(path: str, body: str) -> bool:
    """True only for prepare/draft/in-progress — finished Send must predict."""
    path_l = (path or "").lower()
    if "/prepare" in path_l or path_l.endswith("prepare") or "autocomplet" in path_l:
        return True
    if "partial_query" in (body or "") and "query_str" not in (body or ""):
        return True
    if not body:
        return False
    try:
        data = json.loads(body)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    for m in data.get("messages") or []:
        if not isinstance(m, dict):
            continue
        status = str(m.get("status") or "").lower()
        if status in ("in_progress", "unfinished", "draft"):
            return True
        meta = m.get("metadata") if isinstance(m.get("metadata"), dict) else {}
        if meta.get("is_complete") is False:
            return True
    return False


def is_composer_typing_draft(domain: str, prompt: str) -> bool:
    """Skip only ultra-fast single-keystroke drafts while the user is still typing.

    Final Enter/send must always reach prediction — short prompts like "hi" and
  numbers like "613882" were missed when we treated h→hi growth as draft forever.
    """
    text = (prompt or "").strip()
    if not text or not domain:
        return False
    now = time.time()
    prev = _composer_draft.get(domain)
    _composer_draft[domain] = (text, now)
    if not prev:
        return False
    prev_text, prev_ts = prev
    elapsed = now - prev_ts
    # Pause before Enter/send → treat as a real submit, always predict.
    if elapsed >= 0.25:
        return False
    if text == prev_text:
        return False
    # Only skip a single-character extension during active typing (<250ms).
    if len(text) == len(prev_text) + 1 and text.startswith(prev_text):
        return True
    if len(prev_text) == len(text) + 1 and prev_text.startswith(text):
        return True
    return False


def _parts_to_text(parts) -> str | None:
    """Join ChatGPT/Claude-style content parts into plain user text (skip file/document blocks)."""
    if parts is None:
        return None
    if isinstance(parts, (str, int, float)):
        return _clean_prompt_text(str(parts))
    if not isinstance(parts, list):
        return None
    chunks = []
    for part in parts:
        if isinstance(part, (str, int, float)):
            chunks.append(str(part))
        elif isinstance(part, dict):
            if _is_file_content_part(part):
                continue
            ct = str(part.get("content_type") or "").lower()
            if ct and ct not in ("text", "input_text", "multimodal_text"):
                if ct in ("file", "image", "audio", "video", "document"):
                    continue
            if isinstance(part.get("text"), (str, int, float)):
                chunks.append(str(part["text"]))
            elif part.get("type") in ("text", "input_text") and isinstance(part.get("text"), (str, int, float)):
                chunks.append(str(part["text"]))
            elif "parts" in part and ct in ("", "text", "multimodal_text"):
                nested = _parts_to_text(part.get("parts"))
                if nested:
                    chunks.append(nested)
    return _clean_prompt_text(" ".join(chunks)) if chunks else None


def _extract_from_message_obj(msg: dict) -> str | None:
    """Pull user text from a single message object (OpenAI / ChatGPT / Claude / Copilot / generic shapes)."""
    if not isinstance(msg, dict):
        return None

    role = msg.get("role")
    if role is None and isinstance(msg.get("author"), dict):
        role = msg["author"].get("role")
    if role and str(role).lower() not in ("user", "human", "customer", "client", "sender"):
        return None

    content = msg.get("content")
    if isinstance(content, (str, int, float)):
        return _clean_prompt_text(str(content))
    if isinstance(content, dict):
        if _is_file_content_part(content):
            return None
        # ChatGPT web: {"content_type":"text","parts":["hello"]}
        if "parts" in content:
            return _parts_to_text(content.get("parts"))
        if isinstance(content.get("text"), (str, int, float)):
            return _clean_prompt_text(str(content["text"]))
    if isinstance(content, list):
        text_chunks: list[str] = []
        for block in content:
            if isinstance(block, dict) and _is_file_content_part(block):
                continue
            got = _parts_to_text([block]) if isinstance(block, dict) else _parts_to_text(block)
            if got:
                text_chunks.append(got)
        return _clean_prompt_text(" ".join(text_chunks)) if text_chunks else None

    # Copilot / Graph / Bing / generic fields
    for key in (
        "text", "prompt", "query", "query_str", "rawUserQuery",
        "utterance", "userMessage", "input", "question", "user_input", "inputs",
    ):
        val = msg.get(key)
        if isinstance(val, (str, int, float)):
            sval = str(val)
            if _is_opaque_wire_blob(sval):
                continue
            got = _clean_prompt_text(sval)
            if got:
                return got
    return None


def _extract_from_json(data) -> str | None:
    """Walk known and custom chat API shapes across ANY domain to extract the submitted user prompt."""
    if isinstance(data, list):
        # Gemini StreamGenerate is [null, "<nested json>", requestId, ...].
        # Never treat trailing numeric / token slots as the user prompt.
        if data and (data[0] is None or (len(data) >= 2 and isinstance(data[1], str) and data[1][:1] in ("[", "{"))):
            dumped = json.dumps(data, ensure_ascii=False)
            got = extract_gemini_prompt(dumped)
            if got:
                return _clean_prompt_text(got)
            return None
        # Prefer last user message in an array of messages
        for item in reversed(data):
            got = _extract_from_message_obj(item) if isinstance(item, dict) else None
            if got:
                return got
            if isinstance(item, str):
                # Raw array slots are often request ids; never save mixed-case RPC tokens.
                if _is_opaque_wire_blob(item):
                    continue
                got = _clean_prompt_text(item)
                if got:
                    return got
        return None

    if not isinstance(data, dict):
        return None

    # ChatGPT / OpenAI / DeepSeek / Mistral / Ollama / SGL / vLLM: messages[{author.role=user, content.parts}]
    if isinstance(data.get("messages"), list):
        for msg in reversed(data["messages"]):
            got = _extract_from_message_obj(msg)
            if got:
                return got

    # Claude / Anthropic: messages or prompt
    if isinstance(data.get("prompt"), (str, int, float)):
        got = _clean_prompt_text(str(data["prompt"]))
        if got:
            return got

    # Gemini API: contents[].parts[].text
    if isinstance(data.get("contents"), list) and data["contents"]:
        last = data["contents"][-1]
        if isinstance(last, dict):
            role = str(last.get("role", "user")).lower()
            if role in ("user", "human", ""):
                got = _parts_to_text(last.get("parts"))
                if got:
                    return got

    # Perplexity / Copilot / Bing / generic query fields across ANY Target Website
    for key in (
        "query", "query_str", "prompt", "input", "input_text", "inputs", "text",
        "message", "question", "user_input", "last_query", "user_query",
        "rawUserQuery", "utterance", "userMessage", "content", "instruction",
        "search_query", "q",
    ):
        val = data.get(key)
        if isinstance(val, (str, int, float)):
            sval = str(val)
            if _is_opaque_wire_blob(sval):
                continue
            got = _clean_prompt_text(sval)
            if got:
                return got
        elif isinstance(val, list):
            got = _parts_to_text(val)
            if got:
                return got
        elif isinstance(val, dict):
            got = _extract_from_message_obj(val)
            if got:
                return got
            for nk in ("query", "text", "prompt", "question", "rawUserQuery", "content", "input", "message"):
                if isinstance(val.get(nk), (str, int, float)):
                    sval = str(val[nk])
                    if _is_opaque_wire_blob(sval):
                        continue
                    got = _clean_prompt_text(sval)
                    if got:
                        return got

    # Copilot / Sydney send events — message.text only; content is often an encrypted token.
    if str(data.get("event", "")).lower() in ("send", "message", "chat"):
        msg = data.get("message")
        if isinstance(msg, dict):
            got = _extract_from_message_obj(msg)
            if got:
                return got
        for key in ("parts", "attachments", "input"):
            val = data.get(key)
            if isinstance(val, list):
                got = _parts_to_text(val)
                if got:
                    return got
            if isinstance(val, dict):
                got = _extract_from_message_obj(val)
                if got:
                    return got
            if isinstance(val, (str, int, float)):
                sval = str(val)
                if _is_opaque_wire_blob(sval):
                    continue
                got = _clean_prompt_text(sval)
                if got:
                    return got
        val = data.get("content")
        if isinstance(val, (str, int, float)):
            sval = str(val)
            if not _is_opaque_wire_blob(sval):
                got = _clean_prompt_text(sval)
                if got:
                    return got

    # Nested: { "params": { "query": "..." } }, { "payload": { ... } }, etc.
    for nest_key in ("params", "data", "payload", "body", "request", "arguments", "input", "options"):
        nested = data.get(nest_key)
        if isinstance(nested, (dict, list)):
            got = _extract_from_json(nested)
            if got:
                return got

    return None


def _deep_extract_from_json(data, depth: int = 0, max_depth: int = 10) -> str | None:
    """Recursive domain-agnostic JSON walk — finds user text in any nested shape."""
    if depth > max_depth:
        return None
    if isinstance(data, dict):
        role = str(data.get("role") or "").lower()
        if role in ("user", "human", "customer", "client", "sender", ""):
            got = _extract_from_message_obj(data)
            if got:
                return got
        for key in _UNIVERSAL_PROMPT_KEYS:
            val = data.get(key)
            if isinstance(val, (str, int, float)):
                sval = str(val)
                if not _is_opaque_wire_blob(sval):
                    got = _clean_prompt_text(sval)
                    if got and looks_like_user_prompt(got):
                        return got
            elif isinstance(val, list):
                got = _parts_to_text(val)
                if got:
                    return got
            elif isinstance(val, dict):
                got = _deep_extract_from_json(val, depth + 1, max_depth)
                if got:
                    return got
        for nest_key in ("params", "data", "payload", "body", "request", "arguments", "input", "options", "message", "messages"):
            nested = data.get(nest_key)
            if isinstance(nested, (dict, list)):
                got = _deep_extract_from_json(nested, depth + 1, max_depth)
                if got:
                    return got
    elif isinstance(data, list):
        for item in reversed(data):
            if isinstance(item, (dict, list)):
                got = _deep_extract_from_json(item, depth + 1, max_depth)
                if got:
                    return got
        return None


def _regex_extract_prompt_from_text(text: str) -> str | None:
    """Last-resort: pull known JSON keys from raw text without full parse."""
    if not text or len(text) < 2:
        return None
    for key in _UNIVERSAL_PROMPT_KEYS:
        pat = rf'"{re.escape(key)}"\s*:\s*"((?:[^"\\]|\\.)*)"'
        for m in re.finditer(pat, text):
            cand = _clean_prompt_text(m.group(1).replace("\\n", "\n").replace('\\"', '"'))
            if cand and looks_like_user_prompt(cand) and not _is_opaque_wire_blob(cand):
                return cand
    return None


def extract_prompt_from_query_string(url: str) -> str | None:
    """Extract prompt from GET query params on any monitored domain."""
    try:
        parsed = urllib.parse.urlparse(url or "")
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=False)
        for key in _UNIVERSAL_PROMPT_KEYS:
            vals = qs.get(key) or qs.get(key.lower())
            if vals and isinstance(vals[0], str):
                got = _clean_prompt_text(vals[0])
                if got and looks_like_user_prompt(got):
                    return got
    except Exception:
        pass
    return None


def extract_prompt_universal(body_bytes: bytes, content_type: str = "", host: str = "", url: str = "") -> str | None:
    """
    Domain-agnostic prompt extraction for ANY admin Target Website.
    Platform-specific parsers first, then deep JSON walk, query string, regex fallback.
    """
    got = extract_prompt(body_bytes, content_type, host=host)
    if got:
        return got
    if url:
        got = extract_prompt_from_query_string(url)
        if got:
            return got
    if not body_bytes:
        return None
    try:
        text = body_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return None
    if not text.strip():
        return None
    if text.lstrip().startswith(("{", "[")):
        try:
            data = json.loads(text)
            got = _deep_extract_from_json(data)
            if got:
                return got
        except Exception:
            pass
    return _regex_extract_prompt_from_text(text)


def detect_file_upload(flow: http.HTTPFlow, raw_content: str) -> tuple[bool, str]:
    """Detect real file upload attempts — not chat JSON / + menu / Gemini prompt posts."""
    headers = flow.request.headers
    content_type = (headers.get("content-type", "") or "").lower()
    path = (flow.request.path or "").lower()
    method = (flow.request.method or "").upper()
    host = (flow.request.pretty_host or "").lower()
    body_len = len(flow.request.content or b"")
    path_only = path.split("?", 1)[0]
    raw = raw_content or ""

    # ChatGPT / OpenAI CDN — catch before chat-path exclusions swallow file POSTs
    cgpt_up, cgpt_reason = detect_chatgpt_file_upload(host, path, method, content_type, body_len, flow.request.content or b"")
    if cgpt_up:
        return True, cgpt_reason

    # ── Never treat real chat Send as a file upload ──
    if is_gemini_chat_submit(path, raw) or "f.req=" in raw[:500]:
        return False, ""
    if is_perplexity_chat_submit(path, raw):
        return False, ""
    # Claude / ChatGPT / generic chat completion paths (JSON text prompts)
    chat_path_markers = (
        "/conversation", "/completion", "/completions", "/append_message",
        "/chat_conversations", "/backend-api/f/conversation", "/v1/messages",
        "/streamgenerate", "/generatecontent", "/chat/completions",
    )
    if any(m in path_only for m in chat_path_markers):
        # Only if this request is clearly a binary/multipart file body
        if "multipart/form-data" not in content_type and "octet-stream" not in content_type:
            return False, ""
        if "filename=" not in raw.lower() and "filename*=" not in raw.lower():
            if body_len < 8192:
                return False, ""

    # Google resumable: only real byte transfer / finalize — not session "start"/"query"
    goog_cmd = (headers.get("x-goog-upload-command", "") or "").lower()
    if goog_cmd:
        if any(x in goog_cmd for x in ("upload", "finalize", "append")) and body_len >= 64:
            return True, f"Google Resumable Upload ({goog_cmd})"
        return False, ""  # start / query / cancel = not a file
    for hk, hv in headers.items():
        hk_l = (hk or "").lower()
        hv_l = (hv or "").lower()
        if hk_l.startswith("x-goog-upload") and body_len >= 2048:
            if "start" in hv_l or "query" in hv_l or "cancel" in hv_l:
                continue
            return True, f"Google Resumable Upload ({hk}={hv_l[:40]})"

    # Real multipart with an actual filename= part (picker-open empty multipart ≠ upload)
    if "multipart/form-data" in content_type or "webkitformboundary" in raw[:300].lower():
        if "filename=" in raw or "filename*=" in raw.lower():
            # Empty filename="" is not a real file
            if re.search(r'filename\*?=(?:UTF-8\'\')?["\'][^"\']+', raw[:12000], re.I):
                empty = re.search(r'filename\*?=(?:UTF-8\'\')?["\']["\']', raw[:12000], re.I)
                named = re.search(r'filename\*?=(?:UTF-8\'\')?["\']([^"\']+)["\']', raw[:12000], re.I)
                if named and (named.group(1) or "").strip():
                    return True, f"File content-type ({(content_type or 'multipart').split(';')[0]})"
                if empty and not named:
                    return False, ""
                return True, f"File content-type ({(content_type or 'multipart').split(';')[0]})"
        return False, ""

    # Upload URL paths — require binary / large non-JSON (tiny JSON handshake ≠ upload)
    path_looks_upload = _path_looks_like_upload(path_only)
    for ep in UPLOAD_ENDPOINTS:
        if ep in path_only:
            path_looks_upload = True
            break
    if path_looks_upload:
        if any(x in path_only for x in ("/files/library", "/files/process", "/files/download", "/files/list")):
            return False, ""
        is_json_body = "json" in content_type or raw.lstrip()[:1] in ("{", "[")
        if "multipart/form-data" in content_type or "octet-stream" in content_type:
            if body_len >= 64:
                return True, f"File Upload Endpoint ({path_only[:80]})"
        if not is_json_body and body_len >= 1024:
            return True, f"File Upload Endpoint ({path_only[:80]})"
        if is_json_body and body_len >= 80_000:
            # Huge JSON sometimes wraps base64 file — rare
            if any(k in raw for k in ('"bytes"', '"data":', "base64", '"fileData"', '"inline_data"')):
                return True, f"File Upload Endpoint large JSON ({path_only[:80]})"
        if is_json_body and body_len >= 80 and any(
            k in raw for k in ('"file_name"', '"fileName"', '"filename"', '"mime_type"', '"mimeType"', '"bytes"')
        ):
            return True, f"File Upload Endpoint JSON ({path_only[:80]})"
        return False, ""

    # Binary content-type on non-chat hosts — require real size + magic / upload header
    chat_submit = is_chat_path(path, host, raw)
    if not chat_submit:
        for prefix in UPLOAD_CONTENT_TYPES:
            if prefix in content_type and body_len >= 512:
                # Skip generic application/json mistaken as upload
                if prefix in ("application/pdf", "image/", "audio/", "video/", "application/octet-stream",
                              "application/msword", "application/vnd."):
                    return True, f"File content-type ({content_type.split(';')[0]})"

    # JSON attachment heuristics: NEVER on chat submit
    if raw and not chat_submit and body_len >= 2048:
        strong = any(
            k in raw
            for k in (
                '"file_name"', '"fileName"', '"mime_type"', '"mimeType"',
                '"fileData"', '"inline_data"', '"inlineData"',
                "application/vnd.openxmlformats",
            )
        )
        if strong and (
            "filename=" in raw.lower()
            or body_len >= 8192
            or any(x in raw for x in ('"bytes"', "base64", "octet-stream"))
        ):
            return True, "File Attachment Payload in Request"

    return False, ""


_FAKE_UPLOAD_NAMES = frozenset({
    "", "attachment", "attachment.txt", "attachment.bin", "blob", "blob.txt",
    "file", "file.txt", "upload", "untitled", "document", "document.txt",
    "image", "image.png", "audio", "video", "media", "unknown", "null", "undefined",
})


def is_confident_file_upload(
    *,
    fname: str,
    content_type: str,
    raw_bytes: bytes,
    raw_text: str,
    upload_reason: str = "",
    host: str = "",
    path: str = "",
) -> bool:
    """True only for a real user file pick/upload — not chat/telemetry noise.

    Used to CACHE bytes. Prompt Log + Block happen only later on chat Send.
    """
    name = (fname or "").strip()
    name_l = name.lower()
    ct = (content_type or "").lower()
    data = raw_bytes or b""
    reason = (upload_reason or "").lower()
    raw = raw_text or ""
    host_l = (host or "").lower()
    path_l = (path or "").lower().split("?", 1)[0]

    # File API paths on admin-monitored domains — cache real bytes, not tiny JSON handshakes.
    if detect_target(host_l)[0] and _path_looks_like_upload(path_l) and len(data) >= 32:
        if name and name_l not in _FAKE_UPLOAD_NAMES:
            return True
        if any(x in ct for x in (
            "octet-stream", "multipart", "pdf", "image/", "audio/", "video/",
            "msword", "officedocument",
        )):
            return True
        if data[:5] == b"%PDF-" or (len(data) >= 2 and data[:2] == b"PK"):
            return True
        if b"filename=" in data[:16000].lower() or b"filename*=" in data[:16000].lower():
            return True
        if len(data) >= 2048:
            return True

    # WhatsApp / web.whatsapp sends lots of media-sync binary — never treat as AI file
    # unless path clearly looks like a user media upload AND we have a real name/magic.
    wa_like = "whatsapp" in host_l or "whatsapp" in path_l
    if wa_like:
        has_media_path = any(x in path_l for x in ("/upload", "/media", "/mms", "/cdn", "/attachment"))
        if not has_media_path:
            return False

    # Google resumable finalize/upload with bytes
    if "google resumable" in reason and len(data) >= 64:
        if any(x in reason for x in ("finalize", "upload", "append")):
            return True
        return False

    # Real filename with extension (not placeholder names)
    if name and name_l not in _FAKE_UPLOAD_NAMES and "." in name:
        ext = name_l.rsplit(".", 1)[-1]
        if 1 <= len(ext) <= 5 and ext.isalnum():
            return True

    # Magic bytes / known file shapes (strong evidence)
    if len(data) >= 64:
        if data[:5] == b"%PDF-" or b"%PDF-" in data[:4096]:
            return True
        if _looks_like_image(data, ct, name):
            return True
        if _looks_like_audio(data, ct, name):
            return True
        if data[:2] == b"PK" and len(data) >= 1024:
            # OOXML / zip — only if upload-ish path or office content-type
            if "officedocument" in ct or "zip" in ct or any(
                x in path_l for x in ("/upload", "/files", "/attachment", "/convert")
            ):
                return True

    # Multipart with non-empty real filename=
    if "filename=" in raw.lower() or "filename*=" in raw.lower():
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)["\']?', raw[:16000], re.I)
        if m:
            got = (m.group(1) or "").strip().strip('"\'')
            if got and got.lower() not in _FAKE_UPLOAD_NAMES:
                return True

    # Binary content-type alone is NOT enough (media-sync noise).
    # Require upload path + meaningful size + binary type.
    uploadish = _path_looks_like_upload(path_l) or "/media/" in path_l
    if uploadish and len(data) >= 2048 and any(
        x in ct
        for x in (
            "octet-stream", "application/pdf", "image/", "audio/", "video/",
            "msword", "officedocument",
        )
    ):
        return True

    return False


def extract_filename_from_upload(flow: http.HTTPFlow, raw_text: str = "") -> str:
    """Extract uploaded file name from headers, JSON body, multipart body, or URL path."""
    headers = flow.request.headers

    # 1. Content-Disposition header
    cd = headers.get("content-disposition", "")
    if "filename" in cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)["\']?', cd, re.I)
        if m:
            name = m.group(1).strip().strip('"\'')
            if name.lower() not in _FAKE_UPLOAD_NAMES:
                return name

    # 2. X-File-Name or upload headers
    for hk in ("x-file-name", "x-goog-upload-file-name", "x-filename", "x-upload-filename"):
        val = headers.get(hk)
        if val:
            name = str(val).strip().strip('"\'')
            if name.lower() not in _FAKE_UPLOAD_NAMES:
                return name

    # 3. JSON body fields (e.g. {"file_name": "data.pdf"} or {"fileName": "..."})
    if raw_text:
        m = re.search(
            r'["\'](?:file_name|fileName|filename)["\']\s*:\s*["\']([^"\']+\.[a-zA-Z0-9]{2,6})["\']',
            raw_text,
        )
        if m:
            name = m.group(1).strip()
            if name.lower() not in _FAKE_UPLOAD_NAMES:
                return name
        # Do NOT use generic "name"/"title" — WhatsApp/Gemini metadata often has junk like attachment.txt
        m = re.search(r'filename\s*=\s*["\']([^"\';\r\n]+\.[a-zA-Z0-9]{2,6})["\']', raw_text[:8000], re.I)
        if m:
            name = m.group(1).strip()
            if name.lower() not in _FAKE_UPLOAD_NAMES:
                return name

    # 4. Path parameter if it ends with a file extension
    path_clean = (flow.request.path or "").split("?", 1)[0]
    last_seg = path_clean.rsplit("/", 1)[-1]
    if "." in last_seg and any(last_seg.lower().endswith(ext) for ext in (
        ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".json",
        ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".py", ".js",
        ".wav", ".mp3", ".m4a", ".webm",
    )):
        name = urllib.parse.unquote(last_seg)
        if name.lower() not in _FAKE_UPLOAD_NAMES:
            return name

    return ""


def extract_pdf_bytes(raw: bytes) -> bytes | None:
    """Return PDF payload if present in raw upload body (direct or multipart)."""
    if not raw:
        return None
    if raw.startswith(b"%PDF-"):
        data = raw
    else:
        idx = raw.find(b"%PDF-")
        if idx < 0 or idx > 64 * 1024:
            return None
        data = raw[idx:]
    eof = data.rfind(b"%%EOF")
    if eof >= 0:
        end = eof + 5
        while end < len(data) and data[end] in (10, 13):
            end += 1
        data = data[:end]
    if len(data) > 20 * 1024 * 1024:
        return None
    return data


def _sniff_upload_content_type(data: bytes, file_name: str = "", hint: str = "") -> str:
    hint = (hint or "").split(";")[0].strip().lower()
    if hint and hint not in ("application/octet-stream", "binary/octet-stream"):
        return hint
    if data.startswith(b"%PDF-") or b"%PDF-" in data[:4096]:
        return "application/pdf"
    if len(data) >= 3 and data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF:
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:2] == b"PK":
        low = (file_name or "").lower()
        if low.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if low.endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if low.endswith(".pptx"):
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        return "application/zip"
    ext = os.path.splitext(file_name or "")[1].lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".txt": "text/plain",
        ".csv": "text/csv",
        ".json": "application/json",
    }.get(ext, "application/octet-stream")


def extract_upload_file_payload(raw: bytes, content_type: str = "", file_name: str = "") -> tuple[bytes | None, str, str]:
    """Best-effort file bytes from upload body. Returns (bytes, content_type, name)."""
    if not raw:
        return None, "", file_name or "attachment"
    name = (file_name or "").strip() or "attachment"
    pdf = extract_pdf_bytes(raw)
    if pdf:
        if not name.lower().endswith(".pdf"):
            name = f"{name}.pdf" if name != "attachment" else "document.pdf"
        return pdf, "application/pdf", name

    # ChatGPT conversation / files-API JSON is not the uploaded document.
    stripped = raw.lstrip()
    if stripped[:1] in (b"{", b"[") and raw[:2] != b"PK":
        return None, "", name

    # Multipart: extract part after filename=
    low_prefix = raw[: min(len(raw), 64 * 1024)].lower()
    if b"filename=" in low_prefix or b"webkitformboundary" in low_prefix or b"multipart" in (content_type or "").lower().encode():
        idx = low_prefix.find(b"filename=")
        if idx >= 0:
            rest = raw[idx:]
            sep = b"\r\n\r\n"
            si = rest.find(sep)
            if si < 0:
                sep = b"\n\n"
                si = rest.find(sep)
            if si >= 0:
                body = rest[si + len(sep) :]
                end = len(body)
                for i in range(len(body) - 2):
                    if body[i] == 10 and body[i + 1] == 45 and body[i + 2] == 45:  # \n--
                        end = i - 1 if i > 0 and body[i - 1] == 13 else i
                        break
                part = body[:end]
                if part:
                    pdf2 = extract_pdf_bytes(part)
                    if pdf2:
                        if not name.lower().endswith(".pdf"):
                            name = f"{name}.pdf" if name != "attachment" else "document.pdf"
                        return pdf2, "application/pdf", name
                    ctype = _sniff_upload_content_type(part, name, content_type)
                    if len(part) > 20 * 1024 * 1024:
                        part = part[: 20 * 1024 * 1024]
                    return part, ctype, name

    # Direct binary body (resumable / octet-stream)
    if len(raw) >= 32:
        ctype = _sniff_upload_content_type(raw, name, content_type)
        # Skip tiny JSON metadata
        stripped = raw.lstrip()
        if stripped[:1] in (b"{", b"[") and len(raw) < 50_000 and ctype == "application/octet-stream":
            return None, "", name
        data = raw if len(raw) <= 20 * 1024 * 1024 else raw[: 20 * 1024 * 1024]
        return data, ctype, name
    return None, "", name


def _purge_upload_file_cache(now: float | None = None) -> None:
    now = now if now is not None else time.time()
    dead = [k for k, v in _UPLOAD_FILE_CACHE.items() if now - float(v.get("ts") or 0) > _UPLOAD_FILE_CACHE_TTL]
    for k in dead:
        _UPLOAD_FILE_CACHE.pop(k, None)
    while len(_UPLOAD_FILE_CACHE) > _UPLOAD_FILE_CACHE_MAX:
        oldest = min(_UPLOAD_FILE_CACHE.items(), key=lambda kv: float(kv[1].get("ts") or 0))
        _UPLOAD_FILE_CACHE.pop(oldest[0], None)
    _purge_upload_queues(now)


def _upload_queue_key(alias: str) -> str:
    return f"{alias}::__queue__"


def _purge_upload_queues(now: float | None = None) -> None:
    now = now if now is not None else time.time()
    for qkey in list(_UPLOAD_FILE_QUEUES.keys()):
        q = _UPLOAD_FILE_QUEUES.get(qkey) or []
        alive = [e for e in q if now - float(e.get("ts") or 0) <= _UPLOAD_FILE_CACHE_TTL]
        if alive:
            _UPLOAD_FILE_QUEUES[qkey] = alive[-_UPLOAD_FILE_QUEUE_MAX:]
        else:
            _UPLOAD_FILE_QUEUES.pop(qkey, None)


def _remove_cache_keys_for_entry(entry: dict, aliases: list[str]) -> None:
    fname = (entry.get("file_name") or "attachment").lower()
    fid = entry.get("file_id") or ""
    uid = entry.get("cache_uid")
    for alias in aliases:
        _UPLOAD_FILE_CACHE.pop(f"{alias}|latest", None)
        _UPLOAD_FILE_CACHE.pop(f"{alias}|name|{fname}", None)
        if fid:
            _UPLOAD_FILE_CACHE.pop(f"{alias}|id|{fid}", None)
            _UPLOAD_FILE_CACHE.pop(f"{alias}|id|file-{fid}", None)
        if uid:
            qkey = _upload_queue_key(alias)
            if qkey in _UPLOAD_FILE_QUEUES:
                _UPLOAD_FILE_QUEUES[qkey] = [
                    e for e in _UPLOAD_FILE_QUEUES[qkey] if e.get("cache_uid") != uid
                ]


def upload_domain_aliases(domain: str) -> list[str]:
    """All admin-added Target Websites in the same family as `domain`.

    Built from /api/browser-ai/targets (platform_name + parent_id + subdomain).
    Upload may hit host A; chat Send hits host B — cache is shared across the family.
    """
    get_target_domains()
    d = _normalize_domain(domain or "")
    if not d:
        return []

    fam = _cached_families.get(d)
    if fam:
        return sorted(fam)

    best: set[str] | None = None
    best_len = -1
    for key, fam_set in _cached_families.items():
        if d == key or d.endswith("." + key):
            if len(key) > best_len:
                best_len = len(key)
                best = set(fam_set)
    if best:
        return sorted(best)

    # Single monitored domain with no siblings in Target Websites.
    return [d]


def cache_upload_file(
    domain: str,
    *,
    file_name: str,
    raw_bytes: bytes,
    content_type: str,
    upload_reason: str,
    rule_hit: bool = False,
    rule_name: str = "",
    rule_action: str = "",
    file_id: str = "",
) -> None:
    """Remember file at upload-time; enforcement/log waits for chat Send."""
    payload, ctype, name = extract_upload_file_payload(raw_bytes or b"", content_type, file_name)
    # Keep original body when payload extract fails — needed for View/Download after Block Upload.
    # Do not cache ChatGPT JSON handshakes as if they were the PDF.
    fallback = raw_bytes or b""
    if not payload and fallback.lstrip()[:1] in (b"{", b"["):
        return
    stored = payload if payload else fallback
    if not stored:
        return
    if len(stored) > 20 * 1024 * 1024:
        stored = stored[: 20 * 1024 * 1024]
    entry = {
        "ts": time.time(),
        "domain": domain,
        "file_name": name or file_name or "attachment",
        "content_type": ctype or content_type or "application/octet-stream",
        "raw_bytes": stored,
        "upload_reason": upload_reason or "",
        "rule_hit": bool(rule_hit),
        "rule_name": rule_name or "",
        "rule_action": (rule_action or "").upper(),
        "file_id": file_id or "",
    }
    fname_key = (entry["file_name"] or "attachment").lower()
    entry["cache_uid"] = f"{entry['ts']:.6f}|{fname_key}|{len(stored)}"
    keys: list[str] = []
    aliases = upload_domain_aliases(domain)
    for alias in aliases:
        if file_id:
            keys.append(f"{alias}|id|{file_id}")
        keys.append(f"{alias}|name|{fname_key}")
        keys.append(f"{alias}|latest")
    with _UPLOAD_FILE_CACHE_LOCK:
        _purge_upload_file_cache()
        for k in keys:
            _UPLOAD_FILE_CACHE[k] = entry
        for alias in aliases:
            qkey = _upload_queue_key(alias)
            q = _UPLOAD_FILE_QUEUES.setdefault(qkey, [])
            q.append(entry)
            if len(q) > _UPLOAD_FILE_QUEUE_MAX:
                _UPLOAD_FILE_QUEUES[qkey] = q[-_UPLOAD_FILE_QUEUE_MAX:]
    print(
        f"[UnifAI Proxy] FILE CACHED (await Send) | {domain} | {entry['file_name']} | "
        f"{len(entry['raw_bytes'])} bytes | rule_hit={rule_hit} | aliases={len(keys)}"
    )


def _extract_file_ids_from_chat(raw_text: str) -> list[str]:
    ids: list[str] = []
    if not raw_text:
        return ids
    for pat in (
        r'"file_id"\s*:\s*"([^"]+)"',
        r'"fileId"\s*:\s*"([^"]+)"',
        r'"file_uuid"\s*:\s*"([^"]+)"',
        r'"fileUuid"\s*:\s*"([^"]+)"',
        r'"docId"\s*:\s*"([^"]+)"',
        r'"document_id"\s*:\s*"([^"]+)"',
        r'"attachment_id"\s*:\s*"([^"]+)"',
        r'"attachmentId"\s*:\s*"([^"]+)"',
        r'file-service://file-([a-zA-Z0-9_-]+)',
        r'asset_pointer"\s*:\s*"[^"]*file-([a-zA-Z0-9_-]+)',
        r'"id"\s*:\s*"(file-[a-zA-Z0-9_-]+)"',
    ):
        for m in re.finditer(pat, raw_text):
            ids.append(m.group(1))
    out: list[str] = []
    seen: set[str] = set()
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def chat_carries_attachment(raw_text: str) -> bool:
    """True only when THIS chat Send actually references a real attached file.

    Claude/Copilot text-only bodies often contain keys like "document", "attachments":[]
    or "media_type" — those must NOT count as an upload (that caused Prompt Log =
    "[FILE UPLOAD] attachment" for normal typed prompts).
    """
    if not raw_text:
        return False
    low = raw_text.lower()

    # Empty arrays / nulls are not attachments
    if re.search(r'"attachments"\s*:\s*\[\s*\]', low):
        low = re.sub(r'"attachments"\s*:\s*\[\s*\]', " ", low)
    if re.search(r'"files"\s*:\s*\[\s*\]', low):
        low = re.sub(r'"files"\s*:\s*\[\s*\]', " ", low)
    if re.search(r'"documents"\s*:\s*\[\s*\]', low):
        low = re.sub(r'"documents"\s*:\s*\[\s*\]', " ", low)

    # Strong URI / pointer evidence
    if any(
        x in low
        for x in (
            "file-service://",
            "attachment://",
            "asset_pointer",
            "converted_file",
            "convert_document",
            "/c/api/attachments",
            '"messagetype":"image"',
            "input_file",
            "input_image",
        )
    ):
        return True

    # Non-empty attachment / files arrays
    if re.search(r'"attachments"\s*:\s*\[\s*\{', low):
        return True
    if re.search(r'"files"\s*:\s*\[\s*\{', low):
        return True
    if re.search(r'"documents"\s*:\s*\[\s*\{', low):
        return True

    # Real IDs with non-empty values (not null / "")
    id_patterns = (
        r'"file_id"\s*:\s*"(?!null)[^"]+"',
        r'"fileid"\s*:\s*"(?!null)[^"]+"',
        r'"file_uuid"\s*:\s*"(?!null)[^"]+"',
        r'"fileuuid"\s*:\s*"(?!null)[^"]+"',
        r'"docid"\s*:\s*"(?!null)[^"]+"',
        r'"document_id"\s*:\s*"(?!null)[^"]+"',
        r'"attachment_id"\s*:\s*"(?!null)[^"]+"',
        r'"attachmentid"\s*:\s*"(?!null)[^"]+"',
        r'"file_uri"\s*:\s*"(?!null)[^"]+"',
        r'"fileuri"\s*:\s*"(?!null)[^"]+"',
        r'"image_url"\s*:\s*"(?!null)https?[^"]+"',
        r'"imageurl"\s*:\s*"(?!null)https?[^"]+"',
    )
    if any(re.search(p, low) for p in id_patterns):
        return True

    # Inline binary / base64 file payloads (Gemini / multimodal)
    if re.search(r'"(?:inline_data|inlinedata|filedata)"\s*:\s*\{', low):
        return True
    if re.search(r'"media_type"\s*:\s*"(?:application/|image/|audio/|video/)', low):
        # Claude document blocks often use media_type + data together
        if '"data"' in low or "base64" in low or "extracted_content" in low:
            return True

    # Filename with common document/image extension in this send
    if re.search(
        r'"(?:file_name|filename|fileName|name|title)"\s*:\s*"[^"]+\.(?:pdf|docx?|xlsx?|pptx?|png|jpe?g|gif|webp|txt|csv)"',
        low,
    ):
        return True

    # Claude content blocks: {"type":"document"|"image"|"file"|"audio", ...} with real payload
    if re.search(r'"type"\s*:\s*"(?:document|image|file|input_image|input_file|audio|input_audio|voice)"', low):
        if any(
            x in low
            for x in (
                '"source"', '"data"', "base64", "file_uuid", "file_id",
                "application/pdf", "image/png", "image/jpeg", "extracted_content",
                "audio/", "audio/wav", "audio/mpeg", "audio/webm",
            )
        ):
            return True

    # Voice / audio attachment markers
    if any(
        x in low
        for x in (
            '"input_audio"', "audio_url", '"voice_mode"',
            "audio/webm", "audio/wav", "audio/mpeg", "audio/mp4",
        )
    ):
        return True
    if re.search(r'"(?:transcript|transcription)"\s*:\s*"(?!null)[^"]{2,}"', low):
        # Transcript alone is enough to treat as voice content for rule scan on Send
        if any(x in low for x in ("audio", "voice", "speech", "dictation", "file_id", "attachment")):
            return True

    # Cloud file URI refs on chat submits (not empty placeholders)
    if re.search(r'"(?:file_data|filedata|file_uri|fileuri)"\s*:\s*\{', low):
        return True
    if re.search(r'https?://[^"\']+/(?:file/|open\?id=)', low):
        if re.search(r'"(?:file_data|filedata|file_uri|fileuri|uri|url)"\s*:', low):
            return True

    # ChatGPT / OpenAI file pointers
    if chatgpt_carries_file(raw_text):
        return True
    if re.search(r'"id"\s*:\s*"file-[a-zA-Z0-9_-]+"', low):
        return True
    if re.search(r'"mime_type"\s*:\s*"(?:application/|image/|audio/|video/)', low):
        if '"attachments"' in low or '"files"' in low or '"content_type"' in low:
            return True

    # Copilot / Sydney image or file payloads (base64 in send frame)
    if copilot_carries_binary_attach(raw_text):
        return True

    return False


def copilot_carries_binary_attach(raw_text: str) -> bool:
    """Copilot/Edge image or file sends often embed base64 instead of file_id."""
    if not raw_text:
        return False
    low = raw_text.lower()
    if any(
        x in low
        for x in (
            '"messagetype":"image"',
            '"messagetype": "image"',
            '"inputimage"',
            '"input_image"',
            '"imageurl"',
            '"image_url"',
            '"binarydata"',
            '"binary_data"',
        )
    ):
        return True
    if re.search(r'"(?:data|image|bytes|content)"\s*:\s*"[A-Za-z0-9+/=\s]{500,}"', raw_text):
        return True
    if re.search(r'"type"\s*:\s*"(?:image|input_image|input_file|file|document)"', low):
        if re.search(r'"(?:data|source|url)"\s*:\s*', low):
            return True
    return False


def extract_attachment_filename_from_send(raw_text: str) -> str:
    """Best-effort filename from a chat Send JSON body."""
    if not raw_text:
        return ""
    for pat in (
        r'["\'](?:file_name|fileName|filename)["\']\s*:\s*["\']([^"\']+)["\']',
        r'"attachments"\s*:\s*\[\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
        r'"files"\s*:\s*\[\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
        r'"name"\s*:\s*"([^"]+\.(?:pdf|docx?|xlsx?|pptx?|csv|txt|png|jpe?g|gif|webp|zip))"',
        r'"parts"\s*:\s*\[[\s\S]{0,8000}?"name"\s*:\s*"([^"]+\.[a-zA-Z0-9]{2,8})"',
    ):
        m = re.search(pat, raw_text, re.I)
        if m:
            name = (m.group(1) or "").strip()
            if name and name.lower() not in _FAKE_UPLOAD_NAMES:
                return name
    return ""


def extract_inline_attachment_bytes(raw_text: str) -> tuple[bytes, str, str]:
    """Pull inline base64 file/image bytes from a chat Send body for rule scanning."""
    if not raw_text:
        return b"", "", ""
    import base64

    mime = ""
    m_mime = re.search(r'"(?:mime_type|mimeType|media_type|content_type)"\s*:\s*"([^"]+)"', raw_text, re.I)
    if m_mime:
        mime = (m_mime.group(1) or "").strip()
    fname = extract_attachment_filename_from_send(raw_text)

    for pat in (
        r'"(?:data|bytes|content|image|binary|base64)"\s*:\s*"([A-Za-z0-9+/=\s\\]{200,})"',
    ):
        m = re.search(pat, raw_text)
        if not m:
            continue
        blob = (m.group(1) or "").replace("\\n", "").replace("\\r", "").replace(" ", "")
        if len(blob) < 200:
            continue
        try:
            data = base64.b64decode(blob, validate=False)
        except Exception:
            continue
        if len(data) >= 32:
            if not mime:
                if data[:5] == b"%PDF-":
                    mime = "application/pdf"
                elif data[:2] == b"PK":
                    mime = "application/vnd.openxmlformats-officedocument"
                elif data[:3] == b"\xff\xd8\xff":
                    mime = "image/jpeg"
                elif data[:8] == b"\x89PNG\r\n\x1a\n":
                    mime = "image/png"
            return data[:20 * 1024 * 1024], mime, fname
    return b"", "", ""


def _file_policy_applies_on_send(path: str, raw_text: str, raw_bytes: bytes) -> bool:
    """File scan/log only on finished chat Send — never on upload-picker API calls."""
    if _path_looks_like_upload(path):
        return False
    return _is_confident_chat_send(path, raw_text, raw_bytes)


def block_upload_request_now(
    flow: http.HTTPFlow,
    *,
    platform: str,
    domain: str,
    host: str,
    client_ip: str,
    fname: str,
    raw_bytes: bytes,
    content_type: str,
    raw_text: str = "",
    blocked_reason: str = "Block Upload",
    rule_name: str = "",
    reply_text: str = "",
) -> None:
    """Stop an upload request immediately and log it as blocked."""
    upload_warn = (get_control_settings().get("upload_warning") or "").strip() or "Upload block"
    label = (fname or "attachment").strip() or "attachment"
    tag = _upload_log_tag(label, content_type, raw_bytes)
    excerpt = ""
    scanned_full = ""
    if raw_bytes:
        scanned_full = extract_upload_text_for_rules(raw_bytes, content_type, raw_text, label) or ""
        if scanned_full:
            excerpt = re.sub(r"\s+", " ", scanned_full).strip()[:180]
    reason_label = (rule_name or blocked_reason or "Block Upload").strip()
    prompt_log = f"{tag} {label} — Blocked ({reason_label})"
    dedupe_key = f"upload-req-block|{reason_label}|{label}"
    if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
        print(f"[UnifAI Proxy] UPLOAD BLOCKED (request) | {client_ip} → {host} | {label} | {reason_label}")
        ok = post_upload_intercept(
            platform=platform,
            prompt=prompt_log,
            client_ip=client_ip,
            domain=domain,
            url=flow.request.url,
            method=flow.request.method,
            file_name=label,
            is_blocked=True,
            blocked_reason=reason_label,
            raw_bytes=raw_bytes,
            content_type=content_type,
            extracted_text=scanned_full,
        )
        if ok:
            mark_duplicate_event(domain, dedupe_key)
    if not reply_text:
        if rule_name:
            rule_warn = _warning_for_rule_name(rule_name)
            reply_text = f"{rule_warn} -- {rule_name}" if rule_warn else f"Upload blocked — {rule_name}"
        else:
            reply_text = upload_warn
    make_blocked_response(flow, reason_label, host, reply_text=reply_text)


def take_all_cached_uploads_for_send(
    domain: str,
    raw_text: str = "",
    *,
    allow_latest: bool = False,
) -> list[dict]:
    """Pop all matching cached uploads for this chat Send (one log row per file on Send)."""
    aliases = upload_domain_aliases(domain)
    found: list[dict] = []
    seen_uids: set[str] = set()

    def add_entry(entry: dict) -> None:
        uid = entry.get("cache_uid") or str(id(entry))
        if uid in seen_uids:
            return
        seen_uids.add(uid)
        found.append(entry)

    with _UPLOAD_FILE_CACHE_LOCK:
        _purge_upload_file_cache()
        for fid in _extract_file_ids_from_chat(raw_text):
            for alias in aliases:
                for key in (f"{alias}|id|{fid}", f"{alias}|id|file-{fid}"):
                    if key in _UPLOAD_FILE_CACHE:
                        entry = _UPLOAD_FILE_CACHE.pop(key)
                        add_entry(entry)
                        _remove_cache_keys_for_entry(entry, aliases)
        for m in re.finditer(
            r'["\'](?:file_name|fileName|filename|name|title)["\']\s*:\s*["\']([^"\']+)["\']',
            raw_text or "",
        ):
            name = m.group(1).strip().lower()
            if not name or name in ("attachment", "file", "document", "untitled"):
                continue
            for alias in aliases:
                key = f"{alias}|name|{name}"
                if key in _UPLOAD_FILE_CACHE:
                    entry = _UPLOAD_FILE_CACHE.pop(key)
                    add_entry(entry)
                    _remove_cache_keys_for_entry(entry, aliases)
        if allow_latest:
            now = time.time()
            for alias in aliases:
                qkey = _upload_queue_key(alias)
                for entry in list(_UPLOAD_FILE_QUEUES.get(qkey, [])):
                    age = now - float(entry.get("ts") or 0)
                    if age <= _UPLOAD_LATEST_MATCH_TTL:
                        add_entry(entry)
                        _remove_cache_keys_for_entry(entry, aliases)
                if qkey in _UPLOAD_FILE_QUEUES:
                    _UPLOAD_FILE_QUEUES[qkey] = [
                        e for e in _UPLOAD_FILE_QUEUES[qkey]
                        if e.get("cache_uid") not in seen_uids
                    ]
                latest = _UPLOAD_FILE_CACHE.get(f"{alias}|latest")
                if latest and (now - float(latest.get("ts") or 0)) <= _UPLOAD_LATEST_MATCH_TTL:
                    add_entry(latest)
                    _remove_cache_keys_for_entry(latest, aliases)
    return found


def take_cached_upload_for_send(
    domain: str,
    raw_text: str = "",
    *,
    allow_latest: bool = False,
) -> dict | None:
    """Backward-compatible single-file helper."""
    all_files = take_all_cached_uploads_for_send(domain, raw_text, allow_latest=allow_latest)
    return all_files[0] if all_files else None


def take_recent_confident_caches_for_send(domain: str) -> list[dict]:
    """Bind recent real uploads on Send when attachment markers are weak."""
    aliases = upload_domain_aliases(domain)
    now = time.time()
    out: list[dict] = []
    seen: set[str] = set()
    with _UPLOAD_FILE_CACHE_LOCK:
        _purge_upload_file_cache()
        for alias in aliases:
            candidates: list[dict] = list(_UPLOAD_FILE_QUEUES.get(_upload_queue_key(alias), []))
            latest = _UPLOAD_FILE_CACHE.get(f"{alias}|latest")
            if latest:
                candidates.append(latest)
            for entry in candidates:
                uid = entry.get("cache_uid") or str(id(entry))
                if uid in seen:
                    continue
                age = now - float(entry.get("ts") or 0)
                if age > _UPLOAD_LATEST_MATCH_TTL:
                    continue
                name = (entry.get("file_name") or "").strip()
                if not name or name.lower() in _FAKE_UPLOAD_NAMES:
                    continue
                raw = entry.get("raw_bytes") or b""
                if not is_confident_file_upload(
                    fname=name,
                    content_type=(entry.get("content_type") or ""),
                    raw_bytes=raw if isinstance(raw, (bytes, bytearray)) else b"",
                    raw_text="",
                    upload_reason=(entry.get("upload_reason") or ""),
                    host=alias,
                    path="/files",
                ):
                    continue
                seen.add(uid)
                out.append(entry)
                _remove_cache_keys_for_entry(entry, aliases)
    return out


def take_recent_confident_cache_for_send(domain: str) -> dict | None:
    all_files = take_recent_confident_caches_for_send(domain)
    return all_files[0] if all_files else None


def _scan_upload_for_rules(
    raw_bytes: bytes,
    content_type: str,
    raw_text: str,
    file_label: str,
    cached: dict | None = None,
    *,
    platform: str = "",
    domain: str = "",
    client_ip: str = "",
    url: str = "",
    method: str = "",
) -> tuple[str, bool, str, str, str, list[str], bool]:
    """Scan file bytes on Send only — extract by type, then apply Guard Rules (+ AI bot if configured)."""
    scanned = ""
    rule_hit = False
    rule_name = ""
    rule_action = ""
    excerpt = ""
    upload_images: list[str] = []
    scan_evaluated = False
    try:
        if raw_bytes:
            scanned = extract_upload_text_for_rules(raw_bytes, content_type, raw_text or "", file_label)
        upload_images = _upload_images_for_vision(raw_bytes or b"", content_type, file_label) if raw_bytes else []
        if scanned:
            excerpt = re.sub(r"\s+", " ", scanned).strip()[:180]
            rule_hit, rule_name, rule_action = match_guard_rules_on_text(scanned)
            rule_action = (rule_action or "").upper()
            if rule_action == "WARN":
                rule_action = "REDACT"
        # Backend: regex + bot on extracted text / vision images (when any active rules exist).
        has_regex = bool(get_guard_rules())
        run_backend = bool(
            platform and domain and (scanned or upload_images) and (has_ai_bot_rules() or has_regex)
        )
        if run_backend:
            scan_evaluated = True
            try:
                allowed, rt, action, _, _ = send_to_backend(
                    platform, domain, (scanned or "")[:50_000], client_ip, url, method or "POST",
                    upload_images=upload_images,
                    evaluation_only=True,
                )
                rule_hit, rule_name, rule_action = _merge_file_scan_backend(
                    rule_hit, rule_name, rule_action, allowed, rt, action or "",
                )
            except Exception as e:
                print(f"[UnifAI Proxy] AI bot file scan failed (allowed): {e}")
    except Exception as e:
        print(f"[UnifAI Proxy] file rule scan failed (allowed): {e}")
        scanned = ""
        rule_hit = False
        rule_name = ""
        rule_action = ""
        excerpt = ""
        upload_images = []
        scan_evaluated = False
    return scanned, rule_hit, rule_name, rule_action, excerpt, upload_images, scan_evaluated


def _process_one_cached_file_on_send(
    *,
    cached: dict | None,
    platform: str,
    domain: str,
    host: str,
    client_ip: str,
    url: str,
    method: str,
    raw_text: str,
    content_type: str = "",
    file_name_hint: str = "",
    has_attach: bool = False,
) -> tuple[bool, str, str]:
    """Process one file on chat Send. Returns (should_block_send, block_message, redact_notice)."""
    try:
        return _process_one_cached_file_on_send_impl(
            cached=cached,
            platform=platform,
            domain=domain,
            host=host,
            client_ip=client_ip,
            url=url,
            method=method,
            raw_text=raw_text,
            content_type=content_type,
            file_name_hint=file_name_hint,
            has_attach=has_attach,
        )
    except Exception as e:
        print(f"[UnifAI Proxy] file send policy error (allowed): {e}")
        return False, "", ""


def _process_one_cached_file_on_send_impl(
    *,
    cached: dict | None,
    platform: str,
    domain: str,
    host: str,
    client_ip: str,
    url: str,
    method: str,
    raw_text: str,
    content_type: str = "",
    file_name_hint: str = "",
    has_attach: bool = False,
) -> tuple[bool, str, str]:
    fname = (file_name_hint or "").strip() or extract_attachment_filename_from_send(raw_text or "")
    if cached:
        fname = fname or (cached.get("file_name") or "").strip()
    if not fname:
        for m in re.finditer(
            r'["\'](?:file_name|fileName|filename)["\']\s*:\s*["\']([^"\']+)["\']',
            raw_text or "",
        ):
            cand = m.group(1).strip()
            if cand and "." in cand and cand.lower() not in _FAKE_UPLOAD_NAMES:
                fname = cand
                break

    cached_name = ((cached.get("file_name") if cached else "") or "").strip()
    real_cached = bool(
        cached
        and (
            (cached.get("raw_bytes") and len(cached.get("raw_bytes") or b"") >= 32)
            or (cached_name and cached_name.lower() not in _FAKE_UPLOAD_NAMES)
        )
    )
    real_name = bool(fname and fname.lower() not in _FAKE_UPLOAD_NAMES)
    if not real_cached and not real_name and not has_attach:
        return False, "", ""

    file_label = fname if real_name else (
        cached_name if cached_name and cached_name.lower() not in _FAKE_UPLOAD_NAMES else "attachment"
    )
    if not file_label:
        file_label = "attachment"

    upload_warn = (get_control_settings().get("upload_warning") or "").strip()
    base_upload_msg = upload_warn or "Upload block"

    cached_bytes = (cached.get("raw_bytes") if cached else b"") or b""
    cached_ct = (cached.get("content_type") if cached else "") or content_type
    if not cached_bytes and has_attach:
        inline_bytes, inline_ct, inline_name = extract_inline_attachment_bytes(raw_text or "")
        if inline_bytes:
            cached_bytes = inline_bytes
            cached_ct = inline_ct or content_type
            if inline_name and inline_name.lower() not in _FAKE_UPLOAD_NAMES:
                file_label = inline_name
    scanned, rule_hit, rule_name, rule_action, excerpt, upload_images, scan_evaluated = _scan_upload_for_rules(
        cached_bytes, cached_ct, raw_text or "", file_label, cached,
        platform=platform, domain=domain, client_ip=client_ip, url=url, method=method,
    )

    block_all = controls_active("block_upload")
    has_scan_content = bool((scanned or "").strip() or upload_images)
    scan_guard = _file_scan_guard_metadata(
        scanned, upload_images, rule_hit, rule_name, rule_action, scan_evaluated=scan_evaluated,
    )
    block_for_rule = bool(rule_hit and rule_action == "BLOCK" and has_scan_content)
    redact_for_rule = bool(
        rule_hit
        and rule_action == "REDACT"
        and not block_all
        and has_scan_content
    )
    tag = _upload_log_tag(file_label, cached_ct, cached_bytes)

    if redact_for_rule:
        redact_log = f"{tag} {file_label} — Redacted ({rule_name or 'policy'})"
        dedupe_key = f"upload-send-redact|{rule_name}|{file_label}"
        if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
            print(f"[UnifAI Proxy] FILE SEND REDACTED | {client_ip} → {host} | {file_label}")
            ok = post_upload_intercept(
                platform=platform,
                prompt=redact_log,
                client_ip=client_ip,
                domain=domain,
                url=url,
                method=method,
                file_name=file_label,
                is_blocked=False,
                content_type=cached_ct,
                extracted_text=scanned,
                upload_images=upload_images,
                scan_guard=scan_guard,
            )
            if ok:
                mark_duplicate_event(domain, dedupe_key)
        notice = _redact_notice_for_rule(rule_name)
        return False, "", notice

    if block_all or block_for_rule:
        blocked_reason = "Block Upload" if block_all else (rule_name or "Guard Rule (file content)")
        if block_all:
            prompt_log = f"{tag} {file_label} — Blocked (Block Upload)"
            msg = base_upload_msg
        else:
            rule_warn = _warning_for_rule_name(rule_name)
            left = (rule_warn or base_upload_msg).strip() or "Upload block"
            prompt_log = f"{tag} {file_label} — Blocked ({rule_name or 'policy'})"
            msg = f"{left} -- {rule_name}" if rule_name else left
        dedupe_key = f"upload-send-block|{blocked_reason}|{file_label}"
        if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
            print(f"[UnifAI Proxy] FILE SEND BLOCKED | {client_ip} → {host} | {file_label}")
            ok = post_upload_intercept(
                platform=platform,
                prompt=prompt_log,
                client_ip=client_ip,
                domain=domain,
                url=url,
                method=method,
                file_name=file_label,
                is_blocked=True,
                blocked_reason=blocked_reason,
                content_type=cached_ct,
                extracted_text=scanned,
                upload_images=upload_images,
                scan_guard=scan_guard,
            )
            if ok:
                mark_duplicate_event(domain, dedupe_key)
        return True, msg, ""

    clean_log = f"{tag} {file_label} — Allowed"
    dedupe_key = f"upload-send-allowed|{file_label}"
    if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
        print(f"[UnifAI Proxy] FILE SEND ALLOWED | {client_ip} → {host} | {clean_log}")
        ok = post_upload_intercept(
            platform=platform,
            prompt=clean_log,
            client_ip=client_ip,
            domain=domain,
            url=url,
            method=method,
            file_name=file_label,
            is_blocked=False,
            content_type=cached_ct,
            extracted_text=scanned,
            upload_images=upload_images,
            scan_guard=scan_guard,
        )
        if ok:
            mark_duplicate_event(domain, dedupe_key)
        else:
            print(f"[UnifAI Proxy WARNING] Allowed file log failed to post | {file_label}")
    return False, "", ""


def enforce_file_send_policy(
    *,
    platform: str,
    domain: str,
    host: str,
    client_ip: str,
    url: str,
    method: str,
    raw_text: str,
    content_type: str = "",
    file_name_hint: str = "",
    path: str = "",
) -> tuple[bool, str, str, int]:
    """
    On chat Send with a real attached file (any monitored AI domain):
      - Block Upload ON  → block on Send only (file may attach in UI first)
      - Block Upload OFF → extract PDF/image/Office/voice text → Guard Rules
          BLOCK        → block Send
          REDACT       → log Redacted, allow Send (+ chat notice when possible)
          no match     → Allowed

    Returns (should_block, block_message, redact_notice, files_processed).
    """
    has_attach = (
        chat_carries_attachment(raw_text)
        or chatgpt_carries_file(raw_text)
        or bool((file_name_hint or "").strip())
        or copilot_carries_binary_attach(raw_text)
    )
    cached_list = take_all_cached_uploads_for_send(domain, raw_text, allow_latest=False)
    if not cached_list and has_attach:
        cached_list = take_all_cached_uploads_for_send(domain, raw_text, allow_latest=True)
    if not cached_list and is_chat_path(path or "", host, raw_text or ""):
        cached_list = take_recent_confident_caches_for_send(domain)

    if not has_attach and not cached_list:
        return False, "", "", 0

    if not cached_list and has_attach:
        inline_bytes, inline_ct, inline_name = extract_inline_attachment_bytes(raw_text or "")
        if inline_bytes:
            cached_list = [{
                "file_name": inline_name or "attachment",
                "content_type": inline_ct or content_type,
                "raw_bytes": inline_bytes,
                "ts": time.time(),
            }]

    if not cached_list:
        return False, "", "", 0

    # One log row per unique filename on a single Send (ChatGPT may match the same cache twice).
    deduped: list[dict] = []
    seen_names: set[str] = set()
    for entry in cached_list:
        name_key = ((entry.get("file_name") or "").strip().lower() or f"__{id(entry)}")
        if name_key in seen_names:
            continue
        seen_names.add(name_key)
        deduped.append(entry)
    cached_list = deduped

    get_control_settings()
    should_block = False
    block_msg = ""
    redact_notice = ""
    hint = (file_name_hint or "").strip()
    processed = 0
    for i, cached in enumerate(cached_list):
        per_hint = (cached.get("file_name") or "").strip() or (hint if i == 0 else "")
        sb, msg, rn = _process_one_cached_file_on_send(
            cached=cached,
            platform=platform,
            domain=domain,
            host=host,
            client_ip=client_ip,
            url=url,
            method=method,
            raw_text=raw_text,
            content_type=content_type,
            file_name_hint=per_hint,
            has_attach=has_attach,
        )
        processed += 1
        if sb:
            should_block = True
            block_msg = msg or block_msg
        if rn:
            redact_notice = rn
    return should_block, block_msg, redact_notice, processed


def _upload_log_tag(file_name: str = "", content_type: str = "", raw_bytes: bytes = b"") -> str:
    """Prompt Log prefix: VOICE vs FILE."""
    if _looks_like_audio(raw_bytes or b"", content_type, file_name):
        return "[VOICE UPLOAD]"
    fn = (file_name or "").lower()
    if fn.endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".opus", ".wma")):
        return "[VOICE UPLOAD]"
    return "[FILE UPLOAD]"


def post_upload_intercept(
    *,
    platform: str,
    prompt: str,
    client_ip: str,
    domain: str,
    url: str,
    method: str,
    file_name: str = "",
    is_blocked: bool = False,
    blocked_reason: str = "",
    raw_bytes: bytes | None = None,
    content_type: str = "",
    extracted_text: str = "",
    upload_images: list[str] | None = None,
    scan_guard: dict | None = None,
) -> bool:
    """Log file event on Send — filename + extracted text in metadata only (no file storage)."""
    metadata = {
        "domain": domain,
        "url": url,
        "method": method,
        "is_blocked": bool(is_blocked),
        "upload_scan": True,
        "file_name": file_name or "attachment",
        "agent_id": UNIFAI_AGENT_ID,
        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
    }
    if scan_guard:
        metadata.update(scan_guard)
    if blocked_reason:
        metadata["blocked_reason"] = blocked_reason
    ext = (extracted_text or "").strip()
    if ext:
        metadata["extracted_text"] = ext[:50_000]
    if upload_images:
        metadata["upload_images"] = upload_images[:10]

    safe_name = (file_name or "attachment").replace('"', "")
    ctype = (content_type or "application/octet-stream").strip() or "application/octet-stream"
    try:
        boundary = f"----UnifAI{int(time.time() * 1000)}"
        parts: list[bytes] = []

        def add_field(name: str, value: str) -> None:
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode("utf-8")
            )

        add_field("platform", platform)
        add_field("prompt", prompt)
        add_field("client_ip", client_ip)
        add_field("agent_id", UNIFAI_AGENT_ID or "")
        add_field("agent_hostname", UNIFAI_AGENT_HOSTNAME or "")
        add_field("file_name", safe_name)
        add_field("content_type", ctype)
        add_field("metadata", json.dumps(metadata))
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)
        req = urllib.request.Request(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept-file",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            if 200 <= getattr(resp, "status", 200) < 300:
                return True
    except Exception as e:
        print(f"[UnifAI Proxy WARNING] intercept-file failed, falling back to JSON: {e}")

    try:
        payload_json = json.dumps({
            "platform": platform,
            "prompt": prompt,
            "client_ip": client_ip,
            "agent_id": UNIFAI_AGENT_ID,
            "agent_hostname": UNIFAI_AGENT_HOSTNAME,
            "upload_images": upload_images or [],
            "metadata": metadata,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
            data=payload_json,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4) as resp:
            return 200 <= getattr(resp, "status", 200) < 300
    except Exception as e:
        print(f"[UnifAI Proxy WARNING] upload intercept JSON failed: {e}")
        return False


def _extract_pdf_pypdf(data: bytes) -> str:
    """PDF text via pypdf library."""
    if not data:
        return ""
    if b"%PDF" not in data[:1024] and not data.startswith(b"%PDF"):
        start = data.find(b"%PDF")
        if start < 0:
            return ""
        data = data[start:]
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=False)
        parts: list[str] = []
        for page in reader.pages[:50]:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                parts.append(t)
        return "\n".join(parts).strip()[:200_000]
    except Exception:
        return ""


def _extract_pdf_regex(data: bytes) -> str:
    """PDF text via regex / printable runs (no pypdf)."""
    if not data:
        return ""
    if b"%PDF" not in data[:1024] and not data.startswith(b"%PDF"):
        start = data.find(b"%PDF")
        if start < 0:
            return ""
        data = data[start:]
    try:
        raw = data.decode("latin-1", errors="ignore")
    except Exception:
        return ""
    chunks = re.findall(r"\((?:\\.|[^\\)]){3,}\)|\[[^\]]{3,}\]", raw)
    texts = []
    for c in chunks[:5000]:
        s = c.strip("()[]")
        s = s.replace("\\n", "\n").replace("\\r", "").replace("\\t", "\t")
        s = re.sub(r"\\[0-9]{3}", " ", s)
        s = re.sub(r"[^\x09\x0a\x0d\x20-\x7e\u00a0-\uffff]+", " ", s)
        if len(s.strip()) >= 3:
            texts.append(s.strip())
    for m in re.finditer(r"[ -~]{12,}", raw):
        texts.append(m.group(0))
    return "\n".join(texts)[:200_000]


def _normalize_pdf_bytes(data: bytes) -> bytes:
    """Return PDF payload bytes (direct or embedded in wrapper)."""
    if not data:
        return b""
    if data.startswith(b"%PDF-"):
        return data
    if b"%PDF" in data[:1024]:
        start = data.find(b"%PDF")
        if start >= 0:
            return data[start:]
    start = data.find(b"%PDF-")
    if start >= 0:
        return data[start:]
    return data


def _pdf_text_sufficient(text: str, min_chars: int = 40) -> bool:
    """True when PDF text layer looks usable (not empty/garbage)."""
    if not text:
        return False
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) < min_chars:
        return False
    printable = sum(1 for ch in compact if ch.isprintable())
    return printable / max(1, len(compact)) >= 0.85


def _extract_pdf_embedded_images_ocr(data: bytes, max_images: int = 10) -> str:
    """OCR embedded raster images inside a PDF (common for scanned documents)."""
    parts: list[str] = []
    for b64 in _extract_pdf_images(data, max_images=max_images):
        try:
            raw = base64.b64decode(b64)
        except Exception:
            continue
        t = _extract_image_windows_ocr(raw)
        if not (t or "").strip():
            t = _extract_image_tesseract(raw)
        if (t or "").strip():
            parts.append(t.strip())
    return "\n\n".join(parts)


def _extract_pdf_pymupdf_ocr(data: bytes, max_pages: int = 10) -> str:
    """Render PDF pages to images and OCR (scanned PDFs without a text layer)."""
    data = _normalize_pdf_bytes(data)
    if not data:
        return ""
    try:
        import fitz  # pymupdf
    except ImportError:
        return ""
    parts: list[str] = []
    doc = None
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            try:
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
                png = pix.tobytes("png")
            except Exception:
                continue
            t = _extract_image_windows_ocr(png)
            if not (t or "").strip():
                t = _extract_image_tesseract(png)
            if (t or "").strip():
                parts.append(t.strip())
    except Exception as e:
        print(f"[UnifAI Proxy] PDF page OCR failed (allowed): {e}")
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass
    return "\n\n".join(parts)


def _extract_pdf_ocr(data: bytes, max_pages: int = 10) -> str:
    """OCR fallback for scanned / low-text PDFs."""
    data = _normalize_pdf_bytes(data)
    if not data:
        return ""
    embedded = _extract_pdf_embedded_images_ocr(data, max_images=max_pages)
    embedded_compact = re.sub(r"\s+", "", embedded or "")
    if len(embedded_compact) >= 16:
        return embedded[:200_000]
    rendered = _extract_pdf_pymupdf_ocr(data, max_pages=max_pages)
    if rendered and embedded:
        return (embedded + "\n\n" + rendered)[:200_000]
    return (rendered or embedded or "")[:200_000]


def _extract_pdf_text_smart(data: bytes) -> str:
    """
    PDF text: fast text-layer extract first; OCR only when text layer is missing/weak.
    """
    data = _normalize_pdf_bytes(data)
    if not data:
        return ""
    text = _extract_pdf_pypdf(data)
    if _pdf_text_sufficient(text):
        return text[:200_000]
    regex_t = _extract_pdf_regex(data)
    if _pdf_text_sufficient(regex_t):
        return regex_t[:200_000]
    ocr_t = _extract_pdf_ocr(data)
    if ocr_t.strip():
        print(f"[UnifAI Proxy] PDF OCR extracted {len(ocr_t.strip())} chars (scanned/low-text PDF)")
        return ocr_t[:200_000]
    return (text or regex_t or "")[:200_000]


def _extract_pdf_images(data: bytes, max_images: int = 10) -> list[str]:
    """Extract embedded images from PDF pages as base64 strings (in-memory only)."""
    if not data:
        return []
    if b"%PDF" not in data[:1024] and not data.startswith(b"%PDF"):
        start = data.find(b"%PDF")
        if start < 0:
            return []
        data = data[start:]
    out: list[str] = []
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=False)
        for page in reader.pages[:20]:
            if len(out) >= max_images:
                break
            images = getattr(page, "images", None)
            if not images:
                continue
            for img in images:
                if len(out) >= max_images:
                    break
                raw = getattr(img, "data", None)
                if raw and len(raw) >= 64:
                    out.append(base64.b64encode(raw).decode("ascii"))
    except Exception as e:
        print(f"[UnifAI Proxy] pdf image extract failed (allowed): {e}")
    return out


def _extract_office_images(data: bytes, max_images: int = 10) -> list[str]:
    """Extract embedded images from docx/xlsx/pptx for LLaVA vision rules."""
    zdata = _office_zip_bytes(data)
    if not zdata:
        return []
    out: list[str] = []
    image_ext = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            for name in zf.namelist():
                if len(out) >= max_images:
                    break
                low = name.lower()
                if not (
                    low.startswith("word/media/")
                    or low.startswith("xl/media/")
                    or low.startswith("ppt/media/")
                ):
                    continue
                if not any(low.endswith(ext) for ext in image_ext):
                    continue
                raw = zf.read(name)
                if raw and len(raw) >= 64:
                    out.append(base64.b64encode(raw).decode("ascii"))
    except Exception as e:
        print(f"[UnifAI Proxy] office image extract failed (allowed): {e}")
    return out


def _upload_images_for_vision(raw_bytes: bytes, content_type: str = "", file_name: str = "", max_images: int = 10) -> list[str]:
    """Build base64 image list from an upload for LLaVA vision rules."""
    if not raw_bytes:
        return []
    kind = _classify_upload_kind(raw_bytes, content_type, file_name)
    if kind == "image":
        return [base64.b64encode(raw_bytes).decode("ascii")]
    if kind == "pdf":
        return _extract_pdf_images(raw_bytes, max_images=max_images)
    if kind in ("docx", "xlsx", "pptx"):
        return _extract_office_images(raw_bytes, max_images=max_images)
    return []


def _extract_pdf_text(data: bytes) -> str:
    """Extract readable text from PDF (text layer first, then OCR for scanned PDFs)."""
    return _extract_pdf_text_smart(data)


def _xml_local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _office_zip_bytes(data: bytes) -> bytes | None:
    """Return ZIP payload for OOXML (docx/xlsx/pptx), including multipart-wrapped bodies."""
    if not data:
        return None
    if data[:2] == b"PK":
        return data
    # Multipart / prefix noise: locate ZIP local-file header
    idx = data.find(b"PK\x03\x04")
    if idx >= 0 and idx < len(data) - 30:
        return data[idx:]
    return None


def _extract_docx_text(data: bytes) -> str:
    """Extract paragraph text from .docx (OOXML ZIP) without third-party libs."""
    zdata = _office_zip_bytes(data)
    if not zdata:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            if "word/document.xml" not in zf.namelist():
                return ""
            xml = zf.read("word/document.xml")
    except Exception:
        return ""
    try:
        root = ET.fromstring(xml)
    except Exception:
        return ""
    parts: list[str] = []
    for el in root.iter():
        if _xml_local(el.tag) != "p":
            continue
        bits: list[str] = []
        for node in el.iter():
            loc = _xml_local(node.tag)
            if loc == "t" and node.text:
                bits.append(node.text)
            elif loc == "tab":
                bits.append("\t")
            elif loc in ("br", "cr"):
                bits.append("\n")
        line = "".join(bits).strip()
        if line:
            parts.append(line)
    if not parts:
        for el in root.iter():
            if _xml_local(el.tag) == "t" and (el.text or "").strip():
                parts.append(el.text.strip())
    joined = "\n".join(parts).strip()
    return joined[:200_000]


def _extract_xlsx_text(data: bytes) -> str:
    """Extract cell values from .xlsx (shared strings + sheet cells)."""
    zdata = _office_zip_bytes(data)
    if not zdata:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            names = zf.namelist()
            if not any(n.startswith("xl/") for n in names):
                return ""
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                try:
                    ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                    for si in ss_root:
                        if _xml_local(si.tag) != "si":
                            continue
                        texts = []
                        for node in si.iter():
                            if _xml_local(node.tag) == "t" and node.text:
                                texts.append(node.text)
                        shared.append("".join(texts))
                except Exception:
                    shared = []

            sheet_names = sorted(
                n for n in names if re.match(r"xl/worksheets/sheet\d+\.xml$", n)
            )[:20]
            values: list[str] = []
            for sheet in sheet_names:
                try:
                    root = ET.fromstring(zf.read(sheet))
                except Exception:
                    continue
                for el in root.iter():
                    if _xml_local(el.tag) != "c":
                        continue
                    cell_type = (el.attrib.get("t") or "").lower()
                    v_el = None
                    is_el = None
                    for child in el:
                        loc = _xml_local(child.tag)
                        if loc == "v":
                            v_el = child
                        elif loc == "is":
                            is_el = child
                    if cell_type == "s" and v_el is not None and (v_el.text or "").strip() != "":
                        try:
                            idx = int(v_el.text)
                            if 0 <= idx < len(shared) and shared[idx].strip():
                                values.append(shared[idx].strip())
                        except Exception:
                            pass
                    elif cell_type == "inlineStr" and is_el is not None:
                        texts = []
                        for node in is_el.iter():
                            if _xml_local(node.tag) == "t" and node.text:
                                texts.append(node.text)
                        s = "".join(texts).strip()
                        if s:
                            values.append(s)
                    elif v_el is not None and (v_el.text or "").strip():
                        # numbers / booleans / formulas cached value
                        values.append(v_el.text.strip())
            # Also dump shared strings if sheets yielded little (rare sheet layouts)
            if len(values) < 3 and shared:
                values.extend(s.strip() for s in shared if s and s.strip())
    except Exception:
        return ""
    # Dedupe while preserving order (repeated headers OK once)
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
        if len(out) >= 20_000:
            break
    return "\n".join(out)[:200_000]


def _extract_pptx_text(data: bytes) -> str:
    """Extract text from .pptx slide XMLs."""
    zdata = _office_zip_bytes(data)
    if not zdata:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            slides = sorted(n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n))[:30]
            if not slides:
                return ""
            parts: list[str] = []
            for name in slides:
                try:
                    root = ET.fromstring(zf.read(name))
                except Exception:
                    continue
                for el in root.iter():
                    if _xml_local(el.tag) == "t" and (el.text or "").strip():
                        parts.append(el.text.strip())
    except Exception:
        return ""
    return "\n".join(parts)[:200_000]


def _looks_like_docx(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if "wordprocessingml" in ct or fn.endswith(".docx"):
        return True
    zdata = _office_zip_bytes(data)
    if not zdata:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            return "word/document.xml" in zf.namelist()
    except Exception:
        return False


def _looks_like_xlsx(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if "spreadsheetml" in ct or fn.endswith(".xlsx") or fn.endswith(".xlsm"):
        return True
    zdata = _office_zip_bytes(data)
    if not zdata:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            names = zf.namelist()
            return any(n.startswith("xl/") for n in names)
    except Exception:
        return False


def _looks_like_pptx(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if "presentationml" in ct or fn.endswith(".pptx"):
        return True
    zdata = _office_zip_bytes(data)
    if not zdata:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            return any(n.startswith("ppt/slides/") for n in zf.namelist())
    except Exception:
        return False


def _extract_office_text(data: bytes, content_type: str = "", file_name: str = "") -> str:
    """Best-effort OOXML text (Word / Excel / PowerPoint)."""
    if _looks_like_docx(data, content_type, file_name):
        t = _extract_docx_text(data)
        if t:
            return t
    if _looks_like_xlsx(data, content_type, file_name):
        t = _extract_xlsx_text(data)
        if t:
            return t
    if _looks_like_pptx(data, content_type, file_name):
        t = _extract_pptx_text(data)
        if t:
            return t
    # Unknown ZIP: try all
    if data[:2] == b"PK" or b"PK\x03\x04" in data[:8192]:
        for fn in (_extract_docx_text, _extract_xlsx_text, _extract_pptx_text):
            try:
                t = fn(data)
            except Exception:
                t = ""
            if t:
                return t
    return ""


def _looks_like_image(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if ct.startswith("image/"):
        return True
    if any(fn.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")):
        return True
    if not data:
        return False
    if data.startswith(b"\x89PNG\r\n\x1a\n") or data.startswith(b"\xff\xd8\xff") or data.startswith(b"GIF8"):
        return True
    if data.startswith(b"BM") and len(data) > 30:
        return True
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return True
    return False


def _run_async(coro):
    """Run a coroutine even if mitmproxy already has an event loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    result: dict = {}
    exc: dict = {}

    def runner() -> None:
        try:
            result["v"] = asyncio.run(coro)
        except Exception as e:
            exc["e"] = e

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    t.join(timeout=35)
    if t.is_alive():
        raise TimeoutError("ocr timed out")
    if "e" in exc:
        raise exc["e"]
    return result.get("v")


async def _windows_ocr_pil(img) -> str:
    """Windows.Media.Ocr (built into Windows 10+) — no Tesseract install required."""
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage.streams import DataWriter

    if img.mode != "RGBA":
        img = img.convert("RGBA")
    # Cap size for OCR latency / memory
    max_side = 2000
    w, h = img.size
    if w < 8 or h < 8:
        return ""
    if max(w, h) > max_side:
        scale = max_side / float(max(w, h))
        img = img.resize((max(8, int(w * scale)), max(8, int(h * scale))))

    engine = OcrEngine.try_create_from_user_profile_languages()
    if engine is None:
        for tag in ("en", "en-US", "en-GB"):
            try:
                if OcrEngine.is_language_supported(Language(tag)):
                    engine = OcrEngine.try_create_from_language(Language(tag))
                    if engine is not None:
                        break
            except Exception:
                continue
    if engine is None:
        return ""

    writer = DataWriter()
    writer.write_bytes(bytearray(img.tobytes()))
    bitmap = SoftwareBitmap.create_copy_from_buffer(
        writer.detach_buffer(),
        BitmapPixelFormat.RGBA8,
        img.width,
        img.height,
    )
    result = await engine.recognize_async(bitmap)
    text = (getattr(result, "text", None) or "").strip()
    return text


def _extract_image_windows_ocr(data: bytes) -> str:
    """OCR via Windows.Media.Ocr (built into Windows 10+)."""
    if not data or len(data) < 32:
        return ""
    if len(data) > 15 * 1024 * 1024:
        data = data[: 15 * 1024 * 1024]
    try:
        from PIL import Image
    except Exception:
        return ""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        img = img.convert("RGB")
    except Exception:
        return ""
    try:
        text = _run_async(_windows_ocr_pil(img)) or ""
        return str(text).strip()[:200_000]
    except Exception as e:
        print(f"[UnifAI Proxy] Windows OCR unavailable: {e}")
        return ""


def _extract_image_tesseract(data: bytes) -> str:
    """OCR via pytesseract when installed on the laptop."""
    if not data or len(data) < 32:
        return ""
    try:
        from PIL import Image
        import pytesseract  # type: ignore
    except Exception:
        return ""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        if getattr(img, "n_frames", 1) > 1:
            img.seek(0)
        img = img.convert("RGB")
        text = (pytesseract.image_to_string(img) or "").strip()
        return text[:200_000]
    except Exception:
        return ""


def _extract_image_text(data: bytes) -> str:
    """
    OCR text from image uploads (PNG/JPEG/WebP/GIF/BMP) so Guard Rules can scan
    text that appears inside screenshots / photos of documents.
    Primary: Windows Media OCR. Optional fallback: pytesseract if installed.
    """
    t = _extract_image_windows_ocr(data)
    if t:
        return t
    return _extract_image_tesseract(data)


def _looks_like_audio(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    """True for voice notes / audio file uploads (wav/mp3/m4a/ogg/webm/aac/flac)."""
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if ct.startswith("audio/") or "audio" in ct.split(";")[0]:
        return True
    if fn.endswith((".wav", ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".webm", ".flac", ".wma")):
        return True
    if not data or len(data) < 12:
        return False
    head = data[:16]
    if head[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return True
    if head[:3] == b"ID3" or head[:2] == b"\xff\xfb" or head[:2] == b"\xff\xf3":
        return True  # mp3
    if head[:4] == b"fLaC" or head[:4] == b"OggS":
        return True
    if head[4:8] == b"ftyp":  # m4a/mp4 container
        return True
    return False


def _extract_transcript_fields_from_json(raw_text: str) -> str:
    """Many AI sites STT locally and send transcript JSON with the voice blob."""
    if not raw_text or len(raw_text) < 8:
        return ""
    low = raw_text.lower()
    if not any(
        k in low
        for k in (
            "transcript", "transcription", "spoken", "voice", "dictation",
            "asr", "speech_to_text", "speechtext",
        )
    ):
        return ""
    try:
        data = json.loads(raw_text)
    except Exception:
        # Regex fallback for nested / escaped transcripts
        parts = []
        for pat in (
            r'"(?:transcript|transcription|spoken_text|speech_text|dictation|asr_text)"\s*:\s*"((?:\\.|[^"\\])*)"',
            r'"(?:transcript|transcription)"\s*:\s*"((?:\\.|[^"\\])*)"',
        ):
            for m in re.finditer(pat, raw_text, re.I):
                try:
                    val = json.loads(f'"{m.group(1)}"')
                except Exception:
                    val = m.group(1).replace("\\n", "\n").replace('\\"', '"')
                val = (val or "").strip()
                if val and looks_like_user_prompt(val):
                    parts.append(val)
        return "\n".join(parts)[:200_000]

    found: list[str] = []

    def walk(obj, depth=0):
        if depth > 8 or len(found) >= 5:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                kl = str(k).lower()
                if kl in (
                    "transcript", "transcription", "spoken_text", "speech_text",
                    "dictation", "asr_text", "voice_text", "recognized_text",
                ) and isinstance(v, str) and v.strip():
                    if looks_like_user_prompt(v.strip()):
                        found.append(v.strip())
                else:
                    walk(v, depth + 1)
        elif isinstance(obj, list):
            for item in obj[:40]:
                walk(item, depth + 1)

    walk(data)
    return "\n".join(found)[:200_000]


def _audio_to_wav_path(data: bytes, content_type: str = "", file_name: str = "") -> str | None:
    """Write audio to a temp path; convert to WAV when possible for Windows STT."""
    import tempfile
    import os

    if not data or len(data) < 64:
        return None
    if len(data) > 25 * 1024 * 1024:
        data = data[: 25 * 1024 * 1024]

    fn = (file_name or "").lower()
    ct = (content_type or "").lower()
    suffix = ".bin"
    for ext in (".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma", ".opus"):
        if fn.endswith(ext) or ext.replace(".", "") in ct:
            suffix = ext
            break
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        suffix = ".wav"

    fd, path = tempfile.mkstemp(prefix="unifai_voice_", suffix=suffix)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)

    if path.lower().endswith(".wav"):
        return path

    # Prefer ffmpeg on PATH (common on IT images) to produce PCM WAV for System.Speech
    wav_path = path + ".wav"
    try:
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            import subprocess
            proc = subprocess.run(
                [ffmpeg, "-y", "-i", path, "-ac", "1", "-ar", "16000", wav_path],
                capture_output=True,
                timeout=45,
            )
            if proc.returncode == 0 and os.path.isfile(wav_path) and os.path.getsize(wav_path) > 64:
                try:
                    os.remove(path)
                except Exception:
                    pass
                return wav_path
    except Exception as e:
        print(f"[UnifAI Proxy] ffmpeg voice convert skipped: {e}")

    # Optional pydub (if installed + ffmpeg)
    try:
        from pydub import AudioSegment  # type: ignore
        fmt = suffix.lstrip(".")
        if fmt == "mp3":
            seg = AudioSegment.from_mp3(path)
        elif fmt in ("ogg", "oga", "opus"):
            seg = AudioSegment.from_ogg(path)
        elif fmt == "wav":
            seg = AudioSegment.from_wav(path)
        else:
            seg = AudioSegment.from_file(path)
        seg = seg.set_channels(1).set_frame_rate(16000)
        seg.export(wav_path, format="wav")
        if os.path.isfile(wav_path) and os.path.getsize(wav_path) > 64:
            try:
                os.remove(path)
            except Exception:
                pass
            return wav_path
    except Exception:
        pass

    return path  # may still be useful for whisper


def _windows_system_speech_stt(wav_path: str) -> str:
    """Offline STT via Windows System.Speech (dictation grammar) for WAV files."""
    import subprocess
    import tempfile
    import os

    if not wav_path or not os.path.isfile(wav_path):
        return ""
    # Escape for PowerShell single-quoted string
    safe = wav_path.replace("'", "''")
    ps = f"""
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
try {{
  $engine.SetInputToWaveFile('{safe}')
  $engine.LoadGrammar((New-Object System.Speech.Recognition.DictationGrammar))
  $result = $engine.Recognize()
  if ($result -ne $null) {{ $result.Text }}
}} finally {{
  $engine.Dispose()
}}
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True,
            timeout=60,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        text = (proc.stdout or "").strip()
        if text and looks_like_user_prompt(text):
            return text[:200_000]
    except Exception as e:
        print(f"[UnifAI Proxy] Windows System.Speech STT failed: {e}")
    return ""


def _whisper_stt(path: str) -> str:
    """Optional local Whisper (openai-whisper or faster-whisper) if installed on the machine."""
    if not path:
        return ""
    # faster-whisper
    try:
        from faster_whisper import WhisperModel  # type: ignore

        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _info = model.transcribe(path, beam_size=1)
        parts = [s.text.strip() for s in segments if getattr(s, "text", None)]
        text = " ".join(parts).strip()
        if text:
            return text[:200_000]
    except Exception:
        pass
    # openai-whisper
    try:
        import whisper  # type: ignore

        model = whisper.load_model("tiny")
        result = model.transcribe(path)
        text = (result.get("text") or "").strip()
        if text:
            return text[:200_000]
    except Exception:
        pass
    # speech_recognition + whisper backend
    try:
        import speech_recognition as sr  # type: ignore

        r = sr.Recognizer()
        with sr.AudioFile(path) as source:
            audio = r.record(source)
        if hasattr(r, "recognize_whisper"):
            text = (r.recognize_whisper(audio, model="tiny") or "").strip()
            if text:
                return text[:200_000]
    except Exception:
        pass
    return ""


def _extract_audio_text(data: bytes, content_type: str = "", file_name: str = "") -> str:
    """
    Speech-to-text for voice / audio uploads so Guard Rules can scan spoken content.
    Order: site-provided transcript fields are handled separately; here we STT the bytes.
    1) Windows System.Speech on WAV (built-in)
    2) Optional Whisper / faster-whisper if installed
    """
    import os

    if not data or len(data) < 64:
        return ""
    path = None
    try:
        path = _audio_to_wav_path(data, content_type, file_name)
        if not path:
            return ""
        # Prefer WAV for System.Speech
        wav = path if path.lower().endswith(".wav") else None
        if wav:
            text = _windows_system_speech_stt(wav)
            if text:
                print(f"[UnifAI Proxy] Voice STT (Windows) | {len(text)} chars | {file_name or 'audio'}")
                return text
        text = _whisper_stt(path)
        if text:
            print(f"[UnifAI Proxy] Voice STT (Whisper) | {len(text)} chars | {file_name or 'audio'}")
            return text
        if wav is None and path.lower().endswith((".wav",)):
            text = _windows_system_speech_stt(path)
            if text:
                return text
    except Exception as e:
        print(f"[UnifAI Proxy] Voice STT error: {e}")
    finally:
        if path:
            try:
                os.remove(path)
            except Exception:
                pass
            try:
                if path.endswith(".wav") is False and os.path.isfile(path + ".wav"):
                    os.remove(path + ".wav")
            except Exception:
                pass
    return ""


def _extract_plain_text_bytes(data: bytes) -> str:
    if not data:
        return ""
    # Skip obvious binary without text
    if data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff") or data.startswith(b"GIF8"):
        return ""
    if data[:2] == b"PK" or data[:5] == b"%PDF-":
        return ""
    try:
        text = data.decode("utf-8")
    except Exception:
        try:
            text = data.decode("latin-1", errors="ignore")
        except Exception:
            return ""
    # Heuristic: enough printable ratio
    if not text or len(text) < 8:
        return ""
    printable = sum(1 for ch in text if ch.isprintable() or ch in "\r\n\t")
    if printable / max(1, len(text)) < 0.7:
        return ""
    return text[:200_000]


def _classify_upload_kind(data: bytes, content_type: str = "", file_name: str = "") -> str:
    """Classify upload bytes so we use one extractor per file type (not all at once)."""
    if not data:
        return "unknown"
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()

    if "pdf" in ct or fn.endswith(".pdf") or data[:5] == b"%PDF-" or b"%PDF-" in data[:4096]:
        return "pdf"
    if _looks_like_image(data, content_type, file_name):
        return "image"
    if _looks_like_audio(data, content_type, file_name):
        return "audio"
    if _looks_like_docx(data, content_type, file_name):
        return "docx"
    if _looks_like_xlsx(data, content_type, file_name):
        return "xlsx"
    if _looks_like_pptx(data, content_type, file_name):
        return "pptx"
    if fn.endswith((".txt", ".csv", ".json", ".md", ".log")) or any(
        x in ct for x in ("text/", "csv", "json")
    ):
        return "plain"
    if data[:2] == b"PK" or b"PK\x03\x04" in data[:8192]:
        # Unknown OOXML zip — sniff inner layout
        zdata = _office_zip_bytes(data)
        if zdata:
            try:
                with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
                    names = zf.namelist()
                    if "word/document.xml" in names:
                        return "docx"
                    if any(n.startswith("xl/") for n in names):
                        return "xlsx"
                    if any(n.startswith("ppt/slides/") for n in names):
                        return "pptx"
            except Exception:
                pass
        return "zip"
    return "unknown"


def _try_file_extract_chain(
    data: bytes,
    content_type: str,
    file_name: str,
    kind: str,
    steps: list[tuple[str, callable]],
) -> str:
    """Run extractors in order; first non-empty result wins. Logs fallback usage."""
    for i, (label, fn) in enumerate(steps):
        try:
            t = (fn() or "").strip()
            if t:
                if i > 0:
                    print(
                        f"[UnifAI Proxy] file extract fallback OK ({label}) | "
                        f"{file_name or kind} | {len(t)} chars"
                    )
                return t[:200_000]
        except Exception as e:
            print(f"[UnifAI Proxy] file extract try failed ({label}): {e}")
    return ""


def _office_extract_steps(data: bytes, primary: str) -> list[tuple[str, callable]]:
    """Office OOXML: primary type first, then other Office parsers, then generic ZIP."""
    order = ["docx", "xlsx", "pptx"]
    if primary in order:
        order.remove(primary)
        order.insert(0, primary)
    fns = {
        "docx": ("docx-xml", lambda: _extract_docx_text(data)),
        "xlsx": ("xlsx-xml", lambda: _extract_xlsx_text(data)),
        "pptx": ("pptx-xml", lambda: _extract_pptx_text(data)),
    }
    steps = [fns[k] for k in order if k in fns]
    steps.append(("office-zip-all", lambda: _extract_office_text(data, content_type="", file_name="")))
    return steps


def _extract_text_from_file_bytes(data: bytes, content_type: str = "", file_name: str = "") -> str:
    """Extract scannable text — primary method per file type, then fallbacks until one succeeds."""
    if not data:
        return ""
    kind = _classify_upload_kind(data, content_type, file_name)
    ct = content_type
    fn = file_name
    try:
        if kind == "pdf":
            return _try_file_extract_chain(data, ct, fn, kind, [
                ("pdf-smart", lambda: _extract_pdf_text_smart(data)),
                ("pdf-pypdf", lambda: _extract_pdf_pypdf(data)),
                ("pdf-ocr", lambda: _extract_pdf_ocr(data)),
                ("pdf-regex", lambda: _extract_pdf_regex(data)),
                ("plain-decode", lambda: _extract_plain_text_bytes(data)),
            ])

        if kind == "docx":
            steps = _office_extract_steps(data, "docx")
            steps.append(("plain-decode", lambda: _extract_plain_text_bytes(data)))
            return _try_file_extract_chain(data, ct, fn, kind, steps)

        if kind == "xlsx":
            steps = _office_extract_steps(data, "xlsx")
            steps.append(("plain-decode", lambda: _extract_plain_text_bytes(data)))
            return _try_file_extract_chain(data, ct, fn, kind, steps)

        if kind == "pptx":
            steps = _office_extract_steps(data, "pptx")
            steps.append(("plain-decode", lambda: _extract_plain_text_bytes(data)))
            return _try_file_extract_chain(data, ct, fn, kind, steps)

        if kind == "image":
            return _try_file_extract_chain(data, ct, fn, kind, [
                ("image-windows-ocr", lambda: _extract_image_windows_ocr(data)),
                ("image-tesseract", lambda: _extract_image_tesseract(data)),
                ("pdf-pypdf", lambda: _extract_pdf_pypdf(data)),
                ("plain-decode", lambda: _extract_plain_text_bytes(data)),
            ])

        if kind == "audio":
            return _try_file_extract_chain(data, ct, fn, kind, [
                ("audio-stt", lambda: _extract_audio_text(data, ct, fn)),
                ("plain-decode", lambda: _extract_plain_text_bytes(data)),
            ])

        if kind == "plain":
            return _try_file_extract_chain(data, ct, fn, kind, [
                ("plain-utf8", lambda: _extract_plain_text_bytes(data)),
                ("pdf-pypdf", lambda: _extract_pdf_pypdf(data)),
                ("docx-xml", lambda: _extract_docx_text(data)),
            ])

        if kind == "zip":
            steps = _office_extract_steps(data, "docx")
            steps.append(("plain-decode", lambda: _extract_plain_text_bytes(data)))
            return _try_file_extract_chain(data, ct, fn, kind, steps)

        # Unknown: try every sensible extractor in order
        return _try_file_extract_chain(data, ct, fn, kind or "unknown", [
            ("pdf-pypdf", lambda: _extract_pdf_pypdf(data)),
            ("pdf-regex", lambda: _extract_pdf_regex(data)),
            ("docx-xml", lambda: _extract_docx_text(data)),
            ("xlsx-xml", lambda: _extract_xlsx_text(data)),
            ("pptx-xml", lambda: _extract_pptx_text(data)),
            ("image-windows-ocr", lambda: _extract_image_windows_ocr(data)),
            ("image-tesseract", lambda: _extract_image_tesseract(data)),
            ("audio-stt", lambda: _extract_audio_text(data, ct, fn)),
            ("plain-decode", lambda: _extract_plain_text_bytes(data)),
        ])
    except Exception as e:
        print(f"[UnifAI Proxy] file extract ({kind}) failed — allowed: {e}")
    return ""


def extract_upload_text_for_rules(
    raw_bytes: bytes,
    content_type: str = "",
    raw_text: str = "",
    file_name: str = "",
) -> str:
    """
    Pull text from an upload body so Guard Rules can scan file contents
    (PDF, Word, Excel, PowerPoint, image OCR, voice STT, plain text, multipart).
    Uses one extractor per detected file type.
    """
    try:
        parts: list[str] = []
        ct = (content_type or "").lower()
        data = raw_bytes or b""
        fname = (file_name or "").strip()

        # Site often sends STT transcript alongside the voice blob
        transcript = _extract_transcript_fields_from_json(raw_text or "")
        if transcript:
            parts.append(transcript)

        # Prefer clean file bytes from multipart / wrappers when present
        payload, sniffed_ct, sniffed_name = extract_upload_file_payload(data, content_type, fname)
        if payload and len(payload) >= 32:
            t = _extract_text_from_file_bytes(payload, sniffed_ct or content_type, sniffed_name or fname)
            if t:
                parts.append(t)

        # Direct scan of full body (non-multipart or when payload extract missed)
        if not parts or (transcript and len(parts) == 1):
            t = _extract_text_from_file_bytes(data, content_type, fname)
            if t and t not in parts:
                parts.append(t)

        # Multipart islands: one extractor per part by file type
        if "multipart" in ct or b"filename=" in data[:12000] or b"webkitformboundary" in data[:4000].lower():
            for chunk in re.split(rb"\r\n--[^\r\n]+", data):
                if len(chunk) < 20:
                    continue
                body = chunk
                part_name = ""
                if b"\r\n\r\n" in chunk:
                    header, body = chunk.split(b"\r\n\r\n", 1)
                    try:
                        hdr = header.decode("utf-8", errors="ignore")
                    except Exception:
                        hdr = ""
                    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";\r\n]+)"?', hdr, re.I)
                    if m:
                        part_name = m.group(1).strip()
                t = _extract_text_from_file_bytes(body, content_type, part_name or fname)
                if t and len(t) > 8 and t not in parts:
                    parts.append(t)

        # Plain text bodies only — never treat ChatGPT/API JSON metadata as file content.
        if raw_text and len(raw_text) > 20 and not parts:
            stripped = raw_text.lstrip()
            if stripped[:1] not in ("{", "[") and "filename=" not in raw_text[:2000].lower() and raw_text.count("\x00") == 0:
                parts.append(raw_text[:200_000])

        # Deduplicate while preserving order
        seen = set()
        out = []
        for p in parts:
            key = p[:200]
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return "\n\n".join(out)[:250_000]
    except Exception as e:
        print(f"[UnifAI Proxy] extract_upload_text_for_rules failed (allowed): {e}")
        return ""


def match_guard_rules_on_text(text: str) -> tuple[bool, str, str]:
    """
    Apply active Guard Rules to arbitrary text (prompt or file content).
    Returns (matched, rule_name, action).
    """
    if not text or len(text.strip()) < 1:
        return False, "", ""
    rules = get_guard_rules()
    for r in rules:
        try:
            if r["regex"].search(text):
                return True, r.get("name", "Guard Rule"), (r.get("action") or "BLOCK").upper()
        except Exception:
            continue
    return False, "", ""


def extract_perplexity_prompt(content: str) -> str | None:
    """Extract user query from Perplexity /rest/sse, /rest/thread, entrypoint JSON or SSE lines."""
    if not content:
        return None
    text = content.strip()

    # SSE stream chunks: data: {"query_str":"..."}
    if "data:" in text and not text.lstrip().startswith("{"):
        candidates: list[str] = []
        for line in text.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            chunk = line[5:].strip()
            if not chunk or chunk in ("[DONE]", "done"):
                continue
            if chunk.startswith("{"):
                nested = extract_perplexity_prompt(chunk)
                if nested:
                    candidates.append(nested)
        picked = _pick_best_user_text(candidates)
        if picked:
            return picked

    if not text.startswith("{"):
        return None
    try:
        data = json.loads(text)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    def _pick(val) -> str | None:
        if isinstance(val, (str, int, float)):
            got = _clean_prompt_text(str(val))
            if got:
                return got
        return None

    qs = data.get("query_str")
    if isinstance(qs, str) and qs.strip():
        got = _clean_prompt_text(qs)
        if got:
            return got

    for key in (
        "query", "user_query", "last_query", "search_query", "user_message",
        "message", "text", "input", "follow_up_input", "user_text", "dsl_query",
        "q", "prompt", "utterance",
    ):
        got = _pick(data.get(key))
        if got:
            return got

    params = data.get("params")
    if isinstance(params, dict):
        for key in ("query_str", "dsl_query", "query", "user_query", "message", "text"):
            got = _pick(params.get(key))
            if got:
                return got

    for wrapper in ("data", "payload", "body", "request", "entry"):
        inner = data.get(wrapper)
        if isinstance(inner, dict):
            try:
                nested = extract_perplexity_prompt(json.dumps(inner))
            except Exception:
                nested = None
            if nested:
                return nested

    msgs = data.get("messages")
    if isinstance(msgs, list):
        for msg in reversed(msgs):
            if not isinstance(msg, dict):
                continue
            for key in ("query_str", "query", "text", "content", "message", "user_message"):
                got = _pick(msg.get(key))
                if got:
                    return got

    return None


def extract_gemini_prompt(content: str) -> str:
    """
    Extract ONLY the user-typed prompt from Gemini/Bard requests.

    Real chat submits go to BardFrontendService/StreamGenerate or chat RPCs:
      f.req=[null,"[[\\"what is python\\\\n\\",0,null,...], ...]"]
    Background/telemetry batchexecute RPCs (ESY5D, L5adhe, VxUbXb, aPya6c, etc.) are ignored.
    """
    decoded = urllib.parse.unquote(content)
    req_str = decoded
    if "f.req=" in decoded:
        try:
            parsed = urllib.parse.parse_qs(decoded, keep_blank_values=False)
            req_str = parsed.get("f.req", [""])[0]
        except Exception:
            idx = decoded.find("f.req=")
            req_str = decoded[idx + 6:]
            if "&" in req_str:
                req_str = req_str.split("&", 1)[0]
            req_str = urllib.parse.unquote(req_str)

    if not req_str:
        return ""

    def _normalize_prompt(s: str) -> str:
        """Collapse whitespace and unescape JSON escapes."""
        if not s:
            return ""
        if "\\n" in s or "\\t" in s or '\\"' in s or "\\\\" in s:
            s = (
                s.replace("\\\\", "\0")
                .replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\0", "\\")
            )
        return re.sub(r"\s+", " ", s).strip()

    def _is_valid_user_prompt(s: str) -> bool:
        if not s:
            return False
        s = _normalize_prompt(s)
        if not looks_like_user_prompt(s):
            return False
        if _is_ai_chrome_url(s):
            return False
        # Locale / UI language crumbs from Gemini (hl=en-IN → "en"). Keep greetings like "hi".
        if s.lower() in GEMINI_LOCALE_JUNK or re.fullmatch(r"[a-z]{2}-[A-Za-z]{2,3}", s):
            return False
        if re.fullmatch(r"[a-z]{2}-[A-Z]{2,3}", s):
            return False
        if re.fullmatch(r"en", s, re.IGNORECASE):
            return False
        # Reject dot-tokens like "z.fdeb774424ec3df1"
        if re.match(r"^[a-z]\.[a-f0-9]{8,}", s, re.IGNORECASE):
            return False
        # Hex hashes with letters — not digit-only user input
        if " " not in s and re.fullmatch(r"[0-9a-fA-F]{10,64}", s) and re.search(r"[a-fA-F]", s):
            return False
        # Reject tokens starting with c_, r_, v_, rc_, f_, z_, or bare _session ids
        if s.startswith(("c_", "r_", "v_", "rc_", "f_", "z_", "req0_", "_")):
            return False
        low = s.lower()
        if any(bad in low for bad in (
            "bard activity", "generic", "batchexecute", "wrb.fr",
            "assistant.lamda", "bardfrontendservice", "google account",
            "model_metadata", "conversation_turn", "workspace_id", "count=", "&ofs="
        )):
            return False
        return len(s) >= 1

    def _pick_user_prompt(cands: list[str]) -> str:
        good = []
        for raw in cands:
            cand = _normalize_prompt(raw)
            if _is_valid_user_prompt(cand) and not _is_google_wire_blob(cand):
                good.append(cand)
        if not good:
            return ""
        # Prefer real sentences over a leftover token in the same payload.
        good.sort(key=lambda s: (1 if (" " in s or "\n" in s) else 0, len(s)), reverse=True)
        return good[0]

    def _from_stream_inner(inner) -> str:
        """StreamGenerate: typed prompt is ONLY the first [prompt, 0, ...] slot — not locale."""
        if not isinstance(inner, list) or not inner:
            return ""

        cands: list[str] = []
        if len(inner) > 0 and isinstance(inner[0], list):
            first = inner[0]
            if (
                len(first) > 0
                and isinstance(first[0], list)
                and len(first[0]) > 1
                and isinstance(first[0][0], str)
                and first[0][1] == 0
            ):
                cands.append(first[0][0])
            elif len(first) > 1 and isinstance(first[0], str) and first[1] == 0:
                cands.append(first[0])
        return _pick_user_prompt(cands)

    try:
        data = json.loads(req_str)
        # 1. StreamGenerate payload: [null, "<json_string>", ...]
        if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], str):
            try:
                inner = json.loads(data[1])
                got = _from_stream_inner(inner)
                if got:
                    return got
            except Exception:
                pass

        # 2. batchexecute: ONLY check recognized chat RPCs
        if isinstance(data, list):
            for rpc in data:
                item = None
                if isinstance(rpc, list) and rpc and isinstance(rpc[0], list):
                    item = rpc[0]
                elif isinstance(rpc, list) and len(rpc) > 1 and isinstance(rpc[1], str):
                    item = rpc
                if not item or len(item) < 2:
                    continue
                rpc_id = str(item[0])
                if rpc_id not in GEMINI_CHAT_RPCS:
                    continue
                payload_str = item[1]
                if not isinstance(payload_str, str) or payload_str in ("", "[]", "[[]]"):
                    continue
                try:
                    payload = json.loads(payload_str)
                    if isinstance(payload, list):
                        got = _from_stream_inner(payload)
                        if got:
                            return got
                        if len(payload) >= 2 and isinstance(payload[1], str):
                            try:
                                sub = json.loads(payload[1])
                                got = _from_stream_inner(sub)
                                if got:
                                    return got
                            except Exception:
                                pass
                except Exception:
                    continue
    except Exception:
        pass

    # 3. Slot regex for StreamGenerate-shaped prompts.
    # Google rotates batchexecute RPC ids often — do not require a hard-coded id list.
    for pat in (
        r'\[\s*\[\s*"((?:[^"\\]|\\.)+?)"\s*,\s*0\s*,',
        r'\\"((?:[^"\\]|\\.)+?)\\"\s*,\s*0\s*,',
    ):
        m = re.search(pat, req_str)
        if m:
            cand = _normalize_prompt(m.group(1))
            if _is_valid_user_prompt(cand) and not _is_google_wire_blob(cand):
                return cand

    return ""


def _printable_runs(raw: bytes) -> list[str]:
    """Pull UTF-8 / ASCII strings out of protobuf or mixed ChatGPT bodies."""
    if not raw:
        return []
    text = raw.decode("utf-8", errors="ignore")
    chunks: list[str] = []
    for m in re.finditer(r"[\x20-\x7e\u00a0-\uffff]{1,4000}", text):
        s = (m.group(0) or "").strip()
        if s:
            chunks.append(s)
    return chunks


def extract_chatgpt_prompt(text: str, raw: bytes) -> str | None:
    """ChatGPT web: JSON parts, nested author.content, or protobuf string fields."""
    blob = text or ""
    raw_blob = (raw or b"").decode("utf-8", errors="ignore")
    search_blob = blob if len(blob) >= len(raw_blob) else raw_blob
    if not search_blob and blob:
        search_blob = blob

    # Highest confidence: explicit parts[] / input_text from conversation JSON embedded in protobuf.
    parts_got = _extract_chatgpt_parts_prompt(search_blob)
    if parts_got and (chatgpt_carries_file(search_blob) or chat_carries_attachment(search_blob)):
        if _looks_like_document_body_dump(parts_got) or len(parts_got) > 320:
            parts_got = None
    if parts_got:
        return parts_got

    candidates: list[str] = []
    if blob.lstrip().startswith(("{", "[")):
        try:
            got = _extract_from_json(json.loads(blob))
            if got and not _is_chat_metadata_token(got):
                candidates.append(got)
        except Exception:
            pass
    for pat in (
        r'"prompt"\s*:\s*"((?:[^"\\]|\\.)*)"',
    ):
        for m in re.finditer(pat, search_blob):
            cand = _clean_prompt_text(
                m.group(1).encode("utf-8").decode("unicode_escape", errors="ignore")
                if "\\" in m.group(1)
                else m.group(1)
            )
            if cand and not _is_chat_metadata_token(cand):
                candidates.append(cand)
    for s in _printable_runs(raw or b""):
        if len(s) > 400:
            continue
        if s.startswith("{") or s.startswith("["):
            continue
        if any(x in s.lower() for x in ("text/event-stream", "authorization", "mozilla/")):
            continue
        candidates.append(s)
    return _pick_best_user_text(candidates)


def _extract_prompt_from_multipart(raw: str) -> str | None:
    """Pull user text from multipart form fields (name=prompt/query/...) — not file parts."""
    if not raw or "content-disposition" not in raw.lower():
        return None
    keys = "|".join(re.escape(k) for k in _UNIVERSAL_PROMPT_KEYS)
    pat = (
        rf'Content-Disposition:\s*form-data;\s*name="({keys})"'
        rf'(?![^\r\n]*filename)[^\r\n]*(?:\r\n[^\r\n]+)*\r\n\r\n(.*?)(?:\r\n--|\Z)'
    )
    try:
        for m in re.finditer(pat, raw, re.I | re.S):
            val = (m.group(2) or "").strip()
            if not val or val.startswith("------"):
                continue
            if looks_like_user_prompt(val) and not _is_opaque_wire_blob(val):
                got = _clean_prompt_text(val)
                if got:
                    return got
    except Exception:
        pass
    return None


def extract_prompt(body_bytes: bytes, content_type: str = "", host: str = "") -> str | None:
    """
    Extract ONLY the exact user-typed prompt text from a request body.
    Never returns raw JSON / API metadata / Cloudflare challenge blobs.
    """
    if not body_bytes:
        return None

    try:
        text = body_bytes.decode("utf-8", errors="ignore")
        ct = (content_type or "").lower()
        if not text.strip():
            if _looks_like_chatgpt_body("", body_bytes):
                return extract_chatgpt_prompt(text, body_bytes)
            return None

        # Multipart: extract prompt fields; never treat the raw boundary blob as chat text.
        if "multipart/form-data" in ct or "webkitformboundary" in text[:200].lower() or text.lstrip().startswith("------"):
            return _extract_prompt_from_multipart(text)

        # Body-shape parsers (any admin-monitored domain — no hostname lists).
        if "f.req=" in text or "req0___data__" in text or text.startswith("f.req="):
            gemini_prompt = extract_gemini_prompt(text)
            if gemini_prompt:
                return _clean_prompt_text(gemini_prompt)

        if is_copilot_chat_submit("", text) or '"event":"send"' in text or '"event": "send"' in text:
            copilot_prompt = extract_copilot_prompt(text)
            if copilot_prompt:
                return _clean_prompt_text(copilot_prompt)

        pplx_prompt = extract_perplexity_prompt(text)
        if pplx_prompt:
            return pplx_prompt

        if _looks_like_chatgpt_body(text, body_bytes):
            return extract_chatgpt_prompt(text, body_bytes)

        # URL-encoded form bodies (Copilot / misc — not Gemini)
        if "application/x-www-form-urlencoded" in ct or (
            "%" in text and not text.lstrip().startswith(("{", "["))
        ) or text.startswith(("count=", "at=", "soc-app=", "req0_", "req1_")):
            try:
                form = urllib.parse.parse_qs(urllib.parse.unquote(text), keep_blank_values=False)
                for key in (
                    "prompt", "query", "query_str", "text", "message",
                    "rawUserQuery", "input", "q", "user_query", "instruction",
                    "inputs", "utterance", "content", "user_input", "question",
                ):
                    vals = form.get(key) or form.get(key.lower())
                    if vals and isinstance(vals[0], str):
                        got = _clean_prompt_text(vals[0])
                        if got:
                            return got
                if form.get("f.req"):
                    gemini_prompt = extract_gemini_prompt("f.req=" + form["f.req"][0])
                    return _clean_prompt_text(gemini_prompt) if gemini_prompt else None
            except Exception:
                pass
            return None  # Form data must never fall through to plain text!

        # Structured JSON chat payloads (any platform or custom website)
        if "json" in ct or text.lstrip().startswith(("{", "[")):
            try:
                data = json.loads(text)
            except Exception:
                data = None
            if data is not None:
                got = _extract_from_json(data)
                if got:
                    return got
                got = _deep_extract_from_json(data)
                if got:
                    return got

        # Plain text payloads (only if body itself is a direct user sentence/code)
        cl = text.strip()
        if cl and not cl.startswith(("{", "[")) and looks_like_user_prompt(cl):
            return _clean_prompt_text(cl)

        return None

    except Exception:
        return None


def check_guard_rules(content: str) -> tuple[bool, str, str]:
    """
    Check content against all active DLP guard rules fetched from backend.
    Returns (is_blocked, rule_name, action)
    """
    rules = sorted(
        get_guard_rules(),
        key=lambda r: 1 if is_phone_like_rule(r.get("name", ""), r.get("pattern", "")) else 0,
    )
    for rule in rules:
        if rule_matches_prompt(rule, content):
            return True, rule["name"], rule["action"]
    return False, "", ""


def get_client_ip(flow: http.HTTPFlow) -> str:
    try:
        return flow.client_conn.peername[0]
    except Exception:
        return "127.0.0.1"


def send_to_backend(platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str, upload_images: list[str] | None = None, evaluation_only: bool = False) -> tuple[bool, str, str, str, str]:
    """
    Send intercepted prompt to UnifAI backend /api/browser-ai/intercept.
    Backend handles guard rule matching and returns allowed/blocked decision.
    Returns (allowed, rule_triggered, action, redacted_prompt, reply_text)
    """
    try:
        payload = json.dumps({
            "platform": platform,
            "prompt": prompt,
            "client_ip": client_ip,
            "agent_id": UNIFAI_AGENT_ID,
            "agent_hostname": UNIFAI_AGENT_HOSTNAME,
            "upload_images": upload_images or [],
            "metadata": {
                "domain": domain,
                "url": url,
                "method": method,
                "agent_id": UNIFAI_AGENT_ID,
                "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                "evaluation_only": bool(evaluation_only),
                "upload_scan": bool(evaluation_only),
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # AI Guard Bot may call an LLM — allow enough time for Ollama round-trip
        with urllib.request.urlopen(req, timeout=95) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode("utf-8"))
                allowed = res_data.get("allowed", True)
                rule_triggered = res_data.get("rule_triggered", "")
                action = res_data.get("action", "Allowed")
                redacted_prompt = res_data.get("forward_prompt") or res_data.get("redacted_prompt", prompt)
                # If backend says Redacted but returned the raw prompt, append notice locally.
                if (action or "") in ("Redacted", "Warned") and redacted_prompt == prompt:
                    redacted_prompt = _redacted_forward(prompt, res_data.get("warning_message", ""))
                reply_text = (res_data.get("reply_text") or "").strip()
                eval_error = (res_data.get("eval_error") or "").strip()
                if eval_error:
                    print(f"[UnifAI Proxy] AI Guard Bot eval failed | {eval_error}")
                return allowed, rule_triggered, action, redacted_prompt, reply_text
    except Exception:
        pass

    # Fallback: apply guard rules locally if backend is down
    rules = sorted(
        get_guard_rules(),
        key=lambda r: 1 if is_phone_like_rule(r.get("name", ""), r.get("pattern", "")) else 0,
    )
    for r in rules:
        if not rule_matches_prompt(r, prompt):
            continue
        rule_action = (r.get("action") or "BLOCK").upper()
        if rule_action == "WARN":
            rule_action = "REDACT"
        if rule_action == "BLOCK":
            return False, r["name"], "Blocked", prompt, _security_reply_text(r["name"], r.get("warning_message", ""))
        if rule_action == "REDACT":
            return True, r["name"], "Redacted", _redacted_forward(prompt, r.get("warning_message", "")), ""

    # Backend / evaluator miss — allow traffic; regex rules already ran locally.
    if _fail_open() or has_ai_bot_rules():
        log_prompt_async(platform, domain, prompt, client_ip, url, method)
        return True, "", "Allowed", prompt, ""
    return (
        False,
        "Backend Unreachable",
        "Blocked",
        prompt,
        "UnifAI Guard cannot reach the security backend. Prompt blocked for safety.",
    )


def _security_reply_text(rule_triggered: str, warning_message: str = "") -> str:
    """Only the warning the admin typed on the rule. No built-in template."""
    return (warning_message or "").strip()


def _warning_for_rule_name(rule_name: str) -> str:
    name = (rule_name or "").strip()
    if not name:
        return ""
    get_guard_rules()
    entry = _cached_rule_catalog.get(name)
    if entry:
        return (entry.get("warning_message") or "").strip()
    for r in _cached_rules:
        if (r.get("name") or "").strip() == name:
            return (r.get("warning_message") or "").strip()
    return ""


def inject_file_redact_notice(raw_text: str, notice: str, user_caption: str = "") -> str | None:
    """Append redaction notice to chat Send body. Log keeps original; browser gets notice."""
    notice = (notice or "").strip()
    if not notice or not raw_text:
        return None
    caption = (user_caption or "").strip()
    if caption:
        return inject_warned_prompt(raw_text, caption, _redacted_forward(caption, notice.replace("[UNIFAI REDACTED]", "").strip()))
    if notice in raw_text:
        return raw_text
    escaped = json.dumps(notice)[1:-1]
    if '"content":' in raw_text or '"text":' in raw_text:
        for needle in ('"content":"', '"text":"', '"parts":["'):
            if needle in raw_text:
                return raw_text.replace(needle, needle + escaped + "\\n\\n", 1)
    return raw_text + "\n" + notice


def _ws_frames_copilot(reply: str) -> list[bytes]:
    frames = [
        json.dumps({"event": "received"}, ensure_ascii=False).encode("utf-8"),
        json.dumps({"event": "startMessage", "messageId": "unifai-reply"}, ensure_ascii=False).encode("utf-8"),
    ]
    step = 400
    for i in range(0, len(reply), step):
        frames.append(
            json.dumps({"event": "appendText", "text": reply[i : i + step]}, ensure_ascii=False).encode("utf-8")
        )
    frames.append(json.dumps({"event": "done"}, ensure_ascii=False).encode("utf-8"))
    return frames


def _ws_frames_claude(reply: str) -> list[bytes]:
    return [
        json.dumps({
            "type": "message_start",
            "message": {
                "id": "msg_unifai_reply",
                "type": "message",
                "role": "assistant",
                "content": [],
                "model": "unifai-guard",
            },
        }, ensure_ascii=False).encode("utf-8"),
        json.dumps({
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "text", "text": ""},
        }, ensure_ascii=False).encode("utf-8"),
        json.dumps({
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": reply},
        }, ensure_ascii=False).encode("utf-8"),
        json.dumps({"type": "content_block_stop", "index": 0}, ensure_ascii=False).encode("utf-8"),
        json.dumps({
            "type": "message_delta",
            "delta": {"stop_reason": "end_turn"},
        }, ensure_ascii=False).encode("utf-8"),
        json.dumps({"type": "message_stop"}, ensure_ascii=False).encode("utf-8"),
        json.dumps({
            "completion": reply,
            "stop_reason": None,
            "model": "unifai-guard",
            "stop": None,
            "log_id": "unifai_reply",
        }, ensure_ascii=False).encode("utf-8"),
        json.dumps({
            "completion": "",
            "stop_reason": "stop_sequence",
            "model": "unifai-guard",
            "stop": "",
            "log_id": "unifai_reply",
        }, ensure_ascii=False).encode("utf-8"),
    ]


def _ws_frames_openai(reply: str) -> list[bytes]:
    """ChatGPT / OpenAI-compatible / DeepSeek / many chat UIs."""
    return [
        json.dumps({
            "id": "unifai-reply",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": reply}, "finish_reason": None}],
        }, ensure_ascii=False).encode("utf-8"),
        json.dumps({
            "id": "unifai-reply",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }, ensure_ascii=False).encode("utf-8"),
        b"[DONE]",
        json.dumps({
            "message": {
                "id": "unifai-reply",
                "author": {"role": "assistant"},
                "content": {"content_type": "text", "parts": [reply]},
                "status": "finished_successfully",
            },
            "error": None,
        }, ensure_ascii=False).encode("utf-8"),
    ]


def _ws_frames_perplexity(reply: str) -> list[bytes]:
    return [
        json.dumps({"text": reply}, ensure_ascii=False).encode("utf-8"),
        json.dumps({"status": "completed", "text": reply, "final": True}, ensure_ascii=False).encode("utf-8"),
        json.dumps({"event": "done"}, ensure_ascii=False).encode("utf-8"),
    ]


def _ws_frames_gemini(reply: str) -> list[bytes]:
    return [
        json.dumps({
            "candidates": [{
                "content": {"parts": [{"text": reply}], "role": "model"},
                "finishReason": "STOP",
            }],
        }, ensure_ascii=False).encode("utf-8"),
        b"[DONE]",
    ]


def _ws_frames_universal(reply: str) -> list[bytes]:
    """
    Multi-shape burst for unknown Target Websites.
    Clients ignore frames they don't understand; one matching shape is enough.
    """
    frames: list[bytes] = []
    frames.extend(_ws_frames_copilot(reply))
    frames.extend(_ws_frames_openai(reply))
    frames.extend(_ws_frames_perplexity(reply))
    frames.append(json.dumps({
        "type": "message",
        "role": "assistant",
        "content": reply,
        "text": reply,
        "message": {"role": "assistant", "content": reply, "text": reply},
    }, ensure_ascii=False).encode("utf-8"))
    return frames


def inject_websocket_reply(flow: http.HTTPFlow, host: str, reply_text: str) -> None:
    """
    Push an in-chat assistant reply over WebSocket for ANY monitored Target Website.
    Uses universal frame shapes — no hardcoded hostname routing.
    """
    reply = (reply_text or "").strip()
    if not reply or not flow.websocket:
        return

    try:
        from mitmproxy import ctx
    except Exception as e:
        print(f"[UnifAI Proxy Warning] WS inject unavailable: {e}")
        return

    host_l = (host or "").lower()
    frames = _ws_frames_universal(reply)

    ok = 0
    for frame in frames:
        try:
            ctx.master.commands.call("inject.websocket", flow, True, frame, True)
            ok += 1
        except Exception as e:
            print(f"[UnifAI Proxy Warning] WS inject frame failed: {e}")
            break
    print(f"[UnifAI Proxy] Injected WebSocket reply → {host_l} ({ok}/{len(frames)} frames)")


def make_blocked_response(flow: http.HTTPFlow, rule_triggered: str, host: str, reply_text: str = "") -> None:
    """
    Inject a clean in-chat security reply (HTTP 200) so the website shows a
    professional violation message instead of "Network Error".
    Formats are tailored per platform.
    """
    path = (flow.request.path or "").lower()
    host_l = (host or "").lower()
    accept = (flow.request.headers.get("Accept", "") or "").lower()
    msg = (reply_text or "").strip()
    if not msg:
        msg = "This request was blocked by UnifAI Guard."
    if "evaluation failed" in msg.lower():
        msg = "This request was blocked by UnifAI Guard."
    msg_json = json.dumps(msg)
    msg_escaped = (
        msg.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )

    common_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true",
        "Cache-Control": "no-cache",
    }

    raw_body = (flow.request.content or b"").decode("utf-8", errors="ignore")

    # Wire-format routing: detect from REQUEST SHAPE (path/body/Accept) — not hostname lists.
    chatgpt_body = None
    try:
        parsed = json.loads(raw_body or "")
        if isinstance(parsed, dict) and isinstance(parsed.get("messages"), list):
            if "conversation_id" in parsed or "parent_message_id" in parsed:
                chatgpt_body = parsed
            elif any(isinstance(m, dict) and isinstance(m.get("author"), dict) for m in parsed["messages"]):
                chatgpt_body = parsed
    except Exception:
        chatgpt_body = None

    # ── ChatGPT-shaped conversation APIs (body shape, any monitored domain) ──
    if chatgpt_body is not None:
        user_msg_id = ""
        conv_id = None
        req_data = chatgpt_body if isinstance(chatgpt_body, dict) else {}
        if not req_data:
            try:
                req_data = json.loads(flow.request.content.decode("utf-8", errors="ignore"))
            except Exception:
                req_data = {}
        if not isinstance(req_data, dict):
            req_data = {}
        conv_id = req_data.get("conversation_id")
        user_msg_id = req_data.get("parent_message_id") or ""
        msgs = req_data.get("messages") or []
        if isinstance(msgs, list):
            for m in reversed(msgs):
                if not isinstance(m, dict):
                    continue
                author = m.get("author") if isinstance(m.get("author"), dict) else {}
                if (author.get("role") or "").lower() == "user" and m.get("id"):
                    user_msg_id = m.get("id")
                    break

        import uuid
        reply_msg_id = str(uuid.uuid4())
        now_ts = time.time()

        chatgpt_resp_obj = {
            "message": {
                "id": reply_msg_id,
                "author": {"role": "assistant", "name": None, "metadata": {}},
                "create_time": now_ts,
                "update_time": None,
                "content": {"content_type": "text", "parts": [msg]},
                "status": "finished_successfully",
                "end_turn": True,
                "weight": 1.0,
                "metadata": {
                    "finish_details": {"type": "stop"},
                    "is_complete": True,
                    "model_slug": "gpt-4o",
                    "parent_id": user_msg_id or None,
                },
                "recipient": "all",
            },
            "conversation_id": conv_id,
            "error": None,
        }
        sse_payload = f"data: {json.dumps(chatgpt_resp_obj)}\n\ndata: [DONE]\n\n"
        flow.response = http.Response.make(
            200,
            sse_payload.encode("utf-8"),
            {**common_headers, "Content-Type": "text/event-stream; charset=utf-8"},
        )
        return

    # ── Claude / Anthropic chat APIs (path/body shape) ──
    if _is_claude_api_shape(path, raw_body):
        if "/v1/messages" in path:
            claude_sse = (
                'event: message_start\n'
                'data: {"type":"message_start","message":{"id":"msg_unifai_block","type":"message",'
                '"role":"assistant","content":[],"model":"unifai-guard","stop_reason":null}}\n\n'
                'event: content_block_start\n'
                'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}\n\n'
                'event: content_block_delta\n'
                f'data: {{"type":"content_block_delta","index":0,"delta":{{"type":"text_delta","text":{msg_json}}}}}\n\n'
                'event: content_block_stop\n'
                'data: {"type":"content_block_stop","index":0}\n\n'
                'event: message_delta\n'
                'data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":1}}\n\n'
                'event: message_stop\n'
                'data: {"type":"message_stop"}\n\n'
            )
        else:
            claude_sse = (
                "event: completion\n"
                f"data: {json.dumps({'completion': msg, 'stop_reason': None, 'model': 'unifai-guard', 'stop': None, 'log_id': 'unifai_block'})}\n\n"
                "event: completion\n"
                f"data: {json.dumps({'completion': '', 'stop_reason': 'stop_sequence', 'model': 'unifai-guard', 'stop': '', 'log_id': 'unifai_block'})}\n\n"
            )
        flow.response = http.Response.make(
            200,
            claude_sse.encode("utf-8"),
            {
                **common_headers,
                "Content-Type": "text/event-stream; charset=utf-8",
                "X-Accel-Buffering": "no",
            },
        )
        return

    # ── Microsoft Copilot / Bing (request shape) ──
    if is_copilot_chat_submit(path, raw_body):
        copilot_sse = (
            "data: {\"choices\":[{\"index\":0,\"delta\":{\"role\":\"assistant\",\"content\":"
            f"{msg_json}"
            "}}]}\n\n"
            "data: {\"choices\":[{\"index\":0,\"delta\":{},\"finish_reason\":\"stop\"}]}\n\n"
            "data: [DONE]\n\n"
        )
        # Also provide a Graph-style message payload some Copilot UIs accept
        copilot_json = json.dumps({
            "message": {"text": msg, "role": "assistant"},
            "messages": [{"text": msg, "author": "bot"}],
            "error": None,
            "unifai_blocked": True,
        })
        body = copilot_sse if "event-stream" in accept or "stream" in path else copilot_json
        ctype = (
            "text/event-stream; charset=utf-8"
            if body == copilot_sse
            else "application/json; charset=utf-8"
        )
        flow.response = http.Response.make(
            200,
            body.encode("utf-8"),
            {**common_headers, "Content-Type": ctype},
        )
        return

    # ── Perplexity (request shape) ──
    if is_perplexity_chat_submit(path, raw_body):
        pplx = (
            f'event: message\ndata: {{"text":{msg_json}}}\n\n'
            f'data: {{"status":"completed","text":{msg_json},"final":true}}\n\n'
            "data: [DONE]\n\n"
        )
        flow.response = http.Response.make(
            200,
            pplx.encode("utf-8"),
            {**common_headers, "Content-Type": "text/event-stream; charset=utf-8"},
        )
        return

    # ── Gemini / Bard (request shape) ──
    if is_gemini_chat_submit(path, raw_body) or "f.req=" in raw_body:
        path_compact = path.replace("_", "")
        # StreamGenerate expects progressive Google JSON lines — OpenAI-style SSE leaves the UI spinning.
        if "streamgenerate" in path_compact or "generatecontent" in path_compact or "bardfrontend" in path:
            # Minimal completed model turn so the composer stops loading
            chunk = (
                ")]}'\n"
                f'[["wrb.fr","StreamGenerate","[null,[null,null,null,[[\\"{msg_escaped}\\"]]]]",'
                'null,null,null,"generic"],'
                '["di",34],["af.httprm",34,"-unifai-",1]]\n'
            )
            flow.response = http.Response.make(
                200,
                chunk.encode("utf-8"),
                {**common_headers, "Content-Type": "application/json; charset=utf-8"},
            )
            return

        gemini_body = (
            ")]}'\n"
            f'[["wrb.fr","UnifAIGuard","[[\\"{msg_escaped}\\"]]",null,null,null,"generic"],'
            '["di",34],["af.httprm",34,"-unifai-",1]]\n'
        )
        flow.response = http.Response.make(
            200,
            gemini_body.encode("utf-8"),
            {**common_headers, "Content-Type": "application/json; charset=utf-8"},
        )
        return

    # ── OpenAI-compatible SSE (Accept/path shape — any admin-added domain) ──
    if "event-stream" in accept or "chat/completions" in path or "stream" in path or "completion" in path:
        openai_sse = (
            'data: {"id":"unifai-reply","object":"chat.completion.chunk","choices":'
            '[{"index":0,"delta":{"role":"assistant","content":'
            f"{msg_json}"
            '},"finish_reason":null}]}\n\n'
            'data: {"id":"unifai-reply","object":"chat.completion.chunk","choices":'
            '[{"index":0,"delta":{},"finish_reason":"stop"}]}\n\n'
            "data: [DONE]\n\n"
        )
        flow.response = http.Response.make(
            200,
            openai_sse.encode("utf-8"),
            {**common_headers, "Content-Type": "text/event-stream; charset=utf-8"},
        )
        return

    # ── Fallback for ANY other Target Website: HTTP 200 OpenAI-style JSON ──
    flow.response = http.Response.make(
        200,
        json.dumps({
            "id": "unifai-security-block",
            "object": "chat.completion",
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": msg},
                "finish_reason": "stop",
            }],
            "message": {"role": "assistant", "content": msg, "text": msg},
            "text": msg,
            "unifai": {
                "blocked": True,
                "rule": rule_triggered,
                "message": msg,
            },
        }).encode("utf-8"),
        {**common_headers, "Content-Type": "application/json; charset=utf-8"},
    )


def inject_warned_prompt(raw_text: str, original: str, warned: str) -> str | None:
    """Rewrite request body so WARN forwarding works on JSON and Gemini f.req wire formats."""
    if not raw_text or not original or not warned or original == warned:
        return None
    if original in raw_text:
        return raw_text.replace(original, warned, 1)

    # Gemini / form bodies often JSON-escape the prompt inside f.req=
    variants = [
        original.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"),
        json.dumps(original)[1:-1],  # same escaping as JSON string content
    ]
    warned_variants = [
        warned.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"),
        json.dumps(warned)[1:-1],
    ]
    for ov, wv in zip(variants, warned_variants):
        if ov and ov in raw_text and ov != wv:
            return raw_text.replace(ov, wv, 1)
    return None


# ─────────────────────────────────────────────
# mitmproxy Addon Class
# ─────────────────────────────────────────────

class BrowserAIInterceptor:

    def __init__(self):
        print(f"[UnifAI Proxy] Started. Backend: {UNIFAI_BACKEND_URL}")
        print(f"[UnifAI Proxy] Fetching target domains & guard rules every {CACHE_TTL}s from backend API.")

    def _apply_http_prompt(
        self,
        flow: http.HTTPFlow,
        domain: str,
        platform: str,
        prompt: str,
        client_ip: str,
        raw_text: str,
    ) -> None:
        """Common predict + block/warn for any monitored domain (HTTP)."""
        host = flow.request.pretty_host
        print(f"[UnifAI Proxy] Intercepted prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")
        mark_duplicate_event(domain, prompt)

        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt(
            platform=platform,
            domain=domain,
            prompt=prompt,
            client_ip=client_ip,
            url=flow.request.url,
            method=flow.request.method,
        )

        if not allowed:
            if (action or "").lower() in ("bot answered", "replied"):
                print(f"[UnifAI Proxy] Reply Bot answered for {domain}")
            else:
                print(f"[UnifAI Proxy] BLOCKED prompt to {domain} → Rule: {rule_triggered}")
            make_blocked_response(flow, rule_triggered, host, reply_text=reply_text)
        elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != prompt:
            print(f"[UnifAI Proxy] WARNED prompt to {domain} → Rule: {rule_triggered} (prompt+warning forwarded)")
            try:
                new_content = inject_warned_prompt(raw_text, prompt, redacted_prompt)
                if new_content:
                    flow.request.content = new_content.encode("utf-8")
                else:
                    print(f"[UnifAI Proxy Warning] WARN inject miss | {domain} | could not rewrite body")
            except Exception as e:
                print(f"[UnifAI Proxy Warning] Failed to inject warning into request: {e}")

    def _file_send_maybe_block(
        self,
        flow: http.HTTPFlow,
        domain: str,
        platform: str,
        client_ip: str,
        raw_text: str,
        content_type: str,
        path: str,
    ) -> tuple[bool, int]:
        """Scan attached/cached files on Send. Returns (blocked, files_processed)."""
        should_block_file, file_block_msg, redact_notice, n_processed = enforce_file_send_policy(
            platform=platform,
            domain=domain,
            host=flow.request.pretty_host,
            client_ip=client_ip,
            url=flow.request.url,
            method=flow.request.method,
            raw_text=raw_text,
            content_type=content_type,
            file_name_hint=(
                extract_filename_from_upload(flow, raw_text)
                if chat_carries_attachment(raw_text)
                else extract_attachment_filename_from_send(raw_text)
            ),
            path=path,
        )
        if should_block_file:
            make_blocked_response(
                flow, "Block Upload", flow.request.pretty_host, reply_text=file_block_msg,
            )
            return True, n_processed
        if redact_notice:
            caption = extract_prompt_universal(
                flow.request.content or b"", content_type, host=flow.request.pretty_host, url=flow.request.url,
            ) or ""
            caption = (caption or "").strip()
            try:
                new_content = inject_file_redact_notice(raw_text, redact_notice, caption)
                if new_content:
                    flow.request.content = new_content.encode("utf-8")
                    print(f"[UnifAI Proxy] FILE REDACT notice injected | {domain}")
                else:
                    print(f"[UnifAI Proxy Warning] FILE REDACT inject miss | {domain}")
            except Exception as e:
                print(f"[UnifAI Proxy Warning] FILE REDACT inject failed: {e}")
        return False, n_processed

    def _log_attachment_send_caption(
        self,
        flow: http.HTTPFlow,
        domain: str,
        platform: str,
        client_ip: str,
        raw_text: str,
        peek_prompt: str | None,
        has_prompt: bool,
    ) -> None:
        """Log a short user-typed caption with a file Send — never embedded document body text."""
        if not has_prompt:
            return
        pn = (peek_prompt or "").strip()
        if not pn or len(pn) > 320 or _looks_like_document_body_dump(pn):
            return
        if is_duplicate_event(domain, pn, ttl=DEDUPE_TTL, mark=False):
            return
        self._apply_http_prompt(flow, domain, platform, pn, client_ip, raw_text)

    # ── HTTP Request Interception ──────────────

    def request(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host
        if is_noise_host(host):
            return

        # Full-site lock (admin: Block entire website) — all methods, all paths
        blocked, b_domain, b_platform = detect_site_block(host)
        if blocked:
            client_ip = get_client_ip(flow)
            if not is_duplicate_event(b_domain, "site-block", ttl=BLOCK_DEDUPE_TTL):
                print(f"[UnifAI Proxy] SITE BLOCKED | {client_ip} → {host} ({b_domain})")
                try:
                    payload = json.dumps({
                        "platform": b_platform,
                        "prompt": f"[SITE BLOCKED] Access denied to {b_domain}",
                        "client_ip": client_ip,
                        "agent_id": UNIFAI_AGENT_ID,
                        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                        "metadata": {
                            "domain": b_domain,
                            "url": flow.request.url,
                            "method": flow.request.method,
                            "is_blocked": True,
                            "blocked_reason": "Block Entire Website",
                            "agent_id": UNIFAI_AGENT_ID,
                            "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                        },
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass
            make_site_blocked_response(flow, b_domain, b_platform)
            return

        is_target, domain, platform = detect_target(host)

        if not is_target:
            return

        # Keep control settings warm
        get_control_settings()

        path = flow.request.path
        client_ip = get_client_ip(flow)
        method = (flow.request.method or "").upper()

        # ── Universal GET: query-string prompts on any monitored domain ──
        if method == "GET":
            qs_prompt = extract_prompt_from_query_string(flow.request.url)
            if (
                qs_prompt
                and looks_like_user_prompt(qs_prompt)
                and _is_confident_chat_send(path, "", b"")
                and not is_duplicate_event(domain, qs_prompt, ttl=DEDUPE_TTL, mark=False)
            ):
                self._apply_http_prompt(flow, domain, platform, qs_prompt, client_ip, "")
            return

        if method not in ("POST", "PUT", "PATCH"):
            return

        # ── File Upload: block immediately when policy ON; otherwise cache for Send-time scan ──
        raw_bytes = flow.request.content or b""
        content_type = flow.request.headers.get("content-type", "")

        try:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = ""

        # Domain-add-only: extract user text first. Role labels never skip a real prompt/file.
        peek_prompt = extract_prompt_universal(
            raw_bytes, content_type, host=host, url=flow.request.url,
        )
        has_prompt = _should_intercept_extracted_prompt(
            peek_prompt, path, raw_text, domain, host=host, raw_bytes=raw_bytes,
        )
        attachment_send = _send_carries_attachment(raw_text)

        is_upload, upload_reason = detect_file_upload(flow, raw_text)
        if is_upload:
            fname = extract_filename_from_upload(flow, raw_text)
            confident = is_confident_file_upload(
                fname=fname,
                content_type=content_type,
                raw_bytes=raw_bytes,
                raw_text=raw_text,
                upload_reason=upload_reason or "",
                host=host,
                path=path,
            )
            # Upload pick: cache bytes only — no predict, no log, no block until user presses Send.
            if confident:
                file_ids = _extract_file_ids_from_chat(raw_text)
                cache_upload_file(
                    domain,
                    file_name=fname or "attachment",
                    raw_bytes=raw_bytes,
                    content_type=content_type,
                    upload_reason=upload_reason or "",
                    file_id=file_ids[0] if file_ids else "",
                )
                print(
                    f"[UnifAI Proxy] FILE CACHED (await Send — no log yet) | {domain} | "
                    f"{fname or 'attachment'} | {len(raw_bytes)} bytes"
                )
            else:
                print(
                    f"[UnifAI Proxy] Ignoring weak upload signal | {host} | "
                    f"reason={upload_reason!r} name={fname!r} bytes={len(raw_bytes)}"
                )
            return

        # ── File Send: scan/cache on pick; predict + allow/block on Send ──
        if attachment_send and _file_policy_applies_on_send(path, raw_text, raw_bytes):
            blocked, _n = self._file_send_maybe_block(
                flow, domain, platform, client_ip, raw_text, content_type, path,
            )
            if blocked:
                return
            # File row logged above — do not also log caption or embedded doc text as a separate prompt.
            return

        # ── Domain-add-only intercept: extracted user text → predict ──
        if has_prompt:
            self._apply_http_prompt(flow, domain, platform, peek_prompt, client_ip, raw_text)
            return

        # Gemini batchexecute noise — only skip when body is not a chat submit.
        if "batchexecute" in (path or "").lower() and not is_gemini_chat_submit(path, raw_text):
            return

        if is_copilot_noise_content(raw_text):
            return

        # Only inspect real chat/prompt endpoints — ignore challenges & analytics
        if not is_chat_path(path, host, raw_text):
            return

        chatgpt_shaped = _looks_like_chatgpt_body(raw_text, raw_bytes)
        if not chatgpt_shaped:
            if is_noise(path):
                return
            if is_noise(path, raw_text):
                return
        elif "prepare" in (path or "").lower() or "autocomplet" in (path or "").lower():
            return

        # File attached + Send (fallback path when extract missed on first pass)
        if _file_policy_applies_on_send(path, raw_text, raw_bytes):
            blocked, n_processed = self._file_send_maybe_block(
                flow, domain, platform, client_ip, raw_text, content_type, path,
            )
            if blocked:
                return
            if n_processed > 0:
                return

        prompt = extract_prompt_universal(raw_bytes, content_type, host=host, url=flow.request.url)
        if not prompt or len(prompt.strip()) < 1:
            if len(raw_bytes) > 8:
                print(f"[UnifAI Proxy] No prompt extracted | {platform} ({domain}) path={path[:80]!r} bytes={len(raw_bytes)}")
            # Attachment-only send already logged above (real file markers only)
            if chat_carries_attachment(raw_text):
                return
            return
        if not looks_like_user_prompt(prompt) and not (chatgpt_shaped and prompt.strip()):
            return
        if _is_opaque_wire_blob(prompt) and not (chatgpt_shaped and len(prompt.strip()) < 32):
            return
        # Skip duplicate FILE UPLOAD lines if extract_prompt somehow returned that
        if prompt.strip().startswith("[FILE UPLOAD"):
            return

        # ChatGPT/Perplexity: skip only in-progress draft bodies, not finished submits.
        # Every finished prompt (1 letter, number, symbol, long text) must predict + apply rules.
        if is_unsubmitted_chat_body(path, raw_text):
            return

        # Collapse browser double-fire only; do not stamp until we actually intercept.
        if is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL, mark=False):
            return

        print(f"[UnifAI Proxy] Intercepted prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")
        mark_duplicate_event(domain, prompt)

        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt(
            platform=platform,
            domain=domain,
            prompt=prompt,
            client_ip=client_ip,
            url=flow.request.url,
            method=flow.request.method,
        )

        if not allowed:
            if (action or "").lower() in ("bot answered", "replied"):
                print(f"[UnifAI Proxy] Reply Bot answered for {domain}")
            else:
                print(f"[UnifAI Proxy] BLOCKED prompt to {domain} → Rule: {rule_triggered}")
            make_blocked_response(flow, rule_triggered, host, reply_text=reply_text)
        elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != prompt:
            print(f"[UnifAI Proxy] WARNED prompt to {domain} → Rule: {rule_triggered} (prompt+warning forwarded)")
            try:
                new_content = inject_warned_prompt(raw_text, prompt, redacted_prompt)
                if new_content:
                    flow.request.content = new_content.encode("utf-8")
                else:
                    print(f"[UnifAI Proxy Warning] WARN inject miss | {domain} | could not rewrite body")
            except Exception as e:
                print(f"[UnifAI Proxy Warning] Failed to inject warning into request: {e}")

    def response(self, flow: http.HTTPFlow) -> None:
        # Download / copy-paste controls removed — only upload is blocked on request().
        return

    # ── WebSocket Message Interception ─────────

    def websocket_message(self, flow: http.HTTPFlow) -> None:
        if not flow.websocket or not flow.websocket.messages:
            return

        msg = flow.websocket.messages[-1]
        if not msg.from_client:
            return

        host = flow.request.pretty_host
        if is_noise_host(host):
            return
        blocked, b_domain, b_platform = detect_site_block(host)
        if blocked:
            msg.kill()
            print(f"[UnifAI Proxy] SITE BLOCKED (websocket) → {b_domain} ({b_platform})")
            return
        is_target, domain, platform = detect_target(host)
        if not is_target:
            return

        content = msg.text or ""
        if not content or len(content.strip()) < 1:
            return

        ws_path = flow.request.path or ""
        client_ip = get_client_ip(flow)
        ws_has_prompt = False
        ws_prompt = extract_prompt_universal(
            content.encode("utf-8"), "application/json", host=host, url=flow.request.url,
        )
        ws_has_prompt = _should_intercept_extracted_prompt(
            ws_prompt, ws_path, content, domain, host=host, raw_bytes=content.encode("utf-8", errors="ignore"),
        )
        attachment_send = _send_carries_attachment(content)

        if attachment_send and _file_policy_applies_on_send(ws_path, content, content.encode("utf-8", errors="ignore")):
            should_block_file, file_block_msg, _n = enforce_file_send_policy(
                platform=platform,
                domain=domain,
                host=host,
                client_ip=client_ip,
                url=flow.request.url,
                method="WS",
                raw_text=content,
                content_type="application/json",
                path=ws_path,
            )
            if should_block_file:
                try:
                    msg.drop()
                except Exception:
                    try:
                        msg.kill()
                    except Exception:
                        pass
                inject_websocket_reply(flow, host, (file_block_msg or "").strip())
                return
            # File row logged — only allow a short user caption, never embedded doc text.
            if ws_has_prompt:
                pn = (ws_prompt or "").strip()
                if pn and len(pn) <= 320 and not _looks_like_document_body_dump(pn):
                    if not is_duplicate_event(domain, pn, ttl=DEDUPE_TTL, mark=False):
                        mark_duplicate_event(domain, ws_prompt)
                        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt(
                            platform=platform,
                            domain=domain,
                            prompt=ws_prompt,
                            client_ip=client_ip,
                            url=flow.request.url,
                            method="WS",
                        )
                        if not allowed:
                            try:
                                msg.drop()
                            except Exception:
                                try:
                                    msg.kill()
                                except Exception:
                                    pass
                            inject_websocket_reply(flow, host, (reply_text or "").strip())
                        elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != ws_prompt:
                            new_content = inject_warned_prompt(content, ws_prompt, redacted_prompt)
                            if new_content:
                                msg.text = new_content
            return

        # ── Universal WebSocket: domain-agnostic extract (same rule as HTTP) ──
        if ws_has_prompt:
            mark_duplicate_event(domain, ws_prompt)
            allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt(
                platform=platform,
                domain=domain,
                prompt=ws_prompt,
                client_ip=client_ip,
                url=flow.request.url,
                method="WS",
            )
            if not allowed:
                try:
                    msg.drop()
                except Exception:
                    try:
                        msg.kill()
                    except Exception:
                        pass
                inject_websocket_reply(flow, host, (reply_text or "").strip())
            elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != ws_prompt:
                new_content = inject_warned_prompt(content, ws_prompt, redacted_prompt)
                if new_content:
                    msg.text = new_content
            return

        if "batchexecute" in ws_path.lower() and not is_gemini_chat_submit(ws_path, content):
            return
        if is_copilot_noise_content(content):
            return
        if not is_chat_path(ws_path, host, content):
            return

        chatgpt_shaped = _looks_like_chatgpt_body(content)
        if not chatgpt_shaped and is_noise(ws_path, content):
            return

        # File attachment Send must hit Block Upload / file rules (finished Send only)
        if _file_policy_applies_on_send(ws_path, content, content.encode("utf-8", errors="ignore")):
            should_block_file, file_block_msg, n_processed = enforce_file_send_policy(
                platform=platform,
                domain=domain,
                host=host,
                client_ip=get_client_ip(flow),
                url=flow.request.url,
                method="WS",
                raw_text=content,
                content_type="application/json",
                path=flow.request.path or "",
            )
            if should_block_file:
                try:
                    msg.drop()
                except Exception:
                    try:
                        msg.kill()
                    except Exception:
                        pass
                inject_websocket_reply(flow, host, file_block_msg)
                return
            if n_processed > 0:
                return

        # Copilot/Edge image or file frames must not fall through as garbled text prompts.
        if copilot_carries_binary_attach(content) or chat_carries_attachment(content) or chatgpt_carries_file(content):
            return

        prompt = extract_prompt_universal(content.encode("utf-8"), "application/json", host=host, url=flow.request.url)
        if not prompt or prompt.strip() in ("{}", "[]", "ping", "pong"):
            return
        if not looks_like_user_prompt(prompt) and not (chatgpt_shaped and prompt.strip()):
            return
        if _is_opaque_wire_blob(prompt) and not (chatgpt_shaped and len(prompt.strip()) < 32):
            return

        if is_unsubmitted_chat_body(flow.request.path, content):
            return

        if is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL, mark=False):
            return

        client_ip = get_client_ip(flow)
        print(f"[UnifAI Proxy] WebSocket prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")
        mark_duplicate_event(domain, prompt)

        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt(
            platform=platform,
            domain=domain,
            prompt=prompt,
            client_ip=client_ip,
            url=flow.request.url,
            method="WS",
        )

        if not allowed:
            if (action or "").lower() in ("bot answered", "replied"):
                print(f"[UnifAI Proxy] Reply Bot answered via WebSocket for {domain}")
            else:
                print(f"[UnifAI Proxy] BLOCKED WebSocket to {domain} → Rule: {rule_triggered or action}")
            block_msg = (reply_text or "").strip()
            # Drop outbound turn (site AI never sees it), inject reply for ANY target site.
            try:
                msg.drop()
            except Exception:
                try:
                    msg.kill()
                except Exception:
                    pass
            inject_websocket_reply(flow, host, block_msg)
        elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != prompt:
            print(f"[UnifAI Proxy] WARNED WebSocket prompt to {domain} → Rule: {rule_triggered}")
            new_content = inject_warned_prompt(content, prompt, redacted_prompt)
            if new_content:
                msg.text = new_content


addons = [BrowserAIInterceptor()]
