# Part of UnifAI browser_ai_proxy — loaded via browser_ai_proxy.py into one shared namespace.
# Do not import this file directly.



def _security_reply_text(rule_triggered: str, warning_message: str = "") -> str:
    """Admin block message first; otherwise a clear default that still names the rule."""
    w = (warning_message or "").strip()
    if w:
        return w
    name = (rule_triggered or "").strip()
    if name:
        return f"Blocked by UnifAI Guard ({name})."
    return "This request was blocked by UnifAI Guard."


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

    # ── OpenAI-compatible SSE (Accept/path/body stream flag — any admin-added domain) ──
    raw_low = (raw_body or "").lower()
    wants_stream = (
        "event-stream" in accept
        or "chat/completions" in path
        or "/stream" in path
        or path.endswith("/stream")
        or "stream" in path and ("completion" in path or "chat" in path or "generate" in path)
        or '"stream":true' in raw_low.replace(" ", "")
        or '"stream": true' in raw_low
    )
    if wants_stream or "completion" in path:
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

    # ── Fallback for ANY other Target Website ──
    # Many UIs (Abacus, Poe, custom chat apps) ignore plain OpenAI JSON and keep spinning.
    # Emit a multi-shape body + SSE twin so at least one field the SPA reads shows the block message.
    multi = {
        "id": "unifai-security-block",
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": msg},
            "delta": {"role": "assistant", "content": msg},
            "text": msg,
            "finish_reason": "stop",
        }],
        "message": {
            "id": "unifai-security-block",
            "role": "assistant",
            "author": {"role": "assistant"},
            "content": msg,
            "text": msg,
            "parts": [msg],
            "content_type": "text",
        },
        "messages": [{"role": "assistant", "content": msg, "text": msg}],
        "text": msg,
        "content": msg,
        "answer": msg,
        "reply": msg,
        "response": msg,
        "output": msg,
        "result": {
            "content": [{"type": "text", "text": msg}],
            "message": msg,
            "text": msg,
        },
        "data": {"message": msg, "text": msg, "content": msg, "answer": msg},
        "error": None,
        "unifai": {
            "blocked": True,
            "rule": rule_triggered,
            "message": msg,
        },
        # Some SPAs surface server "detail" / "error_message" even on HTTP 200.
        "detail": msg,
        "error_message": msg,
        "status": "ok",
        "success": True,
    }
    # Prefer SSE when the path looks chatty — stops infinite "thinking" loaders on unknown sites.
    chatty_path = any(
        x in path
        for x in (
            "chat", "message", "completion", "generate", "ask", "prompt",
            "conversation", "thread", "query", "agent", "llm", "ai/",
        )
    )
    if chatty_path:
        sse_lines = (
            f"data: {json.dumps({'text': msg, 'message': msg, 'content': msg, 'role': 'assistant'}, ensure_ascii=False)}\n\n"
            f"data: {json.dumps({'choices': [{'delta': {'content': msg}, 'finish_reason': None}]}, ensure_ascii=False)}\n\n"
            f"data: {json.dumps({'choices': [{'delta': {}, 'finish_reason': 'stop'}]}, ensure_ascii=False)}\n\n"
            f"data: {json.dumps(multi, ensure_ascii=False)}\n\n"
            "data: [DONE]\n\n"
        )
        flow.response = http.Response.make(
            200,
            sse_lines.encode("utf-8"),
            {**common_headers, "Content-Type": "text/event-stream; charset=utf-8"},
        )
        return

    flow.response = http.Response.make(
        200,
        json.dumps(multi, ensure_ascii=False).encode("utf-8"),
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
