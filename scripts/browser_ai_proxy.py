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

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request
from mitmproxy import http

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

# Backend URL (set by docker-compose environment variable)
UNIFAI_BACKEND_URL = os.getenv("UNIFAI_BACKEND_URL", "https://unifai.dev-yp.com")
UNIFAI_AGENT_ID = os.getenv("UNIFAI_AGENT_ID", "")
UNIFAI_AGENT_HOSTNAME = os.getenv("UNIFAI_AGENT_HOSTNAME", "")

# Cache refresh interval in seconds (targets / rules / controls)
CACHE_TTL = 1

# Default fallback domains if backend is temporarily unreachable
# Default fallback is EMPTY — only admin-added Target Websites are monitored.
DEFAULT_TARGET_DOMAINS: dict = {}

# File upload endpoint patterns (include Gemini / Google Drive / Docs upload paths)
UPLOAD_ENDPOINTS = [
    "/files", "/file", "/upload", "/attachment", "/attachments",
    "/backend-api/files", "/v1/files", "/api/upload", "/file-upload",
    "/upload/", "/media/upload", "/resumable", "/filepush", "/pushfile",
    "/v1beta/files", "/upload/v1beta", "/drive/v3/files", "/upload/drive",
]

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
_cached_rules: list = []   # list of {"name": str, "pattern": str, "action": str, "active": bool}
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


# ─────────────────────────────────────────────
# Backend API Fetching
# ─────────────────────────────────────────────

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


def get_target_domains() -> dict:
    """
    Fetch target domains from UnifAI backend every CACHE_TTL seconds.
    Returns dict of {domain: platform_name} for PAC/monitor routing
    (monitored OR block_site). Also refreshes _cached_blocked for full-site lock.
    """
    global _cached_domains, _cached_blocked, _domains_fetched_at
    now = time.time()
    if now - _domains_fetched_at < CACHE_TTL:
        return _cached_domains

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/targets")
    if data is not None:
        targets = data.get("targets", [])
        new_map = {}
        new_blocked = {}
        for t in targets:
            domain = _normalize_domain(t.get("domain", ""))
            monitored = bool(t.get("monitored"))
            block_site = bool(t.get("block_site"))
            platform = t.get("platform_name") or domain or "AI Platform"
            if domain and (monitored or block_site):
                new_map[domain] = platform
            if domain and block_site:
                new_blocked[domain] = platform
        _cached_domains = new_map
        _cached_blocked = new_blocked
        _domains_fetched_at = now
        print(
            f"[UnifAI Proxy] Refreshed {len(new_map)} target domains "
            f"({len(new_blocked)} full-site locks) from backend."
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
    <p>This is a full-site lock (not only prompt filtering). Contact your UnifAI admin to change Target Websites settings.</p>
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
    global _cached_rules, _cached_has_ai_bot, _rules_fetched_at
    now = time.time()
    if now - _rules_fetched_at < CACHE_TTL:
        return _cached_rules

    data = _fetch_json(f"{UNIFAI_BACKEND_URL}/api/browser-ai/rules")
    if data is not None:
        rules = data.get("rules", [])
        compiled = []
        has_ai_bot = False
        for r in rules:
            if not r.get("active", False):
                continue
            # Any active AI bot must hit the backend (including incomplete BLOCK bots —
            # backend fail-closes those). Do not require provider/model/prompt here.
            if str(r.get("rule_type") or "").strip().lower() == "ai_bot":
                has_ai_bot = True
            pattern = r.get("pattern", "").strip()
            if not pattern:
                continue
            try:
                compiled.append({
                    "name": r.get("name", "Unknown Rule"),
                    "pattern": pattern,
                    "regex": re.compile(pattern, re.IGNORECASE),
                    "action": r.get("action", "BLOCK"),  # BLOCK or WARN (legacy REDACT→WARN)
                    "severity": r.get("severity", "HIGH"),
                    "warning_message": (r.get("warning_message") or "").strip(),
                })
            except re.error:
                pass
        _cached_rules = compiled
        _cached_has_ai_bot = has_ai_bot
        _rules_fetched_at = now
        print(f"[UnifAI Proxy] Refreshed {len(compiled)} guard rules from backend.")
        return _cached_rules

    # Backend unreachable: keep last cache (may be empty). Do not invent rules.
    return _cached_rules


def has_ai_bot_rules() -> bool:
    get_guard_rules()
    return bool(_cached_has_ai_bot)


def evaluate_prompt(platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str) -> tuple[bool, str, str, str, str]:
    """Regex decides locally first (fast). AI Guard Bot waits for backend LLM eval."""
    # Fast path: local regex BLOCK — do not wait on AI bot (avoids Gemini spinner).
    local_allowed, rule_triggered, action, redacted_prompt, reply_text = decide_prompt_locally(prompt)
    if action == "Blocked" or not local_allowed:
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

    # Local WARN must NOT skip AI Guard Bot — a BLOCK bot can still escalate.
    if has_ai_bot_rules():
        return send_to_backend(platform, domain, prompt, client_ip, url, method)

    if action in ("Redacted", "Warned"):
        log_prompt_async(platform, domain, prompt, client_ip, url, method)
        return local_allowed, rule_triggered, action, redacted_prompt, reply_text

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

    If controls were never loaded from the backend, fail-closed (same as prompts)
    unless UNIFAI_FAIL_OPEN=1.
    """
    c = get_control_settings()
    if _controls_from_backend:
        return bool(c.get("enabled")) and bool(c.get(key))
    return not _fail_open()


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


def _warned_forward(prompt: str, warning_message: str = "") -> str:
    """ChatGPT receives full original prompt + warning. Logs keep original only (server-side)."""
    w = (warning_message or "").strip() or "This prompt triggered a UnifAI Guard warning."
    return f"{(prompt or '').rstrip()}\n\n[UNIFAI WARNING] {w}"


def decide_prompt_locally(prompt: str) -> tuple[bool, str, str, str, str]:
    rules = sorted(
        get_guard_rules(),
        key=lambda r: 1 if is_phone_like_rule(r.get("name", ""), r.get("pattern", "")) else 0,
    )
    for r in rules:
        if not rule_matches_prompt(r, prompt):
            continue
        rule_action = (r.get("action") or "BLOCK").upper()
        if rule_action == "REDACT":
            rule_action = "WARN"
        if rule_action == "BLOCK":
            return False, r["name"], "Blocked", prompt, _security_reply_text(r["name"], r.get("warning_message", ""))
        if rule_action == "WARN":
            return True, r["name"], "Warned", _warned_forward(prompt, r.get("warning_message", "")), ""
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


def is_chat_path(path: str, host: str = "") -> bool:
    """True when URL path looks like an actual chat/prompt submit endpoint."""
    p = (path or "").lower().split("?", 1)[0]
    h = (host or "").lower()
    if _path_has_ignore_pattern(p):
        return False
    if p and NOISE_EXTENSIONS.search(p):
        return False
    if "chatgpt.com" in h or "chat.openai.com" in h:
        if not p:
            return True
        if "prepare" in p or "autocomplet" in p or "implicit" in p:
            return False
        return "/conversation" in p or "/messages" in p or "/chat/completions" in p
    # Gemini: only the real chat submit URL — never analytics / batchexecute noise
    if is_gemini_host(h):
        if not p:
            return False
        return is_gemini_chat_submit(p, "")
    if not p:
        return True
    return True


def is_gemini_host(host: str) -> bool:
    h = (host or "").lower()
    return any(
        x in h
        for x in (
            "gemini.google.",
            "bard.google.",
            "generativelanguage.googleapis",
        )
    )


def is_gemini_chat_submit(path: str, body: str = "") -> bool:
    """True only for the HTTP call that carries the user's typed Gemini prompt.

    Only StreamGenerate / GenerateContent / BardFrontendService paths.
    batchexecute alone leaks wire junk (co.in, session ids) — never treat as chat.
    """
    _ = body  # kept for call-site compatibility
    path_l = (path or "").lower()
    compact = path_l.replace("_", "")
    if "streamgenerate" in compact or "generatecontent" in compact:
        return True
    if "bardfrontendservice" in path_l:
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
        if any(c.isupper() for c in t) and any(c.islower() for c in t) and ("-" in t or "_" in t):
            return True
    return False


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
    if "gemini.google." in host or "bard.google." in host:
        return True
    if "generativelanguage.googleapis" in host:
        return True
    if host in ("google.com", "www.google.com") and "gemini" in path:
        return True
    # Referrer-style ChatGPT app URLs (hl= locale) — not a user prompt
    if ("chatgpt.com" in host or "chat.openai.com" in host) and (
        "hl=" in query or path in ("", "/", "/app")
    ):
        return True
    return False


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
    if _is_ai_chrome_url(t):
        return False
    if _is_google_wire_blob(t):
        return False
    if t.startswith("gAAAA") or '"p":"gAAAA' in t:
        return False
    if t.startswith("[FILE UPLOAD") or t.startswith("[FILE DOWNLOAD") or t.startswith("[FILE CONTENT") or t.startswith("[SITE BLOCKED"):
        return True

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
    for domain, platform in domains_map.items():
        if host_lower == domain or host_lower.endswith("." + domain):
            return True, domain, platform
    return False, "", ""


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
        if '"presence"' in content:
            return True
        if content.startswith('{"id":') and '"command":' in content and '"messages"' not in content:
            return True
        if len(content) > 0 and ord(content[0]) < 32 and ord(content[0]) not in (10, 13):
            return True
        # Gemini / form chat bodies are valid (f.req=...)
        cl = content.lstrip()
        if cl.startswith("f.req=") or "f.req=" in cl[:120]:
            return False
        # Copilot websocket send events
        if '"event":"send"' in content or '"event": "send"' in content:
            return False
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


def is_duplicate_event(domain: str, event_key: str, ttl: float = DEDUPE_TTL) -> bool:
    """Return True if the same event was already logged for this domain recently."""
    now = time.time()
    expired = [k for k, ts in _recent_prompts.items() if now - ts > max(DEDUPE_TTL, BLOCK_DEDUPE_TTL)]
    for k in expired:
        _recent_prompts.pop(k, None)

    key = f"{domain}|{event_key.strip().lower()}"
    prev = _recent_prompts.get(key)
    if prev is not None and (now - prev) <= ttl:
        return True
    _recent_prompts[key] = now
    return False


def is_duplicate_prompt(domain: str, prompt: str) -> bool:
    """Return True if the same prompt was already logged for this domain recently."""
    return is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL)


def is_chatgpt_host(host: str) -> bool:
    h = (host or "").lower()
    return "chatgpt.com" in h or "chat.openai.com" in h


def is_unsubmitted_chat_body(path: str, body: str) -> bool:
    """True for ChatGPT prepare/draft/in-progress payloads — not Enter/send."""
    path_l = (path or "").lower()
    if "prepare" in path_l or "autocomplet" in path_l or "partial" in path_l:
        return True
    if not body:
        return False
    try:
        data = json.loads(body)
    except Exception:
        return False
    if not isinstance(data, dict):
        return False
    action = str(data.get("action") or "").strip().lower()
    if action and action not in ("next", "variant", "continue"):
        return True
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
    """Skip growing/shrinking composer text (keystrokes). Intercept the finished submit."""
    text = (prompt or "").strip()
    if not text or not domain:
        return False
    now = time.time()
    prev = _composer_draft.get(domain)
    _composer_draft[domain] = (text, now)
    if not prev:
        return False
    prev_text, prev_ts = prev
    if now - prev_ts > 2.5:
        return False
    if text == prev_text:
        return False
    grew = text.startswith(prev_text) and 0 < len(text) - len(prev_text) <= 24
    shrunk = prev_text.startswith(text) and 0 < len(prev_text) - len(text) <= 24
    return grew or shrunk


def _parts_to_text(parts) -> str | None:
    """Join ChatGPT/Claude-style content parts into plain user text."""
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
            if isinstance(part.get("text"), (str, int, float)):
                chunks.append(str(part["text"]))
            elif part.get("type") in ("text", "input_text") and isinstance(part.get("text"), (str, int, float)):
                chunks.append(str(part["text"]))
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
        # ChatGPT web: {"content_type":"text","parts":["hello"]}
        if "parts" in content:
            return _parts_to_text(content.get("parts"))
        if isinstance(content.get("text"), (str, int, float)):
            return _clean_prompt_text(str(content["text"]))
    if isinstance(content, list):
        return _parts_to_text(content)

    # Copilot / Graph / Bing / generic fields
    for key in (
        "text", "prompt", "query", "query_str", "rawUserQuery",
        "utterance", "userMessage", "input", "question", "user_input", "inputs",
    ):
        val = msg.get(key)
        if isinstance(val, (str, int, float)):
            got = _clean_prompt_text(str(val))
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
                if _is_google_wire_blob(item):
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
            got = _clean_prompt_text(str(val))
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
                    got = _clean_prompt_text(str(val[nk]))
                    if got:
                        return got

    # Copilot / Sydney send events
    if str(data.get("event", "")).lower() in ("send", "message", "chat"):
        for key in ("content", "message", "parts", "attachments", "input"):
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
                got = _clean_prompt_text(str(val))
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


def detect_file_upload(flow: http.HTTPFlow, raw_content: str) -> tuple[bool, str]:
    """Detect real file upload attempts — not chat JSON / + menu handshakes."""
    headers = flow.request.headers
    content_type = (headers.get("content-type", "") or "").lower()
    path = (flow.request.path or "").lower()
    method = (flow.request.method or "").upper()
    host = (flow.request.pretty_host or "").lower()
    chat_submit = is_chat_path(path, host)
    body_len = len(flow.request.content or b"")
    path_only = path.split("?", 1)[0]

    # Google resumable: only real byte transfer / finalize — not session "start"/"query"
    goog_cmd = (headers.get("x-goog-upload-command", "") or "").lower()
    if goog_cmd:
        if any(x in goog_cmd for x in ("upload", "finalize", "append")):
            return True, f"Google Resumable Upload ({goog_cmd})"
        # start / query / cancel = picker open or handshake, not a file yet
    else:
        for hk, hv in headers.items():
            hk_l = (hk or "").lower()
            hv_l = (hv or "").lower()
            if hk_l.startswith("x-goog-upload") and body_len >= 512:
                return True, f"Google Resumable Upload ({hk}={hv_l[:40]})"
            if "upload" in hk_l and ("file" in hk_l or "content" in hk_l) and body_len >= 512:
                return True, f"Upload header ({hk})"

    # Real multipart / binary body
    if "multipart/form-data" in content_type:
        # Empty multipart from opening the picker — require a filename= part
        if "filename=" in (raw_content or "") or "filename*=" in (raw_content or "").lower():
            return True, f"File content-type ({content_type.split(';')[0]})"
        if body_len >= 1500:
            return True, f"File content-type ({content_type.split(';')[0]})"
        return False, ""
    if not chat_submit:
        for prefix in UPLOAD_CONTENT_TYPES:
            if prefix in content_type and body_len >= 64:
                return True, f"File content-type ({content_type.split(';')[0]})"

    # Upload URL paths — ChatGPT "+" hits /files JSON handshake before any file is chosen
    for ep in UPLOAD_ENDPOINTS:
        if ep not in path_only:
            continue
        # Ignore library / list / process-status style GETs (method already POST-only upstream)
        if any(x in path_only for x in ("/files/library", "/files/process", "/files/download")):
            continue
        is_json_body = "json" in content_type or (raw_content or "").lstrip()[:1] in ("{", "[")
        # Real upload: binary, multipart, or large non-JSON body
        if "multipart/form-data" in content_type or "octet-stream" in content_type:
            return True, f"File Upload Endpoint ({path_only[:80]})"
        if not is_json_body and body_len >= 512:
            return True, f"File Upload Endpoint ({path_only[:80]})"
        if is_json_body and body_len >= 50_000:
            return True, f"File Upload Endpoint large JSON ({path_only[:80]})"
        # Small JSON to /files = create upload session / open + menu — NOT an upload
        continue

    if method in ("POST", "PUT", "PATCH") and body_len >= 2048:
        if any(
            x in host
            for x in ("upload.google", "drive.google", "docs.google", "clients6.google", "googleapis.com")
        ):
            if "json" not in content_type or body_len >= 50_000:
                return True, f"Large upload body on {host} ({body_len} bytes)"

    # JSON attachment heuristics: NEVER on chat submit; NEVER tiny metadata-only bodies
    if raw_content and not chat_submit and body_len >= 256:
        strong = any(
            k in raw_content
            for k in (
                '"file_name"', '"fileName"', '"mime_type"', '"mimeType"',
                '"fileData"', '"inline_data"', '"inlineData"',
                "application/vnd.openxmlformats", "multipart/form-data",
            )
        )
        # file_id / asset_pointer alone are prior-turn chat metadata — not a new upload
        if strong and (
            "filename=" in raw_content.lower()
            or body_len >= 2048
            or any(x in raw_content for x in ('"bytes"', '"data":', "base64", "octet-stream"))
        ):
            return True, "File Attachment Payload in Request"
        low = raw_content.lower()
        if "filename" in low and "content-type" in low and any(
            x in low for x in (".docx", ".pdf", ".xlsx", ".pptx", ".png", ".jpg")
        ):
            return True, "Multipart-like file attachment payload"

    return False, ""


def extract_filename_from_upload(flow: http.HTTPFlow, raw_text: str = "") -> str:
    """Extract uploaded file name from headers, JSON body, multipart body, or URL path."""
    headers = flow.request.headers

    # 1. Content-Disposition header
    cd = headers.get("content-disposition", "")
    if "filename" in cd:
        m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)["\']?', cd, re.I)
        if m:
            return m.group(1).strip().strip('"\'')

    # 2. X-File-Name or upload headers
    for hk in ("x-file-name", "x-goog-upload-file-name", "x-filename", "x-upload-filename"):
        val = headers.get(hk)
        if val:
            return str(val).strip().strip('"\'')

    # 3. JSON body fields (e.g. {"file_name": "data.pdf"} or {"fileName": "..."})
    if raw_text:
        m = re.search(r'["\'](?:file_name|fileName|name|title|filename)["\']\s*:\s*["\']([^"\']+\.[a-zA-Z0-9]{2,6})["\']', raw_text)
        if m:
            return m.group(1).strip()
        # Multipart filename inside raw_text body
        m = re.search(r'filename\s*=\s*["\']([^"\';\r\n]+\.[a-zA-Z0-9]{2,6})["\']', raw_text[:8000], re.I)
        if m:
            return m.group(1).strip()

    # 4. Path parameter if it ends with a file extension
    path_clean = (flow.request.path or "").split("?", 1)[0]
    last_seg = path_clean.rsplit("/", 1)[-1]
    if "." in last_seg and any(last_seg.lower().endswith(ext) for ext in (
        ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".json",
        ".png", ".jpg", ".jpeg", ".zip", ".tar", ".gz", ".py", ".js",
    )):
        return urllib.parse.unquote(last_seg)

    return ""


def _extract_pdf_text(data: bytes) -> str:
    """Extract readable text from PDF bytes (pypdf if available, else lightweight fallback)."""
    if not data or b"%PDF" not in data[:1024] and not data.startswith(b"%PDF"):
        # Still try if magic is later in multipart
        start = data.find(b"%PDF")
        if start < 0:
            return ""
        data = data[start:]

    # Prefer pypdf
    try:
        from io import BytesIO
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data), strict=False)
        parts: list[str] = []
        for page in reader.pages[:50]:  # cap pages for performance
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                parts.append(t)
        joined = "\n".join(parts).strip()
        if joined:
            return joined[:200_000]
    except Exception:
        pass

    # Fallback: pull printable runs + common PDF string literals (...) 
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
    # Also long printable ASCII runs
    for m in re.finditer(r"[ -~]{12,}", raw):
        texts.append(m.group(0))
    return "\n".join(texts)[:200_000]


def _extract_plain_text_bytes(data: bytes) -> str:
    if not data:
        return ""
    # Skip obvious binary without text
    if data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff") or data.startswith(b"GIF8"):
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


def extract_upload_text_for_rules(raw_bytes: bytes, content_type: str = "", raw_text: str = "") -> str:
    """
    Pull text from an upload body so Guard Rules can scan file contents
    (PDF insides, plain text, multipart attachments).
    """
    parts: list[str] = []
    ct = (content_type or "").lower()
    data = raw_bytes or b""

    # Direct PDF body
    if "pdf" in ct or data[:5] == b"%PDF" or b"%PDF" in data[:4096]:
        pdf_text = _extract_pdf_text(data)
        if pdf_text:
            parts.append(pdf_text)

    # Multipart / mixed: scan each binary island for PDF + text
    if "multipart" in ct or b"%PDF" in data or b"filename=" in data[:8000]:
        # Split roughly on boundaries
        for chunk in re.split(rb"\r\n--[^\r\n]+", data):
            if len(chunk) < 20:
                continue
            if b"%PDF" in chunk[:2000] or chunk.lstrip().startswith(b"%PDF"):
                t = _extract_pdf_text(chunk)
                if t:
                    parts.append(t)
            else:
                # strip headers
                body = chunk
                if b"\r\n\r\n" in chunk:
                    body = chunk.split(b"\r\n\r\n", 1)[1]
                t = _extract_plain_text_bytes(body)
                if t and len(t) > 20:
                    parts.append(t)

    # Plain / json text bodies
    if raw_text and len(raw_text) > 20:
        parts.append(raw_text[:200_000])
    elif not parts:
        t = _extract_plain_text_bytes(data)
        if t:
            parts.append(t)

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


def match_guard_rules_on_text(text: str) -> tuple[bool, str, str]:
    """
    Apply active Guard Rules to arbitrary text (prompt or file content).
    Returns (matched, rule_name, action).
    """
    if not text or len(text.strip()) < 3:
        return False, "", ""
    rules = get_guard_rules()
    for r in rules:
        try:
            if r["regex"].search(text):
                return True, r.get("name", "Guard Rule"), (r.get("action") or "BLOCK").upper()
        except Exception:
            continue
    return False, "", ""


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

    # 3. Slot regex only when a known chat RPC id is present (skip telemetry batchexecute).
    if any(rpc in req_str for rpc in GEMINI_CHAT_RPCS):
        for pat in (
            r'\[\s*\[\s*"((?:[^"\\]|\\.)+?)"\s*,\s*0\s*,',
            r'\\"((?:[^"\\]|\\.)+?)\\"\s*,\s*0\s*,',
        ):
            m = re.search(pat, req_str)
            if m:
                cand = _normalize_prompt(m.group(1))
                if _is_valid_user_prompt(cand):
                    return cand

    return ""


def extract_prompt(body_bytes: bytes, content_type: str = "", host: str = "") -> str | None:
    """
    Extract ONLY the exact user-typed prompt text from a request body.
    Never returns raw JSON / API metadata / Cloudflare challenge blobs.
    """
    if not body_bytes:
        return None

    try:
        text = body_bytes.decode("utf-8", errors="ignore")
        if not text.strip():
            return None

        ct = (content_type or "").lower()

        # Gemini: never walk generic JSON/form fields — those are request ids.
        if is_gemini_host(host) or "f.req=" in text or "req0___data__" in text or text.startswith("f.req="):
            gemini_prompt = extract_gemini_prompt(text)
            return _clean_prompt_text(gemini_prompt) if gemini_prompt else None

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
                return None
            return _extract_from_json(data)

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


def send_to_backend(platform: str, domain: str, prompt: str, client_ip: str, url: str, method: str) -> tuple[bool, str, str, str, str]:
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
            "metadata": {
                "domain": domain,
                "url": url,
                "method": method,
                "agent_id": UNIFAI_AGENT_ID,
                "agent_hostname": UNIFAI_AGENT_HOSTNAME,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        # AI Guard Bot may call an LLM — allow enough time for provider round-trip
        with urllib.request.urlopen(req, timeout=22) as response:
            if response.status == 200:
                res_data = json.loads(response.read().decode("utf-8"))
                allowed = res_data.get("allowed", True)
                rule_triggered = res_data.get("rule_triggered", "")
                action = res_data.get("action", "Allowed")
                redacted_prompt = res_data.get("forward_prompt") or res_data.get("redacted_prompt", prompt)
                # If backend says Warned but returned the raw prompt, append warning locally.
                if (action or "") == "Warned" and redacted_prompt == prompt:
                    redacted_prompt = _warned_forward(prompt, res_data.get("warning_message", ""))
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
        if rule_action == "REDACT":
            rule_action = "WARN"
        if rule_action == "BLOCK":
            return False, r["name"], "Blocked", prompt, _security_reply_text(r["name"], r.get("warning_message", ""))
        if rule_action == "WARN":
            return True, r["name"], "Warned", _warned_forward(prompt, r.get("warning_message", "")), ""

    # Backend / evaluator miss. With AI Guard Bot rules configured, fail-closed
    # so DLP cannot be silently bypassed when the backend is down/slow.
    if _fail_open():
        return True, "", "Allowed", prompt, ""
    if has_ai_bot_rules():
        return (
            False,
            "AI Guard Bot",
            "Blocked",
            prompt,
            "UnifAI Guard could not reach the security backend to evaluate this prompt. Blocked for safety.",
        )
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
    for r in get_guard_rules():
        if (r.get("name") or "").strip() == name:
            return (r.get("warning_message") or "").strip()
    return ""


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

    if "copilot" in host_l or "bing.com" in host_l or "sydney" in host_l:
        frames = _ws_frames_copilot(reply)
    elif "claude.ai" in host_l or "anthropic.com" in host_l:
        frames = _ws_frames_claude(reply)
    elif "chatgpt.com" in host_l or "openai.com" in host_l or "deepseek.com" in host_l:
        frames = _ws_frames_openai(reply)
    elif "perplexity.ai" in host_l:
        frames = _ws_frames_perplexity(reply)
    elif "gemini.google.com" in host_l or "bard.google.com" in host_l or "googleapis.com" in host_l:
        frames = _ws_frames_gemini(reply)
    elif any(x in host_l for x in ("grok.", "x.ai", "poe.com", "mistral.ai", "huggingface.co")):
        frames = _ws_frames_openai(reply)
    else:
        # Any other Target Website you add
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

    # Wire-format routing for in-chat replies. Any admin-added host can hit these
    # when the request looks like that product's API (not a default target list).
    chatgpt_body = None
    try:
        parsed = json.loads((flow.request.content or b"").decode("utf-8", errors="ignore") or "")
        if isinstance(parsed, dict) and isinstance(parsed.get("messages"), list):
            if "conversation_id" in parsed or "parent_message_id" in parsed:
                chatgpt_body = parsed
            elif any(isinstance(m, dict) and isinstance(m.get("author"), dict) for m in parsed["messages"]):
                chatgpt_body = parsed
    except Exception:
        chatgpt_body = None

    # ── ChatGPT-shaped conversation APIs ──
    if chatgpt_body is not None or "chatgpt.com" in host_l or "chat.openai.com" in host_l:
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

    # ── Claude.ai ──
    if "claude.ai" in host_l:
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

    if "anthropic.com" in host_l:
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

    # ── Microsoft Copilot / Bing (any host with copilot or bing in the name) ──
    if "copilot" in host_l or "bing.com" in host_l or "sydney" in host_l:
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

    # ── Perplexity ──
    if "perplexity.ai" in host_l:
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

    # ── Gemini / Bard ──
    if (
        "gemini.google.com" in host_l
        or "bard.google.com" in host_l
        or "generativelanguage.googleapis.com" in host_l
        or ("google.com" in host_l and "batchexecute" in path)
    ):
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

    # ── Grok / Poe / Mistral / HuggingFace / DeepSeek — OpenAI-compatible SSE ──
    if any(
        x in host_l
        for x in (
            "deepseek.com", "poe.com", "mistral.ai", "huggingface.co",
            "grok.com", "grok.x.ai", "x.ai",
        )
    ) or "event-stream" in accept or "chat" in path or "stream" in path or "completion" in path:
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


# ─────────────────────────────────────────────
# mitmproxy Addon Class
# ─────────────────────────────────────────────

class BrowserAIInterceptor:

    def __init__(self):
        print(f"[UnifAI Proxy] Started. Backend: {UNIFAI_BACKEND_URL}")
        print(f"[UnifAI Proxy] Fetching target domains & guard rules every {CACHE_TTL}s from backend API.")

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

        if flow.request.method not in ("POST", "PUT", "PATCH"):
            return

        path = flow.request.path
        client_ip = get_client_ip(flow)

        # ── File Upload Detection (before noise filter) ──
        raw_bytes = flow.request.content or b""
        content_type = flow.request.headers.get("content-type", "")

        try:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = ""

        is_upload, upload_reason = detect_file_upload(flow, raw_text)

        # Always scan upload body with Guard Rules (PDF insides + text files)
        file_rule_hit = False
        file_rule_name = ""
        file_rule_action = ""
        if is_upload:
            upload_text = extract_upload_text_for_rules(raw_bytes, content_type, raw_text)
            file_rule_hit, file_rule_name, file_rule_action = match_guard_rules_on_text(upload_text)
            if file_rule_hit:
                print(
                    f"[UnifAI Proxy] FILE CONTENT RULE HIT | {host} | "
                    f"rule={file_rule_name} action={file_rule_action} chars={len(upload_text)}"
                )

        block_all_uploads = is_upload and controls_active("block_upload")
        # For file uploads: legacy REDACT treated as BLOCK; WARN also blocks attachments (safer)
        block_for_rule = bool(
            is_upload and file_rule_hit and file_rule_action in ("BLOCK", "REDACT", "WARN")
        )
        # WARN on file content still blocks upload (safer for attachments)
        if block_all_uploads or block_for_rule:
            reason = upload_reason
            blocked_reason = "Block Upload"
            upload_warn = (get_control_settings().get("upload_warning") or "").strip()
            base_upload_msg = upload_warn or "Upload block"
            # Prompt Logs: admin warning text; rule hits append " -- {policy name}"
            prompt_log = base_upload_msg
            if block_for_rule:
                reason = f"Guard Rule in file: {file_rule_name}"
                blocked_reason = file_rule_name or "Guard Rule (file content)"
                rule_warn = _warning_for_rule_name(file_rule_name)
                # Prefer rule's own warning as the left side when set; else upload policy warning
                left = (rule_warn or base_upload_msg).strip() or "Upload block"
                prompt_log = f"{left} -- {file_rule_name}" if file_rule_name else left

            should_log = not is_duplicate_event(
                domain,
                f"upload-block|{blocked_reason}|{reason}",
                ttl=BLOCK_DEDUPE_TTL,
            )
            if should_log:
                print(f"[UnifAI Proxy] FILE UPLOAD BLOCKED | {client_ip} → {host} | Reason: {reason}")
                try:
                    payload = json.dumps({
                        "platform": platform,
                        "prompt": prompt_log,
                        "client_ip": client_ip,
                        "agent_id": UNIFAI_AGENT_ID,
                        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                        "metadata": {
                            "domain": domain,
                            "url": flow.request.url,
                            "method": flow.request.method,
                            "is_blocked": True,
                            "blocked_reason": blocked_reason,
                            "upload_scan": True,
                            "agent_id": UNIFAI_AGENT_ID,
                            "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                        },
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass

            # Same text employees / chat replies see
            msg = prompt_log if (block_for_rule or block_all_uploads) else ""
            if is_chat_path(path, host) and msg:
                make_blocked_response(flow, blocked_reason, host, reply_text=msg)
                return
            flow.response = http.Response.make(
                403,
                json.dumps({
                    "error": {
                        "message": msg,
                        "type": "file_upload_blocked",
                        "code": "file_content_rule_blocked" if block_for_rule else "file_upload_restricted",
                        "rule": file_rule_name or None,
                    },
                    "detail": f"File upload blocked: {reason}",
                    "status": "PERMISSION_DENIED",
                }).encode("utf-8"),
                {
                    "Content-Type": "application/json; charset=utf-8",
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "no-store",
                }
            )
            return
        elif is_upload:
            # Clean file upload allowed: Log audit event to backend
            fname = extract_filename_from_upload(flow, raw_text)
            clean_log = f"[FILE UPLOAD] {fname}" if fname else f"[FILE UPLOAD] {upload_reason or 'File attachment'}"
            should_log = not is_duplicate_event(
                domain,
                f"upload-allowed|{fname or upload_reason}",
                ttl=BLOCK_DEDUPE_TTL,
            )
            if should_log:
                print(f"[UnifAI Proxy] FILE UPLOAD ALLOWED | {client_ip} → {host} | {clean_log}")
                try:
                    payload = json.dumps({
                        "platform": platform,
                        "prompt": clean_log,
                        "client_ip": client_ip,
                        "agent_id": UNIFAI_AGENT_ID,
                        "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                        "metadata": {
                            "domain": domain,
                            "url": flow.request.url,
                            "method": flow.request.method,
                            "is_blocked": False,
                            "upload_scan": True,
                            "file_name": fname or "attachment",
                            "agent_id": UNIFAI_AGENT_ID,
                            "agent_hostname": UNIFAI_AGENT_HOSTNAME,
                        },
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept",
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass

        # Gemini fires many extra POSTs (session ids, counters). Log only the chat submit.
        if is_gemini_host(host) and not is_gemini_chat_submit(path, raw_text):
            return

        # Only inspect real chat/prompt endpoints — ignore challenges & analytics
        if not is_chat_path(path, host):
            return

        if is_noise(path):
            return

        # ── Prompt Extraction ──
        if is_noise(path, raw_text):
            return

        prompt = extract_prompt(raw_bytes, content_type, host=host)
        if not prompt or len(prompt.strip()) < 1:
            # Help debug Gemini/Copilot misses without flooding logs
            if any(x in (domain or "") for x in ("gemini", "copilot", "bing")) and len(raw_text) > 20:
                print(f"[UnifAI Proxy] No prompt extracted | {platform} ({domain}) path={path[:80]!r} bytes={len(raw_bytes)}")
            return
        if not looks_like_user_prompt(prompt):
            return
        if _is_google_wire_blob(prompt):
            return

        # Gemini batchexecute background RPCs: only StreamGenerate / known chat RPCs.
        path_l = (path or "").lower()
        compact = path_l.replace("_", "")
        if "batchexecute" in path_l and "streamgenerate" not in compact:
            if not any(rpc in raw_text for rpc in GEMINI_CHAT_RPCS):
                return

        # ChatGPT fires POSTs while typing. Predict only after Enter/send.
        if is_unsubmitted_chat_body(path, raw_text) or is_composer_typing_draft(domain, prompt):
            return

        # Skip duplicate / typing-repeat submissions
        if is_duplicate_prompt(domain, prompt):
            return

        print(f"[UnifAI Proxy] Intercepted prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")

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
                new_content = raw_text.replace(prompt, redacted_prompt)
                flow.request.content = new_content.encode("utf-8")
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

        if is_gemini_host(host):
            # HTTP path must be StreamGenerate; empty WS path relies on extract_gemini_prompt
            ws_path = flow.request.path or ""
            if ws_path and not is_gemini_chat_submit(ws_path, content):
                return

        if is_noise(flow.request.path, content):
            return

        prompt = extract_prompt(content.encode("utf-8"), "application/json", host=host)
        if not prompt or prompt.strip() in ("{}", "[]", "ping", "pong"):
            return
        if not looks_like_user_prompt(prompt):
            return

        if is_unsubmitted_chat_body(flow.request.path, content) or is_composer_typing_draft(domain, prompt):
            return

        if is_duplicate_prompt(domain, prompt):
            return

        client_ip = get_client_ip(flow)
        print(f"[UnifAI Proxy] WebSocket prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")

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
            msg.text = msg.text.replace(prompt, redacted_prompt)


addons = [BrowserAIInterceptor()]
