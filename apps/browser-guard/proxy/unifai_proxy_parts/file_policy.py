# Part of UnifAI browser_ai_proxy — loaded via browser_ai_proxy.py into one shared namespace.
# Do not import this file directly.



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
) -> tuple[bool, str, str, int, bool]:
    """
    On chat Send with a real attached file (any monitored AI domain):
      - Block Upload ON  → block on Send only (file may attach in UI first)
      - Block Upload OFF → extract PDF/image/Office/voice text → Guard Rules
          BLOCK        → block Send
          REDACT       → log Redacted, allow Send (+ chat notice when possible)
          no match     → Allowed

    Multi-file + caption: ALL files (any count) + typed text are evaluated together
    once, then each file is logged with the shared verdict.

    Returns (should_block, block_message, redact_notice, files_processed, caption_consumed).
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
        return False, "", "", 0, False

    if not cached_list and has_attach:
        inlines = extract_all_inline_attachment_bytes(raw_text or "")
        if inlines:
            cached_list = []
            for idx, (inline_bytes, inline_ct, inline_name) in enumerate(inlines):
                cached_list.append({
                    "file_name": inline_name or f"attachment_{idx + 1}",
                    "content_type": inline_ct or content_type,
                    "raw_bytes": inline_bytes,
                    "ts": time.time(),
                    "cache_uid": f"inline|{time.time():.6f}|{idx}|{len(inline_bytes)}",
                })
        else:
            inline_bytes, inline_ct, inline_name = extract_inline_attachment_bytes(raw_text or "")
            if inline_bytes:
                cached_list = [{
                    "file_name": inline_name or "attachment",
                    "content_type": inline_ct or content_type,
                    "raw_bytes": inline_bytes,
                    "ts": time.time(),
                    "cache_uid": f"inline|{time.time():.6f}",
                }]

    # Cache miss but Send clearly carries file/voice — never fail-open for Block Upload.
    if not cached_list and has_attach:
        get_control_settings()
        hint = (file_name_hint or "").strip() or extract_attachment_filename_from_send(raw_text or "") or "attachment"
        tag = "[VOICE UPLOAD]" if (
            chat_carries_attachment(raw_text) and _extract_transcript_fields_from_json(raw_text or "")
        ) or _looks_like_audio(b"", content_type, hint) else "[FILE UPLOAD]"
        if controls_active("block_upload"):
            warn = (get_control_settings().get("upload_warning") or "").strip() or "File/voice uploads are blocked by admin policy."
            msg = warn
            dedupe_key = f"upload-send-block-all-nocache|{hint}"
            if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
                print(f"[UnifAI Proxy] FILE/VOICE SEND BLOCKED (no cache, Block Upload ON) | {client_ip} → {host}")
                ok = post_upload_intercept(
                    platform=platform,
                    prompt=f"{tag} {hint} — Blocked (Block Upload)",
                    client_ip=client_ip,
                    domain=domain,
                    url=url,
                    method=method,
                    file_name=hint,
                    is_blocked=True,
                    blocked_reason="Block Upload",
                    scan_guard={"cache_miss": True},
                )
                if ok:
                    mark_duplicate_event(domain, dedupe_key)
            return True, msg, "", 0, False

        # Voice/transcript or caption text still get regex+bot even without file bytes.
        transcript = _extract_transcript_fields_from_json(raw_text or "")
        caption = ""
        try:
            from_body = extract_prompt_universal((raw_text or "").encode("utf-8", errors="ignore"), content_type or "", host, url)
            if from_body and looks_like_user_prompt(from_body):
                caption = from_body.strip()
        except Exception:
            caption = ""
        scan_text = "\n".join(x for x in (transcript, caption) if x).strip()
        if scan_text:
            rule_hit, rule_name, rule_action = match_guard_rules_on_text(scan_text)
            rule_action = (rule_action or "").upper()
            if rule_action == "WARN":
                rule_action = "REDACT"
            if platform and domain and (has_ai_bot_rules() or get_guard_rules()):
                try:
                    allowed, rt, action, _, _, eval_err = send_to_backend(
                        platform, domain, scan_text[:50_000], client_ip, url, method or "POST",
                        evaluation_only=True,
                        extracted_text=scan_text[:50_000],
                    )
                    if not eval_err:
                        rule_hit, rule_name, rule_action = _merge_file_scan_backend(
                            rule_hit, rule_name, rule_action, allowed, rt, action or "",
                        )
                        rule_action = (rule_action or "").upper()
                        if rule_action == "WARN":
                            rule_action = "REDACT"
                except Exception as e:
                    print(f"[UnifAI Proxy] transcript/caption scan failed (allowed): {e}")
            cap_done = bool(caption)
            if rule_hit and rule_action == "BLOCK":
                msg = _security_reply_text(rule_name, "") or f"Blocked by Guard Rule ({rule_name})"
                dedupe_key = f"upload-send-block-nocache|{rule_name}|{hint}"
                if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
                    print(f"[UnifAI Proxy] FILE/VOICE SEND BLOCKED (transcript/caption) | {rule_name}")
                    ok = post_upload_intercept(
                        platform=platform,
                        prompt=f"{tag} {hint} — Blocked ({rule_name})",
                        client_ip=client_ip,
                        domain=domain,
                        url=url,
                        method=method,
                        file_name=hint,
                        is_blocked=True,
                        blocked_reason=rule_name,
                        extracted_text=scan_text[:50_000],
                        scan_guard={
                            "cache_miss": True,
                            "scan_rule_hit": True,
                            "scan_rule_name": rule_name,
                            "scan_rule_action": "BLOCK",
                        },
                    )
                    if ok:
                        mark_duplicate_event(domain, dedupe_key)
                return True, msg, "", 1, cap_done
            if rule_hit and rule_action == "REDACT":
                notice = _warning_for_rule_name(rule_name) or "UnifAI Guard redaction policy."
                dedupe_key = f"upload-send-redact-nocache|{rule_name}|{hint}"
                if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
                    post_upload_intercept(
                        platform=platform,
                        prompt=f"{tag} {hint} — Redacted ({rule_name})",
                        client_ip=client_ip,
                        domain=domain,
                        url=url,
                        method=method,
                        file_name=hint,
                        extracted_text=scan_text[:50_000],
                        scan_guard={
                            "cache_miss": True,
                            "scan_rule_hit": True,
                            "scan_rule_name": rule_name,
                            "scan_rule_action": "REDACT",
                        },
                    )
                    mark_duplicate_event(domain, dedupe_key)
                return False, "", notice, 1, cap_done
            dedupe_key = f"upload-send-allow-nocache|{hint}|{scan_text[:40]}"
            if not is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
                post_upload_intercept(
                    platform=platform,
                    prompt=f"{tag} {hint} — Allowed",
                    client_ip=client_ip,
                    domain=domain,
                    url=url,
                    method=method,
                    file_name=hint,
                    extracted_text=scan_text[:50_000],
                    scan_guard={"cache_miss": True},
                )
                mark_duplicate_event(domain, dedupe_key)
            return False, "", "", 1, cap_done

        return False, "", "", 0, False

    # Dedup by cache_uid ONLY — many ChatGPT/Claude images share name "attachment".
    deduped: list[dict] = []
    seen_uids: set[str] = set()
    for entry in cached_list:
        uid = str(entry.get("cache_uid") or id(entry))
        if uid in seen_uids:
            continue
        seen_uids.add(uid)
        deduped.append(entry)
    cached_list = deduped[:_UPLOAD_FILE_QUEUE_MAX]
    cached_list = _bind_real_filenames_to_cached_uploads(cached_list, raw_text or "")

    caption = ""
    try:
        from_body = extract_prompt_universal(
            (raw_text or "").encode("utf-8", errors="ignore"),
            content_type or "",
            host,
            url,
        )
        if (
            from_body
            and looks_like_user_prompt(from_body)
            and len(from_body.strip()) <= 500
            and not _looks_like_document_body_dump(from_body)
        ):
            caption = from_body.strip()
    except Exception:
        caption = ""

    get_control_settings()
    block_all = controls_active("block_upload")
    base_upload_msg = (get_control_settings().get("upload_warning") or "").strip() or "Upload block"

    file_rows: list[dict] = []
    all_images: list[str] = []
    text_parts: list[str] = []
    if caption:
        text_parts.append(f"USER_CAPTION:\n{caption}")

    hint = (file_name_hint or "").strip()
    for i, cached in enumerate(cached_list):
        fname = (cached.get("file_name") or "").strip() or (hint if i == 0 else "") or ""
        if _is_fake_upload_name(fname):
            raw0 = cached.get("raw_bytes") or b""
            fname = _default_name_from_bytes(
                bytes(raw0) if isinstance(raw0, (bytes, bytearray)) else b"",
                cached.get("content_type") or content_type or "",
                i,
            )
        cached_bytes = cached.get("raw_bytes") or b""
        if not isinstance(cached_bytes, (bytes, bytearray)):
            cached_bytes = b""
        cached_ct = (cached.get("content_type") or content_type or "").strip()
        display_label = _display_label_for_upload(fname, bytes(cached_bytes), cached_ct)
        scanned, local_hit, local_name, local_action, excerpt, upload_images, _, _ = _scan_upload_for_rules(
            bytes(cached_bytes),
            cached_ct,
            raw_text or "",
            fname,
            cached,
            platform=platform,
            domain=domain,
            client_ip=client_ip,
            url=url,
            method=method,
            skip_backend=True,
            extra_context=caption,
        )
        for img in upload_images or []:
            if len(all_images) >= _MULTI_FILE_VISION_MAX:
                break
            if img and img not in all_images:
                all_images.append(img)
        if scanned:
            text_parts.append(f"[FILE:{fname}]\n{scanned}")
        file_rows.append({
            "file_label": display_label,
            "store_name": fname,
            "cached_bytes": bytes(cached_bytes),
            "cached_ct": cached_ct,
            "scanned": scanned or "",
            "excerpt": excerpt or "",
            "upload_images": upload_images or [],
            "local_hit": bool(local_hit),
            "local_name": local_name or "",
            "local_action": (local_action or "").upper(),
            "cache_uid": str(cached.get("cache_uid") or id(cached)),
        })

    combined_text = "\n\n".join(text_parts).strip()
    rule_hit = False
    rule_name = ""
    rule_action = ""
    for row in file_rows:
        if row["local_hit"]:
            rule_hit = True
            rule_name = row["local_name"] or rule_name
            act = row["local_action"]
            if act == "WARN":
                act = "REDACT"
            if act == "BLOCK" or rule_action != "BLOCK":
                rule_action = act or rule_action
    if combined_text:
        try:
            h, n, a = match_guard_rules_on_text(combined_text)
            a = (a or "").upper()
            if a == "WARN":
                a = "REDACT"
            if h:
                rule_hit = True
                if a == "BLOCK" or not rule_action:
                    rule_name, rule_action = n or rule_name, a or rule_action
                elif not rule_name:
                    rule_name, rule_action = n, a
        except Exception as e:
            print(f"[UnifAI Proxy] combined multi-file regex failed (allowed): {e}")

    scan_evaluated = False
    scan_eval_error = ""
    has_regex = bool(get_guard_rules())
    # Instant path: local regex already BLOCK → skip slow AI Guard Bot (same as typed prompts).
    need_backend = (
        platform
        and domain
        and (combined_text or all_images)
        and (has_ai_bot_rules() or has_regex)
        and not (rule_hit and (rule_action or "").upper() == "BLOCK")
    )
    if need_backend:
        try:
            eval_prompt = combined_text or (caption if caption else f"[FILE UPLOAD] {len(file_rows)} file(s)")
            allowed, rt, action, _, _, eval_err = send_to_backend(
                platform,
                domain,
                eval_prompt[:50_000],
                client_ip,
                url,
                method or "POST",
                upload_images=all_images[:_MULTI_FILE_VISION_MAX],
                evaluation_only=True,
                extracted_text=(combined_text or "")[:50_000],
            )
            if eval_err:
                scan_eval_error = str(eval_err).strip()
                scan_evaluated = False
                print(f"[UnifAI Proxy] multi-file combined eval_error: {scan_eval_error}")
            else:
                scan_evaluated = True
                rule_hit, rule_name, rule_action = _merge_file_scan_backend(
                    rule_hit, rule_name, rule_action, allowed, rt, action or "",
                )
                rule_action = (rule_action or "").upper()
                if rule_action == "WARN":
                    rule_action = "REDACT"
        except Exception as e:
            scan_eval_error = str(e).strip()[:300] or "multi-file backend scan failed"
            print(f"[UnifAI Proxy] multi-file combined eval failed (allowed): {e}")
    elif rule_hit and (rule_action or "").upper() == "BLOCK":
        scan_evaluated = True

    labels = [r["file_label"] for r in file_rows]
    if len(labels) <= 4:
        labels_str = ", ".join(labels)
    else:
        labels_str = ", ".join(labels[:4]) + f" (+{len(labels) - 4} more)"
    caption_bit = f" | {caption}" if caption else ""
    n_files = len(file_rows)
    count_bit = f"{n_files} files: " if n_files > 1 else ""
    has_scan_content = bool(combined_text.strip() or all_images)
    block_for_rule = bool(rule_hit and rule_action == "BLOCK" and (has_scan_content or block_all))
    redact_for_rule = bool(rule_hit and rule_action == "REDACT" and not block_all and has_scan_content)
    scan_guard = _file_scan_guard_metadata(
        combined_text,
        all_images,
        rule_hit,
        rule_name,
        rule_action,
        scan_evaluated=scan_evaluated,
        scan_eval_error=scan_eval_error,
    )
    scan_guard["multi_file_count"] = n_files
    if caption:
        scan_guard["user_caption"] = caption[:500]

    should_block = False
    block_msg = ""
    redact_notice = ""

    if block_all or block_for_rule:
        should_block = True
        blocked_reason = "Block Upload" if block_all else (rule_name or "Guard Rule (file content)")
        if block_all:
            status = "Blocked (Block Upload)"
            block_msg = base_upload_msg
        else:
            rule_warn = _warning_for_rule_name(rule_name)
            left = (rule_warn or base_upload_msg).strip() or "Upload block"
            status = f"Blocked ({rule_name or 'policy'})"
            block_msg = f"{left} -- {rule_name}" if rule_name else left
        for idx, row in enumerate(file_rows):
            tag = _upload_log_tag(row["file_label"], row["cached_ct"], row["cached_bytes"])
            prompt_log = f"{tag} {count_bit}{labels_str}{caption_bit} — {status}"
            if n_files > 1:
                prompt_log = f"{tag} {row['file_label']} ({idx + 1}/{n_files}){caption_bit} — {status}"
            dedupe_key = f"upload-send-block|{blocked_reason}|{row['cache_uid']}"
            if is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
                continue
            print(f"[UnifAI Proxy] FILE SEND BLOCKED | {client_ip} → {host} | {row['file_label']} | multi={n_files}")
            ok = post_upload_intercept(
                platform=platform,
                prompt=prompt_log,
                client_ip=client_ip,
                domain=domain,
                url=url,
                method=method,
                file_name=row.get("store_name") or row["file_label"],
                is_blocked=True,
                blocked_reason=blocked_reason,
                raw_bytes=row["cached_bytes"],
                content_type=row["cached_ct"],
                extracted_text=combined_text or row["scanned"],
                upload_images=all_images if idx == 0 else row["upload_images"],
                scan_guard=scan_guard,
            )
            if ok:
                mark_duplicate_event(domain, dedupe_key)
        return True, block_msg, "", n_files, bool(caption)

    if redact_for_rule:
        redact_notice = _redact_notice_for_rule(rule_name)
        status = f"Redacted ({rule_name or 'policy'})"
        for idx, row in enumerate(file_rows):
            tag = _upload_log_tag(row["file_label"], row["cached_ct"], row["cached_bytes"])
            prompt_log = f"{tag} {row['file_label']} ({idx + 1}/{n_files}){caption_bit} — {status}" if n_files > 1 else f"{tag} {row['file_label']}{caption_bit} — {status}"
            dedupe_key = f"upload-send-redact|{rule_name}|{row['cache_uid']}"
            if is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
                continue
            print(f"[UnifAI Proxy] FILE SEND REDACTED | {client_ip} → {host} | {row['file_label']} | multi={n_files}")
            ok = post_upload_intercept(
                platform=platform,
                prompt=prompt_log,
                client_ip=client_ip,
                domain=domain,
                url=url,
                method=method,
                file_name=row.get("store_name") or row["file_label"],
                is_blocked=False,
                raw_bytes=row["cached_bytes"],
                content_type=row["cached_ct"],
                extracted_text=combined_text or row["scanned"],
                upload_images=all_images if idx == 0 else row["upload_images"],
                scan_guard=scan_guard,
            )
            if ok:
                mark_duplicate_event(domain, dedupe_key)
        return False, "", redact_notice, n_files, bool(caption)

    status = "Allowed"
    for idx, row in enumerate(file_rows):
        tag = _upload_log_tag(row["file_label"], row["cached_ct"], row["cached_bytes"])
        if n_files > 1:
            prompt_log = f"{tag} {row['file_label']} ({idx + 1}/{n_files}){caption_bit} — {status}"
        else:
            prompt_log = f"{tag} {row['file_label']}{caption_bit} — {status}"
        dedupe_key = f"upload-send-allowed|{row['cache_uid']}"
        if is_duplicate_event(domain, dedupe_key, ttl=BLOCK_DEDUPE_TTL, mark=False):
            continue
        print(f"[UnifAI Proxy] FILE SEND ALLOWED | {client_ip} → {host} | {prompt_log}")
        ok = post_upload_intercept(
            platform=platform,
            prompt=prompt_log,
            client_ip=client_ip,
            domain=domain,
            url=url,
            method=method,
            file_name=row.get("store_name") or row["file_label"],
            is_blocked=False,
            raw_bytes=row["cached_bytes"],
            content_type=row["cached_ct"],
            extracted_text=combined_text or row["scanned"],
            upload_images=all_images if idx == 0 else row["upload_images"],
            scan_guard=scan_guard,
        )
        if ok:
            mark_duplicate_event(domain, dedupe_key)
        else:
            print(f"[UnifAI Proxy WARNING] Allowed file log failed to post | {row['file_label']}")
    return False, "", "", n_files, bool(caption)


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
    """
    Log file event on Send.
    Always posts filename + extracted text (permanent in Prompt Logs).
    Also attaches file bytes (when present, capped) so backend can temp-store
    for ~10 minutes of View/Download, then auto-delete the file only.
    """
    metadata = {
        "domain": domain,
        "url": url,
        "method": method,
        "is_blocked": bool(is_blocked),
        "upload_scan": True,
        "file_name": file_name or "attachment",
        **_agent_metadata_fields(),
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

    safe_name = (file_name or "attachment").replace('"', "").replace("\r", "").replace("\n", "")
    if not safe_name:
        safe_name = "attachment"
    ctype = (content_type or "application/octet-stream").strip() or "application/octet-stream"

    # Prefer clean payload (multipart unwrap / PDF island) for View storage
    file_payload = b""
    file_ctype = ctype
    file_label = safe_name
    try:
        if raw_bytes and len(raw_bytes) >= 32:
            payload, sniffed_ct, sniffed_name = extract_upload_file_payload(
                raw_bytes, content_type, safe_name,
            )
            if payload and len(payload) >= 32:
                file_payload = payload
                if sniffed_ct:
                    file_ctype = sniffed_ct
                if sniffed_name and sniffed_name.lower() not in _FAKE_UPLOAD_NAMES:
                    file_label = sniffed_name.replace('"', "").replace("\r", "").replace("\n", "")
            else:
                # Raw body if it does not look like chat JSON metadata
                sample = raw_bytes[:64].lstrip()
                if sample[:1] not in (b"{", b"["):
                    file_payload = raw_bytes
    except Exception as e:
        print(f"[UnifAI Proxy] upload payload prepare failed (log without file): {e}")
        file_payload = b""

    max_attach = 20 * 1024 * 1024
    if len(file_payload) > max_attach:
        print(
            f"[UnifAI Proxy] upload file too large for temp View store "
            f"({len(file_payload)} bytes) — logging name+extract only"
        )
        file_payload = b""

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
        add_field("agent_type", UNIFAI_AGENT_TYPE or "endpoint")
        add_field("file_name", file_label)
        add_field("content_type", file_ctype)
        add_field("metadata", json.dumps(metadata))
        if file_payload:
            # Backend reads form file field "file" for 10-minute temp View storage
            hdr = (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"file\"; filename=\"{file_label}\"\r\n"
                f"Content-Type: {file_ctype}\r\n\r\n"
            ).encode("utf-8")
            parts.append(hdr)
            parts.append(file_payload)
            parts.append(b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        body = b"".join(parts)
        req = urllib.request.Request(
            f"{UNIFAI_BACKEND_URL}/api/browser-ai/intercept-file",
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        # Larger timeout when uploading file bytes
        timeout = 30 if file_payload else 12
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= getattr(resp, "status", 200) < 300:
                return True
    except Exception as e:
        print(f"[UnifAI Proxy WARNING] intercept-file failed, falling back to JSON: {e}")

    try:
        payload_json = json.dumps({
            "platform": platform,
            "prompt": prompt,
            "client_ip": client_ip,
            **_agent_wire_fields(),
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


def _looks_like_ole(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    """True for legacy OLE Compound File binary Office (.doc/.xls/.ppt)."""
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    # Careful: str.endswith(".doc") is also true for ".docx"
    if fn.endswith((".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm")):
        return False
    if fn.endswith((".doc", ".xls", ".ppt", ".msg")):
        return True
    if any(x in ct for x in (
        "msword", "ms-excel", "ms-powerpoint", "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint", "application/vnd.ms-office",
    )) and "openxmlformats" not in ct:
        # Content-type alone can lie (some clients send msword for docx) —
        # prefer magic bytes when present.
        if data and data[:2] == b"PK":
            return False
        if data and data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return True
        if data and len(data) >= 8:
            return data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        return True
    return bool(data) and data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _extract_binary_string_runs(data: bytes, *, min_chars: int = 4) -> str:
    """Harvest printable ASCII + UTF-16LE runs from binary office blobs (DLP-oriented)."""
    if not data:
        return ""
    # Cap work on huge uploads
    blob = data[: 12 * 1024 * 1024]
    parts: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        s = re.sub(r"\s+", " ", (s or "").strip())
        if len(s) < min_chars:
            return
        key = s[:120].lower()
        if key in seen:
            return
        seen.add(key)
        parts.append(s)

    # ASCII printable runs
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % min_chars, blob):
        try:
            add(m.group(0).decode("ascii", errors="ignore"))
        except Exception:
            continue
        if len(parts) >= 4000:
            break

    # UTF-16LE printable runs (common in .doc/.xls/.ppt)
    i = 0
    n = len(blob)
    while i + (min_chars * 2) <= n and len(parts) < 5000:
        if blob[i + 1] != 0 or not (0x20 <= blob[i] <= 0x7E):
            i += 1
            continue
        chars: list[str] = []
        j = i
        while j + 1 < n and blob[j + 1] == 0 and 0x20 <= blob[j] <= 0x7E:
            chars.append(chr(blob[j]))
            j += 2
            if len(chars) >= 800:
                break
        if len(chars) >= min_chars:
            add("".join(chars))
            i = j
        else:
            i += 1

    # Skip OLE/CFB structural noise tokens
    noise = (
        "root entry", "workbook", "worddocument", "powerpoint document",
        "summaryinformation", "documentsummaryinformation", "compobj",
        "1table", "0table", "data", "current user", "pictures",
    )
    cleaned = []
    for p in parts:
        low = p.lower()
        if low in noise or low.startswith(("_____", "objinfo", "workbook")):
            continue
        if re.fullmatch(r"[0-9A-Fa-f]{8,}", p):
            continue
        cleaned.append(p)
    return "\n".join(cleaned)[:200_000]


def _extract_ole_office_text(data: bytes, content_type: str = "", file_name: str = "") -> str:
    """Best-effort text from legacy .doc / .xls / .ppt (OLE CFB) without third-party libs."""
    if not data:
        return ""
    try:
        if not _looks_like_ole(data, content_type, file_name) and data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            fn = (file_name or "").lower()
            if not fn.endswith((".doc", ".xls", ".ppt")):
                return ""
        return _extract_binary_string_runs(data, min_chars=4)
    except Exception as e:
        print(f"[UnifAI Proxy] OLE office extract failed (allowed): {e}")
        return ""


def _looks_like_rtf(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if fn.endswith(".rtf") or "rtf" in ct or "richtext" in ct:
        return True
    head = (data or b"")[:64].lstrip()
    return head.startswith(b"{\\rtf")


def _extract_rtf_text(data: bytes) -> str:
    """Strip RTF control words and keep readable text for Guard Rules."""
    if not data:
        return ""
    try:
        raw = data[: 4 * 1024 * 1024].decode("latin-1", errors="ignore")
    except Exception:
        return ""
    if "\\rtf" not in raw[:200].lower() and not raw.lstrip().startswith("{\\rtf"):
        return ""
    try:
        # Hex escapes \'hh
        def _hex_repl(m: re.Match) -> str:
            try:
                return chr(int(m.group(1), 16))
            except Exception:
                return ""

        text = re.sub(r"\\'([0-9a-fA-F]{2})", _hex_repl, raw)
        # Unicode \uN?
        def _u_repl(m: re.Match) -> str:
            try:
                n = int(m.group(1))
                if n < 0:
                    n = 65536 + n
                return chr(n)
            except Exception:
                return ""

        text = re.sub(r"\\u(-?\d+)\??", _u_repl, text)
        # Drop destinations like {\*\...}
        text = re.sub(r"\{\\\*[^}]*\}", " ", text)
        # Control words / symbols
        text = re.sub(r"\\[a-zA-Z]+\d* ?", " ", text)
        text = re.sub(r"\\[^a-zA-Z\s]", " ", text)
        text = text.replace("{", " ").replace("}", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text[:200_000]
    except Exception as e:
        print(f"[UnifAI Proxy] RTF extract failed (allowed): {e}")
        return ""


def _looks_like_opendocument(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if fn.endswith((".odt", ".ods", ".odp")) or "opendocument" in ct:
        return True
    zdata = _office_zip_bytes(data) if data else None
    if not zdata:
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            names = set(zf.namelist())
            return "content.xml" in names and (
                "mimetype" in names or any(n.startswith("META-INF/") for n in names)
            )
    except Exception:
        return False


def _extract_opendocument_text(data: bytes) -> str:
    """Extract text from ODF (.odt/.ods/.odp) content.xml."""
    zdata = _office_zip_bytes(data)
    if not zdata:
        return ""
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            if "content.xml" not in zf.namelist():
                return ""
            xml = zf.read("content.xml")
    except Exception:
        return ""
    try:
        root = ET.fromstring(xml)
    except Exception:
        return ""
    parts: list[str] = []
    for el in root.iter():
        loc = _xml_local(el.tag)
        if loc in ("p", "h", "span", "a", "text", "s"):
            if el.text and el.text.strip():
                parts.append(el.text.strip())
            if el.tail and el.tail.strip():
                parts.append(el.tail.strip())
        elif el.text and el.text.strip() and loc not in ("script", "style", "binary-data"):
            # Spreadsheet cell values etc.
            if len(el.text.strip()) >= 2:
                parts.append(el.text.strip())
    # Dedupe adjacent
    out: list[str] = []
    prev = ""
    for p in parts:
        if p == prev:
            continue
        out.append(p)
        prev = p
    return "\n".join(out)[:200_000]


def _looks_like_html(data: bytes, content_type: str = "", file_name: str = "") -> bool:
    ct = (content_type or "").lower()
    fn = (file_name or "").lower()
    if fn.endswith((".html", ".htm", ".xhtml")) or "text/html" in ct or "xhtml" in ct:
        return True
    head = (data or b"")[:256].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:64]


def _extract_html_text(data: bytes) -> str:
    """Strip tags from HTML uploads so regex rules can scan page text."""
    if not data:
        return ""
    try:
        raw = data[: 4 * 1024 * 1024].decode("utf-8", errors="ignore")
        if not raw.strip():
            raw = data[: 4 * 1024 * 1024].decode("latin-1", errors="ignore")
    except Exception:
        return ""
    try:
        text = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
        text = re.sub(r"(?is)<!--.*?-->", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = (
            text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
        )
        text = re.sub(r"\s+", " ", text).strip()
        return text[:200_000]
    except Exception:
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
