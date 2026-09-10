# Part of UnifAI browser_ai_proxy — loaded via browser_ai_proxy.py into one shared namespace.
# Do not import this file directly.



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
    # Digit-only text is a valid user prompt (IDs, math, OTPs). Do not drop it.
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


def _is_internal_wire_text(text: str) -> bool:
    """Internal RPC ids, pubsub actions, and wire fragments — not user-typed chat."""
    t = (text or "").strip()
    if not t:
        return True
    if _is_typed_numeric_prompt(t):
        return False
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
    # Keep mostly-digit tokens (formatted IDs) — not opaque wire.
    if len(t) <= 14 and " " not in t:
        special = sum(1 for c in t if not c.isalnum() and c not in "._-'")
        digits = sum(1 for c in t if c.isdigit())
        if digits >= 3 and special <= 2 and all(c.isdigit() or c in "+#*-(). " for c in t):
            return False
        if special >= 1 and len(t) <= 10:
            return True
        if special >= 2:
            return True
        letters = sum(1 for c in t if c.isalpha())
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
    """Finished chat Send with user text → predict. Telemetry/sync must not.

    Confident Send (Claude/ChatGPT/Gemini/… shape): accept ANY non-empty typed
    text — letters, digits, symbols, 1 char or 1000+ — unless clear protocol junk.
    """
    if not prompt or not isinstance(prompt, str):
        return False
    text = prompt.strip()
    if len(text) < 1:
        return False
    if text.startswith("[FILE UPLOAD"):
        return False
    if _is_typing_or_draft_path(path, raw_text):
        return False
    if is_noise(path, raw_text):
        return False
    # File Send bodies embed PDF/doc text — only short user captions belong in Prompt Logs.
    if _send_carries_attachment(raw_text):
        if _looks_like_document_body_dump(text) or len(text) > 320:
            return False

    confident = _is_confident_chat_send(path, raw_text, raw_bytes)

    if confident:
        # Exact user Send — do not drop number/symbol/short text via wire heuristics.
        if _is_clear_protocol_junk(text):
            return False
        if _is_ide_non_chat_noise(text, domain=domain) or _is_ide_non_chat_noise(text, domain=host):
            if not _is_digit_heavy_user_text(text) and not _is_typed_numeric_prompt(text):
                return False
        # Draft coalesce happens at commit (wait_if_composer_unstable) — do not mutate here.
        if is_duplicate_event(domain, text, ttl=DEDUPE_TTL, mark=False):
            return False
        return True

    # Non-confident paths keep stricter filters (avoid telemetry false positives).
    if not looks_like_user_prompt(text):
        return False
    if _is_opaque_wire_blob(text):
        return False
    if _looks_like_binary_or_wire_garbage(text) and not _is_digit_heavy_user_text(text):
        return False
    if _is_ide_non_chat_noise(text, domain=domain) or _is_ide_non_chat_noise(text, domain=host):
        return False
    if _is_internal_wire_text(text) and not _is_digit_heavy_user_text(text):
        return False
    if _looks_like_filename_only(text):
        return False
    if not (
        is_chat_path(path, host, raw_text)
        or _path_has_chat_marker(path)
        or _is_clear_chat_submit(path, host or "", raw_text, raw_bytes)
    ):
        return False
    if len(text) < 2 and not text.isdigit() and not _is_typed_numeric_prompt(text):
        return False
    body = (raw_text or "").lstrip()
    if body.startswith(("{", "[")) and not _looks_like_chatgpt_body(body, raw_bytes):
        if not _path_has_chat_marker(path) and not is_chat_path(path, host, raw_text):
            return False
    if is_duplicate_event(domain, text, ttl=DEDUPE_TTL, mark=False):
        return False
    return True


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


def _composer_hold_seconds(text: str) -> float:
    n = len((text or "").strip())
    if n <= 3:
        return COMPOSER_STABILITY_HOLD_TINY
    if n <= 12:
        return COMPOSER_STABILITY_HOLD_SHORT
    return COMPOSER_STABILITY_HOLD


def _composer_related(a: str, b: str) -> bool:
    """True when one string is a typing prefix/extension of the other."""
    if not a or not b:
        return False
    if a == b:
        return True
    if a.startswith(b) or b.startswith(a):
        return True
    # Small edit distance growth (typo fix) within max grow window
    if abs(len(a) - len(b)) <= COMPOSER_DRAFT_MAX_GROW and (a[:3] == b[:3] if len(a) >= 3 and len(b) >= 3 else False):
        return True
    return False


def note_composer_observation(domain: str, prompt: str) -> None:
    """Observe phase: remember latest composer text for this Target family key."""
    text = (prompt or "").strip()
    if not text or not domain:
        return
    with _composer_lock:
        _composer_draft[domain] = (text, time.time())


def is_composer_typing_draft(domain: str, prompt: str) -> bool:
    """True when this fragment is clearly mid-edit vs the latest observation."""
    text = (prompt or "").strip()
    if not text or not domain:
        return False
    now = time.time()
    with _composer_lock:
        prev = _composer_draft.get(domain)
        _composer_draft[domain] = (text, now)
    if not prev:
        return False
    prev_text, prev_ts = prev
    elapsed = now - float(prev_ts)
    if elapsed >= COMPOSER_PREFIX_WINDOW:
        return False
    if text == prev_text:
        return False
    # Shorter than latest related text → stale keystroke request (skip).
    if prev_text.startswith(text) and len(prev_text) > len(text):
        return True
    # We just grew from prev within window — still typing; commit waits for quiet.
    if text.startswith(prev_text) and 1 <= (len(text) - len(prev_text)) <= COMPOSER_DRAFT_MAX_GROW:
        return False
    if prev_text.startswith(text) and 1 <= (len(prev_text) - len(text)) <= COMPOSER_DRAFT_MAX_GROW:
        return True
    return False


def wait_if_composer_unstable(domain: str, prompt: str) -> str | None:
    """Commit phase for ALL monitored domains.

    Many AI sites (Grok, Copilot, …) POST every keystroke as a chat-shaped request.
    We OBSERVE those, but COMMIT predict only after the composer text is quiet
    for an adaptive hold — so "h" then "hi" becomes one predict: "hi".

    Returns final text to evaluate, or None if this request was superseded.
    """
    text = (prompt or "").strip()
    if not text or not domain:
        return text or None

    note_composer_observation(domain, text)

    # Very long pastes / finished essays: still brief check for supersede, then go.
    hold = _composer_hold_seconds(text)
    if len(text) > COMPOSER_HOLD_MAX_LEN:
        hold = min(hold, 0.25)

    deadline = time.time() + hold
    while time.time() < deadline:
        time.sleep(0.05)
        with _composer_lock:
            cur = _composer_draft.get(domain)
        if not cur:
            break
        cur_text, cur_ts = cur
        cur_text = (cur_text or "").strip()
        if not cur_text:
            break

        if cur_text != text:
            if _composer_related(cur_text, text):
                if len(cur_text) > len(text):
                    # Longer typing won — drop this stale keystroke request.
                    return None
                # We grew (or matched longer stored) — follow the latest string.
                text = cur_text
                hold = _composer_hold_seconds(text)
                deadline = max(deadline, time.time() + hold * 0.65)
                continue
            # Unrelated new prompt — stop waiting; evaluate what we have.
            break

        # Same text: commit once it has been quiet long enough.
        quiet = time.time() - float(cur_ts)
        need = _composer_hold_seconds(text)
        if quiet >= need * 0.85 or quiet >= COMPOSER_DRAFT_TTL:
            break

    with _composer_lock:
        cur = _composer_draft.get(domain)
    if cur:
        cur_text = (cur[0] or "").strip()
        if cur_text and cur_text != text and _composer_related(cur_text, text):
            if len(cur_text) > len(text):
                return None
            text = cur_text

    # Final guard: never commit a proper prefix of the live composer within PREFIX_WINDOW.
    with _composer_lock:
        cur = _composer_draft.get(domain)
    if cur:
        cur_text, cur_ts = cur
        cur_text = (cur_text or "").strip()
        if (
            cur_text
            and text != cur_text
            and cur_text.startswith(text)
            and len(cur_text) > len(text)
            and (time.time() - float(cur_ts)) <= COMPOSER_PREFIX_WINDOW
        ):
            return None

    return text


def clear_composer_state(domain: str) -> None:
    if domain:
        with _composer_lock:
            _composer_draft.pop(domain, None)


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
