# BrowserAIInterceptor — mitmproxy addon (loaded after responses_inject.py via MANIFEST).

class BrowserAIInterceptor:

    def __init__(self):
        print(f"[UnifAI Proxy] Started. Backend: {UNIFAI_BACKEND_URL}")
        print(
            "[UnifAI Proxy] Config refresh: background every 1s "
            "(targets/rules/controls) — request path is memory-only (instant Block/Monitor)."
        )
        _ensure_background_config_refresh()

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
        prompt = (prompt or "").strip()
        if not prompt:
            return
        # Same-text browser double-fire: reuse decision (never silent skip).
        if is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL, mark=False):
            self._apply_duplicate_http_prompt(flow, domain, platform, prompt, client_ip, raw_text)
            return

        print(f"[UnifAI Proxy] Intercepted prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")

        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt_coalesced(
            platform=platform,
            domain=domain,
            prompt=prompt,
            client_ip=client_ip,
            url=flow.request.url,
            method=flow.request.method,
        )
        # Mark only after evaluate so a failed first attempt can retry.
        mark_duplicate_event(domain, prompt)
        clear_composer_state(domain)

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

    def _apply_duplicate_http_prompt(
        self,
        flow: http.HTTPFlow,
        domain: str,
        platform: str,
        prompt: str,
        client_ip: str,
        raw_text: str,
    ) -> None:
        """ChatGPT/Claude often double-fire the same Send — never silent-allow the retry."""
        host = flow.request.pretty_host
        decision = get_remembered_guard_decision(domain, prompt)
        if decision is None:
            decision = evaluate_prompt_coalesced(
                platform=platform,
                domain=domain,
                prompt=prompt,
                client_ip=client_ip,
                url=flow.request.url,
                method=flow.request.method,
            )
        allowed, rule_triggered, action, redacted_prompt, reply_text = decision
        if not allowed:
            print(f"[UnifAI Proxy] BLOCKED duplicate prompt to {domain} → Rule: {rule_triggered}")
            make_blocked_response(flow, rule_triggered, host, reply_text=reply_text)
        elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != prompt:
            try:
                new_content = inject_warned_prompt(raw_text, prompt, redacted_prompt)
                if new_content:
                    flow.request.content = new_content.encode("utf-8")
            except Exception:
                pass
    def _file_send_maybe_block(
        self,
        flow: http.HTTPFlow,
        domain: str,
        platform: str,
        client_ip: str,
        raw_text: str,
        content_type: str,
        path: str,
    ) -> tuple[bool, int, bool]:
        """Scan attached/cached files on Send. Returns (blocked, files_processed, caption_consumed)."""
        should_block_file, file_block_msg, redact_notice, n_processed, caption_consumed = enforce_file_send_policy(
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
            return True, n_processed, caption_consumed
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
        return False, n_processed, caption_consumed

    def _detect_search_browser(self, flow: http.HTTPFlow) -> str:
        """Identify the employee browser from UA / Client Hints — any Chromium or Gecko browser."""
        user_agent = flow.request.headers.get("user-agent", "") or ""
        sec_ch_ua = (flow.request.headers.get("sec-ch-ua", "") or "").lower()
        ua = user_agent.lower()

        # Order matters: Edge/Opera/Brave/Vivaldi embed "chrome/" in UA.
        if (
            "edg/" in ua
            or "edga/" in ua
            or "edgios/" in ua
            or "microsoft edge" in sec_ch_ua
            or '"microsoft edge"' in sec_ch_ua
        ):
            return "Edge"
        if "opr/" in ua or "opera" in sec_ch_ua:
            return "Opera"
        if "brave" in sec_ch_ua or "brave/" in ua:
            return "Brave"
        if "vivaldi" in ua or "vivaldi" in sec_ch_ua:
            return "Vivaldi"
        if "firefox/" in ua or "fxios/" in ua:
            return "Firefox"
        if ("safari/" in ua or "version/" in ua) and "chrome" not in ua and "chromium" not in ua:
            return "Safari"
        if "chrome/" in ua or "crios/" in ua or "google chrome" in sec_ch_ua or "chromium" in sec_ch_ua:
            return "Chrome"
        return "Unknown"

    @staticmethod
    def _decode_bing_click_u(u_val: str) -> str:
        """Decode Bing/Edge result redirect `u=a1…` (base64url) to the destination URL."""
        import base64
        import urllib.parse

        raw = (u_val or "").strip()
        if not raw:
            return ""
        # Plain URL sometimes appears without a1 prefix
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        # a1 / a1aHR0… — strip leading letter+digit marker then pad base64
        payload = raw
        if len(raw) > 2 and raw[0].isalpha() and raw[1].isdigit():
            payload = raw[2:]
        pad = "=" * ((4 - (len(payload) % 4)) % 4)
        for candidate in (payload + pad, payload):
            try:
                decoded = base64.urlsafe_b64decode(candidate.encode("ascii", errors="ignore")).decode(
                    "utf-8", errors="ignore"
                )
                decoded = (decoded or "").strip()
                if decoded.startswith("http://") or decoded.startswith("https://"):
                    return decoded
                # Sometimes nested once
                if decoded and not decoded.startswith("http"):
                    again = urllib.parse.unquote(decoded)
                    if again.startswith("http"):
                        return again
            except Exception:
                continue
        return ""

    def _maybe_record_search_engine(self, flow: http.HTTPFlow, host: str) -> None:
        """Capture search queries + result clicks for ANY browser (Chrome/Edge/Firefox/…).

        Engines: Google, Bing (incl. Edge/MSN), DuckDuckGo, Yahoo.
        Saves via POST /api/browser-ai/search-logs → Postgres.
        """
        try:
            import urllib.parse

            h_lower = (host or "").lower().strip(".")
            engine = ""
            # Edge new-tab / MSN often fronts Bing — treat as Bing for Search Logs.
            if "google." in h_lower:
                engine = "Google"
            elif (
                "bing.com" in h_lower
                or h_lower.endswith("msn.com")
                or h_lower == "msn.com"
                or "edgeservices.bing" in h_lower
                or h_lower.endswith(".msn.com")
            ):
                engine = "Bing"
            elif "duckduckgo.com" in h_lower:
                engine = "DuckDuckGo"
            elif "search.brave.com" in h_lower or h_lower == "search.brave.com":
                engine = "Brave Search"
            elif "search.yahoo.com" in h_lower or h_lower.endswith("yahoo.com") or h_lower == "yahoo.com":
                engine = "Yahoo"
            else:
                return

            browser = self._detect_search_browser(flow)

            cookie = flow.request.headers.get("cookie", "") or ""
            is_incognito = False
            if flow.request.headers.get("x-edge-inprivate", ""):
                is_incognito = True
            elif not cookie or len(cookie.strip()) < 15:
                is_incognito = True
            elif engine == "Google" and ("SAPISID=" not in cookie and "SID=" not in cookie):
                is_incognito = True
            elif engine == "Bing" and ("MUID=" not in cookie and "_EDGE_S=" not in cookie and "USRLOC=" not in cookie):
                is_incognito = True

            path = flow.request.path or ""
            path_l = path.lower().split("?", 1)[0]
            query_str = flow.request.query or {}
            searched_query = ""
            clicked_url = ""
            clicked_title = ""

            def _q(*keys: str) -> str:
                for k in keys:
                    v = query_str.get(k, "")
                    if isinstance(v, (list, tuple)):
                        v = v[0] if v else ""
                    v = (v or "").strip()
                    if v:
                        return urllib.parse.unquote_plus(v)
                return ""

            if engine == "Google":
                # Skip autocomplete / suggest noise — keep committed /search and link redirects.
                if "/complete/" in path_l or path_l.endswith("/complete/search"):
                    return
                if not any(x in path_l for x in ("/gen_204", "/client_204", "/async/", "/csi", "/verify/")):
                    raw_q = _q("q", "as_q", "query")
                    if raw_q and not raw_q.startswith("http"):
                        searched_query = raw_q
                # Result link click: /url?url=… or /url?q=https://…
                if path_l.startswith("/url") or "/url?" in (flow.request.path or "").lower() or path_l == "/url":
                    target = _q("url", "q", "qurl")
                    if target.startswith("http"):
                        clicked_url = target
                        searched_query = ""  # click row — don't also store redirect junk as query
                # Image result click
                if not clicked_url and ("/imgres" in path_l or path_l.startswith("/imgres")):
                    target = _q("imgurl", "imgrefurl", "q")
                    if target.startswith("http"):
                        clicked_url = target

            elif engine == "Bing":
                # Skip suggest / telemetry
                if any(path_l.startswith(p) for p in ("/as/", "/suggestions/", "/fd/ls", "/notifications/", "/api/")):
                    if not (path_l.startswith("/ck/") or "alink.aspx" in path_l or path_l.startswith("/aclick")):
                        return
                raw_q = _q("q", "pq", "query")
                if raw_q and not raw_q.startswith("http"):
                    searched_query = raw_q
                # Edge/Bing result click redirects
                if (
                    path_l.startswith("/ck/")
                    or "alink.aspx" in path_l
                    or path_l.startswith("/aclick")
                    or path_l.startswith("/news/apiclick")
                    or "r.msn.com" in h_lower
                    or path_l.startswith("/cl/")
                ):
                    u_val = query_str.get("u", "") or query_str.get("url", "") or query_str.get("r", "")
                    if isinstance(u_val, (list, tuple)):
                        u_val = u_val[0] if u_val else ""
                    decoded = self._decode_bing_click_u(str(u_val or ""))
                    if not decoded:
                        decoded = _q("url", "r", "u")
                        if not (decoded.startswith("http")):
                            decoded = ""
                    if decoded.startswith("http"):
                        clicked_url = decoded
                        # Prefer click row without duplicating the search q from referrer noise
                        if path_l.startswith("/ck/") or "alink" in path_l:
                            searched_query = searched_query if searched_query and len(searched_query) < 200 else ""

            elif engine == "DuckDuckGo":
                if path_l.startswith("/ac/"):
                    return
                raw_q = _q("q", "query")
                if raw_q and not raw_q.startswith("http"):
                    searched_query = raw_q
                if path_l.startswith("/l/") or path_l.startswith("/y.js"):
                    uddg = _q("uddg", "u")
                    if uddg.startswith("http"):
                        clicked_url = uddg
                        searched_query = ""

            elif engine == "Brave Search":
                raw_q = _q("q", "query")
                if raw_q and not raw_q.startswith("http"):
                    searched_query = raw_q
                # Brave often links out directly; capture redirect helpers when present
                target = _q("url", "u")
                if target.startswith("http") and ("/redirect" in path_l or path_l.startswith("/out")):
                    clicked_url = target
                    searched_query = ""

            elif engine == "Yahoo":
                raw_q = _q("p", "q", "query")
                if raw_q and not raw_q.startswith("http"):
                    searched_query = raw_q
                # Yahoo click redirects
                if "/RU=" in (flow.request.url or "") or path_l.startswith("/click") or "rds.yahoo" in h_lower:
                    ru = ""
                    full = flow.request.url or ""
                    if "/RU=" in full:
                        try:
                            part = full.split("/RU=", 1)[1]
                            part = part.split("/RK=", 1)[0].split("/RS=", 1)[0]
                            ru = urllib.parse.unquote(part)
                        except Exception:
                            ru = ""
                    if not ru:
                        ru = _q("RU", "url")
                    if ru.startswith("http"):
                        clicked_url = ru
                        searched_query = searched_query if searched_query else ""

            searched_query = (searched_query or "").strip()
            clicked_url = (clicked_url or "").strip()
            if not searched_query and not clicked_url:
                return

            # Drop obvious non-user noise queries
            if searched_query and len(searched_query) > 500:
                searched_query = searched_query[:500]
            if clicked_url and len(clicked_url) > 2000:
                clicked_url = clicked_url[:2000]

            if clicked_url:
                try:
                    p = urllib.parse.urlparse(clicked_url)
                    clicked_title = p.netloc or clicked_url[:40]
                except Exception:
                    clicked_title = clicked_url[:40]

            client_ip = get_client_ip(flow)
            # Include browser + IP so Edge is not dropped when Chrome searched the same term.
            event_key = f"{engine}:{browser}:{client_ip}:{searched_query}:{clicked_url}"
            if is_duplicate_event("search-engine", event_key, ttl=4):
                return
            mark_duplicate_event("search-engine", event_key)

            wire_fields = _agent_wire_fields() if "_agent_wire_fields" in globals() else {}
            payload_dict = {
                "engine": engine,
                "browser": browser,
                "is_incognito": is_incognito,
                "query": searched_query,
                "clicked_url": clicked_url,
                "clicked_title": clicked_title,
                "url": flow.request.url,
                "host": host,
                "client_ip": client_ip,
                **wire_fields,
            }

            import json
            import ssl
            import threading
            import urllib.request

            def _post():
                try:
                    ssl_ctx = ssl.create_default_context()
                    ssl_ctx.check_hostname = False
                    ssl_ctx.verify_mode = ssl.CERT_NONE
                    req_data = json.dumps(payload_dict).encode("utf-8")
                    r = urllib.request.Request(
                        f"{UNIFAI_BACKEND_URL}/api/browser-ai/search-logs",
                        data=req_data,
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with urllib.request.urlopen(r, context=ssl_ctx, timeout=8) as resp:
                        if getattr(resp, "status", 200) >= 400:
                            print(
                                f"[UnifAI Proxy Warning] search-log HTTP {resp.status} → {UNIFAI_BACKEND_URL}"
                            )
                except Exception as e:
                    print(f"[UnifAI Proxy Warning] Failed to send search log to {UNIFAI_BACKEND_URL}: {e}")

            threading.Thread(target=_post, daemon=True).start()
            print(
                f"[UnifAI Proxy] SEARCH LOGGED | {engine} ({browser}"
                f"{' - INCOGNITO' if is_incognito else ''}) | "
                f"Query={searched_query!r} Click={clicked_url!r}"
            )

        except Exception as e:
            print(f"[UnifAI Proxy Warning] Search engine parse error: {e}")

    # ── HTTP Request Interception ──────────────

    def request(self, flow: http.HTTPFlow) -> None:
        host = flow.request.pretty_host
        method = (flow.request.method or "").upper()

        # Search engine query & result link interception (Google, Edge/Bing, Safari, DuckDuckGo, Yahoo)
        self._maybe_record_search_engine(flow, host)

        # CDN / noise hosts (cdn.*, static.*) often carry file uploads. Cache via Referer
        # BEFORE noise early-return — otherwise extract→rules never see the bytes.
        if method in ("POST", "PUT", "PATCH") and is_noise_host(host):
            path_n = flow.request.path
            raw_bytes_n = flow.request.content or b""
            content_type_n = flow.request.headers.get("content-type", "")
            try:
                raw_text_n = raw_bytes_n.decode("utf-8", errors="ignore")
            except Exception:
                raw_text_n = ""
            is_upload_n, upload_reason_n = detect_file_upload(flow, raw_text_n)
            if is_upload_n:
                fname_n = extract_filename_from_upload(flow, raw_text_n)
                if is_confident_file_upload(
                    fname=fname_n,
                    content_type=content_type_n,
                    raw_bytes=raw_bytes_n,
                    raw_text=raw_text_n,
                    upload_reason=upload_reason_n or "",
                    host=host,
                    path=path_n,
                ):
                    bind = _resolve_upload_bind_domain(flow, host)
                    if bind:
                        file_ids = _extract_file_ids_from_chat(raw_text_n)
                        cache_upload_file(
                            bind,
                            file_name=fname_n or "attachment",
                            raw_bytes=raw_bytes_n,
                            content_type=content_type_n,
                            upload_reason=upload_reason_n or "",
                            file_id=file_ids[0] if file_ids else "",
                        )
                        print(
                            f"[UnifAI Proxy] FILE CACHED via noise CDN bind | upload_host={host} → "
                            f"target={bind} | {fname_n or 'attachment'} | {len(raw_bytes_n)} bytes"
                        )
            return

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
                        **_agent_wire_fields(),
                        "metadata": {
                            "domain": b_domain,
                            "url": flow.request.url,
                            "method": flow.request.method,
                            "is_blocked": True,
                            "blocked_reason": "Block Entire Website",
                            **_agent_metadata_fields(),
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
        path = flow.request.path
        client_ip = get_client_ip(flow)
        method = (flow.request.method or "").upper()

        # Do NOT brand-skip google.*/bing.*/yahoo.* here.
        # Search Logs already recorded above; non-targets fall through to CDN bind then return.
        # Admin Target Websites on those hosts (clients6.google.com, notebooklm.google.com,
        # aistudio.google.com, bing Copilot, …) must still cache uploads + run Guard Rules.

        if not is_target:
            # File CDNs are often NOT the chat Target Website. Bind via Referer/Origin
            # to the admin-added domain so extract→rules still run on Send (any AI site).
            if method in ("POST", "PUT", "PATCH"):
                raw_bytes_nt = flow.request.content or b""
                content_type_nt = flow.request.headers.get("content-type", "")
                try:
                    raw_text_nt = raw_bytes_nt.decode("utf-8", errors="ignore")
                except Exception:
                    raw_text_nt = ""
                is_upload_nt, upload_reason_nt = detect_file_upload(flow, raw_text_nt)
                if is_upload_nt:
                    fname_nt = extract_filename_from_upload(flow, raw_text_nt)
                    if is_confident_file_upload(
                        fname=fname_nt,
                        content_type=content_type_nt,
                        raw_bytes=raw_bytes_nt,
                        raw_text=raw_text_nt,
                        upload_reason=upload_reason_nt or "",
                        host=host,
                        path=path,
                    ):
                        bind = _resolve_upload_bind_domain(flow, host)
                        if bind:
                            file_ids = _extract_file_ids_from_chat(raw_text_nt)
                            cache_upload_file(
                                bind,
                                file_name=fname_nt or "attachment",
                                raw_bytes=raw_bytes_nt,
                                content_type=content_type_nt,
                                upload_reason=upload_reason_nt or "",
                                file_id=file_ids[0] if file_ids else "",
                            )
                            print(
                                f"[UnifAI Proxy] FILE CACHED via Referer bind | upload_host={host} → "
                                f"target={bind} | {fname_nt or 'attachment'} | {len(raw_bytes_nt)} bytes"
                            )
            return

        # Keep control settings warm
        get_control_settings()

        # ── Universal GET: query-string prompts on any monitored domain ──
        if method == "GET":
            qs_prompt = extract_prompt_from_query_string(flow.request.url)
            if (
                qs_prompt
                and looks_like_user_prompt(qs_prompt)
                and _is_confident_chat_send(path, "", b"")
            ):
                if is_duplicate_event(domain, qs_prompt, ttl=DEDUPE_TTL, mark=False):
                    self._apply_duplicate_http_prompt(flow, domain, platform, qs_prompt, client_ip, "")
                else:
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
            # Upload pick: cache bytes — pure picks wait for Send; combined file+prompt
            # on the same request must fall through so extract + Guard Rules still run.
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
                combined_send = bool(
                    has_prompt
                    or attachment_send
                    or _is_confident_chat_send(path, raw_text, raw_bytes)
                    or _send_carries_attachment(raw_text)
                )
                if not combined_send:
                    return
                print(
                    f"[UnifAI Proxy] Upload also looks like chat Send — continue extract/rules | {domain}"
                )
            # Weak upload signal: do NOT abort — fall through so typed prompt / file Send
            # on the same request still reaches Prompt Logs + Guard Rules.
            else:
                print(
                    f"[UnifAI Proxy] Ignoring weak upload signal (continue evaluate) | {host} | "
                    f"reason={upload_reason!r} name={fname!r} bytes={len(raw_bytes)}"
                )

        # ── File Send: scan cached bytes; then still apply caption Guard Rules ──
        # Any admin Target Website — attachment markers OR pending upload cache.
        if _file_policy_applies_on_send(path, raw_text, raw_bytes, domain=domain, host=host):
            blocked, n_processed, caption_consumed = self._file_send_maybe_block(
                flow, domain, platform, client_ip, raw_text, content_type, path,
            )
            if blocked:
                return
            if n_processed > 0:
                # Caption already evaluated with all files — avoid duplicate predict row.
                if (
                    not caption_consumed
                    and has_prompt
                    and peek_prompt
                    and len((peek_prompt or "").strip()) <= 320
                    and not _looks_like_document_body_dump(peek_prompt)
                ):
                    self._apply_http_prompt(flow, domain, platform, peek_prompt, client_ip, raw_text)
                return
            # Cache miss with attachment markers: fall through so prompt + rules still run.
            print(
                f"[UnifAI Proxy] File Send markers without cache | {domain} | "
                "falling through to prompt evaluate (upload may have used another host)"
            )

        # ── Domain-add-only intercept: extracted user text → predict ──
        # Only finished chat Sends (and short captions after file scan). Never every site request.
        if has_prompt:
            # Active typing / keystroke drafts (e.g. Grok, Copilot): wait for composer to settle so "h" then "hi" becomes full prompt
            if len(peek_prompt.strip()) <= 15 or is_composer_typing_draft(domain, peek_prompt):
                stable = wait_if_composer_unstable(domain, peek_prompt)
                if stable is None:
                    return
                peek_prompt = stable

            self._apply_http_prompt(flow, domain, platform, peek_prompt, client_ip, raw_text)
            return

        # Gemini batchexecute noise — only skip when body is not a chat submit.
        if "batchexecute" in (path or "").lower() and not is_batchexecute_chat_submit(path, raw_text):
            return

        if is_event_sync_noise_content(raw_text):
            return

        # Only inspect real chat/prompt endpoints — ignore challenges & analytics
        if not is_chat_path(path, host, raw_text):
            return

        if not _is_confident_chat_send(path, raw_text, raw_bytes) and not attachment_send:
            # Telemetry / background RPCs on chat-ish paths — no predict
            return

        messages_parts_shaped = _looks_like_messages_parts_body(raw_text, raw_bytes)
        if not messages_parts_shaped:
            if is_noise(path):
                return
            if is_noise(path, raw_text):
                return
        elif "prepare" in (path or "").lower() or "autocomplet" in (path or "").lower():
            return

        # File attached + Send (fallback path when extract missed on first pass)
        if _file_policy_applies_on_send(path, raw_text, raw_bytes, domain=domain, host=host):
            blocked, n_processed, caption_consumed = self._file_send_maybe_block(
                flow, domain, platform, client_ip, raw_text, content_type, path,
            )
            if blocked:
                return
            if n_processed > 0 and caption_consumed:
                # Combined multi-file+caption already predicted — skip duplicate text path.
                return
            # If no cache processed, continue so prompt evaluate can still block.

        prompt = extract_prompt_universal(raw_bytes, content_type, host=host, url=flow.request.url)
        if not prompt or len(prompt.strip()) < 1:
            if len(raw_bytes) > 8:
                print(f"[UnifAI Proxy] No prompt extracted | {platform} ({domain}) path={path[:80]!r} bytes={len(raw_bytes)}")
            # Attachment-only send already logged above (real file markers only)
            if chat_carries_attachment(raw_text):
                return
            return
        # Same gate as early path — confident Send keeps number/symbol/short text.
        if not _should_intercept_extracted_prompt(
            prompt, path, raw_text, domain, host=host, raw_bytes=raw_bytes
        ):
            return
        # Skip duplicate FILE UPLOAD lines if extract_prompt somehow returned that
        if prompt.strip().startswith("[FILE UPLOAD"):
            return

        # ChatGPT/Perplexity: skip only in-progress draft bodies, not finished submits.
        if is_unsubmitted_chat_body(path, raw_text):
            return
        # Finished chat-shaped Sends: commit immediately (all Target domains).
        # Composer hold is ONLY for keystroke-as-HTTP sites (Grok/Copilot) — long waits
        # caused intermittent predict misses (hi / numbers / symbols / every AI).
        confident_send = _is_confident_chat_send(path, raw_text, raw_bytes)

        # Body-shape shortcut: if JSON body carries messages[]/prompt/query etc.
        # → treat as confident regardless of path recognition (fixes ChatGPT/Perplexity).
        if not confident_send and raw_text.lstrip().startswith(("{", "[")):
            try:
                _body_data = json.loads(raw_text)
                if _body_has_user_send_payload(_body_data):
                    confident_send = True
            except Exception:
                pass

        if not confident_send:
            if len(prompt.strip()) <= 15 or is_composer_typing_draft(domain, prompt):
                stable = wait_if_composer_unstable(domain, prompt)
                if stable is None:
                    # Supersede fallback: never silently drop — commit whatever is latest.
                    with _composer_lock:
                        _fallback = _composer_draft.get(domain)
                    prompt = (_fallback[0] or prompt).strip() if _fallback else prompt
                    if not prompt:
                        return
                else:
                    prompt = stable


        # Collapse browser double-fire — MUST still enforce the same guard decision
        # (silent return here previously let the 2nd request bypass BLOCK).
        if is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL, mark=False):
            self._apply_duplicate_http_prompt(flow, domain, platform, prompt, client_ip, raw_text)
            return

        print(f"[UnifAI Proxy] Intercepted prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")
        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt_coalesced(
            platform=platform,
            domain=domain,
            prompt=prompt,
            client_ip=client_ip,
            url=flow.request.url,
            method=flow.request.method,
        )
        mark_duplicate_event(domain, prompt)
        clear_composer_state(domain)

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

        if attachment_send and _file_policy_applies_on_send(
            ws_path, content, content.encode("utf-8", errors="ignore"), domain=domain, host=host,
        ):
            should_block_file, file_block_msg, _redact_notice, _n, _caption_consumed = enforce_file_send_policy(
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
                        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt_coalesced(
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
                    else:
                        decision = get_remembered_guard_decision(domain, pn) or evaluate_prompt_coalesced(
                            platform=platform,
                            domain=domain,
                            prompt=ws_prompt,
                            client_ip=client_ip,
                            url=flow.request.url,
                            method="WS",
                        )
                        allowed, rule_triggered, action, redacted_prompt, reply_text = decision
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
            if len(ws_prompt.strip()) <= 15 or is_composer_typing_draft(domain, ws_prompt):
                stable = wait_if_composer_unstable(domain, ws_prompt)
                if stable is None:
                    return
                ws_prompt = stable

            mark_duplicate_event(domain, ws_prompt)
            allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt_coalesced(
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

        if "batchexecute" in ws_path.lower() and not is_batchexecute_chat_submit(ws_path, content):
            return
        if is_event_sync_noise_content(content):
            return
        if not is_chat_path(ws_path, host, content):
            return

        messages_parts_shaped = _looks_like_messages_parts_body(content)
        if not messages_parts_shaped and is_noise(ws_path, content):
            return

        # File attachment Send must hit Block Upload / file rules (finished Send only)
        if _file_policy_applies_on_send(
            ws_path, content, content.encode("utf-8", errors="ignore"), domain=domain, host=host,
        ):
            should_block_file, file_block_msg, _redact_notice, n_processed, caption_consumed = enforce_file_send_policy(
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
            if n_processed > 0 and caption_consumed:
                return
            # Cache miss: fall through to prompt evaluate. Cache hit without caption: allow below.

        # Copilot/Edge image or file frames must not fall through as garbled text prompts.
        if (
            (event_send_carries_binary_attach(content) or chat_carries_attachment(content) or messages_parts_carries_file(content))
            and not (ws_has_prompt and ws_prompt and len((ws_prompt or "").strip()) <= 320)
        ):
            return

        prompt = extract_prompt_universal(content.encode("utf-8"), "application/json", host=host, url=flow.request.url)
        if not prompt or prompt.strip() in ("{}", "[]", "ping", "pong"):
            return
        ws_bytes = content.encode("utf-8", errors="ignore")
        if not _should_intercept_extracted_prompt(
            prompt, flow.request.path, content, domain, host=host, raw_bytes=ws_bytes
        ):
            return

        if is_unsubmitted_chat_body(flow.request.path, content):
            return
        # Confident chat shapes: predict immediately (same as HTTP path).
        confident_ws = _is_confident_chat_send(flow.request.path, content, ws_bytes)
        if not confident_ws:
            if is_composer_typing_draft(domain, prompt):
                return
            stable = wait_if_composer_unstable(domain, prompt)
            if stable is None:
                return
            prompt = stable

        if is_duplicate_event(domain, prompt, ttl=DEDUPE_TTL, mark=False):
            decision = get_remembered_guard_decision(domain, prompt)
            if decision is None:
                decision = evaluate_prompt_coalesced(
                    platform=platform,
                    domain=domain,
                    prompt=prompt,
                    client_ip=get_client_ip(flow),
                    url=flow.request.url,
                    method="WS",
                )
            allowed, rule_triggered, action, redacted_prompt, reply_text = decision
            if not allowed:
                try:
                    msg.drop()
                except Exception:
                    try:
                        msg.kill()
                    except Exception:
                        pass
                inject_websocket_reply(flow, host, (reply_text or "").strip())
            elif action in ("Warned", "Redacted") and redacted_prompt and redacted_prompt != prompt:
                new_content = inject_warned_prompt(content, prompt, redacted_prompt)
                if new_content:
                    msg.text = new_content
            return

        client_ip = get_client_ip(flow)
        print(f"[UnifAI Proxy] WebSocket prompt | {client_ip} → {platform} ({domain}) | {prompt[:80]!r}")
        allowed, rule_triggered, action, redacted_prompt, reply_text = evaluate_prompt_coalesced(
            platform=platform,
            domain=domain,
            prompt=prompt,
            client_ip=client_ip,
            url=flow.request.url,
            method="WS",
        )
        mark_duplicate_event(domain, prompt)
        clear_composer_state(domain)

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
