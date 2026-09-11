# Part of UnifAI browser_ai_proxy — loaded via browser_ai_proxy.py into one shared namespace.
# Do not import this file directly.



_FAKE_UPLOAD_NAMES = frozenset({
    "", "attachment", "attachment.txt", "attachment.bin", "blob", "blob.txt",
    "file", "file.txt", "upload", "untitled", "document", "document.txt",
    "image", "image.png", "audio", "video", "media", "unknown", "null", "undefined",
    "document.pdf", "archive.zip", "attachment-1", "attachment-2", "attachment-3",
})

_UPLOAD_NAME_EXTS = (
    ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".xlsm", ".pptx", ".ppt",
    ".odt", ".ods", ".odp", ".rtf", ".html", ".htm", ".xml",
    ".txt", ".csv", ".json", ".md", ".log",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac", ".aac", ".opus", ".wma",
    ".py", ".js", ".ts", ".java", ".go",
)


def _is_fake_upload_name(name: str) -> bool:
    n = (name or "").strip().lower()
    if not n or n in _FAKE_UPLOAD_NAMES:
        return True
    if re.fullmatch(r"attachment(-\d+)?", n):
        return True
    return False


def _sanitize_upload_filename(name: str) -> str:
    name = urllib.parse.unquote((name or "").strip().strip("\"'"))
    name = name.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or _is_fake_upload_name(name):
        return ""
    # Reject path traversal / absurd lengths
    if ".." in name or len(name) > 180:
        return ""
    return name


def _filename_from_multipart_or_headers(raw: bytes = b"", headers=None, raw_text: str = "") -> str:
    """Pull a real user filename from multipart bytes, headers, or JSON text."""
    if headers is not None:
        try:
            cd = headers.get("content-disposition", "") or ""
        except Exception:
            cd = ""
        if "filename" in cd.lower():
            m = re.search(r"filename\*=(?:UTF-8''|utf-8'')([^;\r\n]+)|filename\*?=(?:UTF-8''|utf-8'')?\"?([^\";\r\n]+)\"?", cd, re.I)
            if m:
                got = _sanitize_upload_filename(m.group(1) or m.group(2) or "")
                if got:
                    return got
        for hk in (
            "x-file-name", "x-goog-upload-file-name", "x-filename", "x-upload-filename",
            "x-ms-file-name", "openai-file-name", "file-name", "x-amz-meta-filename",
        ):
            try:
                val = headers.get(hk)
            except Exception:
                val = None
            if val:
                got = _sanitize_upload_filename(str(val))
                if got:
                    return got

    blob = raw or b""
    if blob:
        sample = blob[: min(len(blob), 96 * 1024)]
        for pat in (
            rb'filename\*=(?:UTF-8\'\'|utf-8\'\')([^;\r\n]+)',
            rb'filename="([^"]+)"',
            rb"filename='([^']+)'",
            rb'filename=([^;\r\n\s]+)',
        ):
            m = re.search(pat, sample, re.I)
            if m:
                try:
                    raw_name = m.group(1).decode("utf-8", errors="ignore")
                except Exception:
                    raw_name = m.group(1).decode("latin-1", errors="ignore")
                got = _sanitize_upload_filename(raw_name)
                if got:
                    return got

    text = raw_text or ""
    if text:
        for pat in (
            r'["\'](?:file_name|fileName|filename|original_name|originalName|original_filename)["\']\s*:\s*["\']([^"\']+)["\']',
            r'filename\s*=\s*["\']([^"\';\r\n]+)["\']',
        ):
            m = re.search(pat, text[:20000], re.I)
            if m:
                got = _sanitize_upload_filename(m.group(1))
                if got:
                    return got
    return ""


def _default_name_from_bytes(raw: bytes, content_type: str = "", idx: int = 0) -> str:
    """Fallback label when the product wire omits the real filename."""
    kind = ""
    try:
        kind = _classify_upload_kind(raw or b"", content_type, "")
    except Exception:
        kind = ""
    suffix = f"-{idx + 1}" if idx > 0 else ""
    return {
        "pdf": f"document{suffix}.pdf",
        "zip": f"archive{suffix}.zip",
        "image": f"image{suffix}.png",
        "audio": f"audio{suffix}.bin",
        "video": f"video{suffix}.bin",
        "docx": f"document{suffix}.docx",
        "xlsx": f"spreadsheet{suffix}.xlsx",
        "pptx": f"presentation{suffix}.pptx",
        "plain": f"file{suffix}.txt",
    }.get(kind, f"attachment{suffix}")


def _list_zip_member_basenames(data: bytes, max_names: int = 24) -> list[str]:
    if not data:
        return []
    zdata = data if data[:2] == b"PK" else (_office_zip_bytes(data) or b"")
    if not zdata or zdata[:2] != b"PK":
        return []
    out: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(zdata)) as zf:
            for info in zf.infolist():
                if len(out) >= max_names:
                    break
                if info.is_dir():
                    continue
                name = (info.filename or "").replace("\\", "/")
                base = name.rsplit("/", 1)[-1]
                low = name.lower()
                if not base or base.startswith("."):
                    continue
                if "__macosx" in low or low.endswith(".ds_store"):
                    continue
                out.append(base)
    except Exception:
        return []
    return out


def extract_all_attachment_filenames_from_send(raw_text: str) -> list[str]:
    """All real filenames referenced on a chat Send (multi-file)."""
    if not raw_text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    patterns = (
        r'["\'](?:file_name|fileName|filename|original_name|originalName|original_filename)["\']\s*:\s*["\']([^"\']+)["\']',
        r'"attachments"\s*:\s*\[[\s\S]{0,20000}?\]',
        r'"name"\s*:\s*"([^"]+\.[A-Za-z0-9]{2,8})"',
        r'"title"\s*:\s*"([^"]+\.[A-Za-z0-9]{2,8})"',
    )
    for pat in patterns:
        if pat.startswith('"attachments"'):
            continue
        for m in re.finditer(pat, raw_text, re.I):
            got = _sanitize_upload_filename(m.group(1))
            if not got:
                continue
            key = got.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(got)
    # Attachment objects: pull name fields inside attachments/files arrays
    for arr_pat in (
        r'"attachments"\s*:\s*\[([\s\S]{0,40000}?)\]',
        r'"files"\s*:\s*\[([\s\S]{0,40000}?)\]',
        r'"parts"\s*:\s*\[([\s\S]{0,40000}?)\]',
    ):
        for am in re.finditer(arr_pat, raw_text, re.I):
            block = am.group(1) or ""
            for m in re.finditer(
                r'["\'](?:file_name|fileName|filename|name|title)["\']\s*:\s*["\']([^"\']+)["\']',
                block,
                re.I,
            ):
                got = _sanitize_upload_filename(m.group(1))
                if not got:
                    continue
                key = got.lower()
                if key in seen:
                    continue
                seen.add(key)
                found.append(got)
    return found


def extract_file_id_name_map(raw_text: str) -> dict[str, str]:
    """Map ChatGPT/Claude file_id → real filename when both appear near each other."""
    out: dict[str, str] = {}
    if not raw_text:
        return out
    # file_id then name (within a small window)
    for m in re.finditer(
        r'(?:file_id|fileId|id)\s*"?\s*:\s*"((?:file-)?[A-Za-z0-9_-]{6,})"[^\n]{0,400}?'
        r'(?:file_name|fileName|filename|name|title)\s*"?\s*:\s*"([^"]+)"',
        raw_text,
        re.I,
    ):
        fid = (m.group(1) or "").strip()
        name = _sanitize_upload_filename(m.group(2))
        if fid and name:
            out[fid] = name
            if fid.startswith("file-"):
                out[fid[5:]] = name
            else:
                out["file-" + fid] = name
    # name then file_id
    for m in re.finditer(
        r'(?:file_name|fileName|filename|name|title)\s*"?\s*:\s*"([^"]+)"[^\n]{0,400}?'
        r'(?:file_id|fileId|id)\s*"?\s*:\s*"((?:file-)?[A-Za-z0-9_-]{6,})"',
        raw_text,
        re.I,
    ):
        name = _sanitize_upload_filename(m.group(1))
        fid = (m.group(2) or "").strip()
        if fid and name:
            out[fid] = name
            if fid.startswith("file-"):
                out[fid[5:]] = name
            else:
                out["file-" + fid] = name
    return out


def _bind_real_filenames_to_cached_uploads(cached_list: list[dict], raw_text: str) -> list[dict]:
    """Attach real names from the Send body onto cached uploads (ChatGPT often omits name at upload)."""
    if not cached_list:
        return cached_list
    id_map = extract_file_id_name_map(raw_text or "")
    send_names = extract_all_attachment_filenames_from_send(raw_text or "")
    used_names: set[str] = set()

    for entry in cached_list:
        cur = (entry.get("file_name") or "").strip()
        fid = (entry.get("file_id") or "").strip()
        if fid and fid in id_map:
            entry["file_name"] = id_map[fid]
            used_names.add(id_map[fid].lower())
            continue
        if fid.startswith("file-") and fid[5:] in id_map:
            entry["file_name"] = id_map[fid[5:]]
            used_names.add(id_map[fid[5:]].lower())
            continue
        if not _is_fake_upload_name(cur) and cur.lower() != "document.pdf":
            used_names.add(cur.lower())

    unused = [n for n in send_names if n.lower() not in used_names]
    ui = 0
    for i, entry in enumerate(cached_list):
        cur = (entry.get("file_name") or "").strip()
        if not _is_fake_upload_name(cur) and cur.lower() != "document.pdf":
            continue
        if ui < len(unused):
            entry["file_name"] = unused[ui]
            used_names.add(unused[ui].lower())
            ui += 1
            continue
        raw = entry.get("raw_bytes") or b""
        if isinstance(raw, (bytes, bytearray)) and raw:
            entry["file_name"] = _default_name_from_bytes(
                bytes(raw), entry.get("content_type") or "", i,
            )
        elif _is_fake_upload_name(cur):
            entry["file_name"] = f"attachment-{i + 1}"
    return cached_list


def _display_label_for_upload(name: str, raw: bytes, content_type: str = "") -> str:
    """Human label for Prompt Logs — real name + ZIP member preview when useful."""
    label = (name or "").strip() or "attachment"
    kind = ""
    try:
        kind = _classify_upload_kind(raw or b"", content_type, label)
    except Exception:
        kind = ""
    if kind == "zip" or label.lower().endswith(".zip"):
        members = _list_zip_member_basenames(raw or b"")
        if members:
            preview = ", ".join(members[:4])
            more = f" +{len(members) - 4} more" if len(members) > 4 else ""
            return f"{label} [{len(members)} files: {preview}{more}]"
    return label


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
    raw_bytes = b""
    try:
        raw_bytes = flow.request.content or b""
    except Exception:
        raw_bytes = b""
    got = _filename_from_multipart_or_headers(raw_bytes, flow.request.headers, raw_text or "")
    if got:
        return got

    # Path parameter if it ends with a file extension
    path_clean = (flow.request.path or "").split("?", 1)[0]
    last_seg = path_clean.rsplit("/", 1)[-1]
    if "." in last_seg:
        name = _sanitize_upload_filename(urllib.parse.unquote(last_seg))
        if name and any(name.lower().endswith(ext) for ext in _UPLOAD_NAME_EXTS):
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
    name = _sanitize_upload_filename(file_name) or (file_name or "").strip() or "attachment"
    # Prefer multipart / header filename when caller only had a placeholder.
    mp_name = _filename_from_multipart_or_headers(raw, None, "")
    if mp_name and _is_fake_upload_name(name):
        name = mp_name
    elif mp_name and not _is_fake_upload_name(mp_name):
        name = mp_name

    pdf = extract_pdf_bytes(raw)
    if pdf:
        if not name.lower().endswith(".pdf"):
            if _is_fake_upload_name(name):
                name = "document.pdf"
            else:
                name = f"{name}.pdf"
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
            # Capture filename= value from this part header
            try:
                hdr_end = rest.find(b"\r\n\r\n")
                hdr = rest[: hdr_end if hdr_end >= 0 else 800].decode("utf-8", errors="ignore")
                hm = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)["\']?', hdr, re.I)
                if hm:
                    got = _sanitize_upload_filename(hm.group(1))
                    if got:
                        name = got
            except Exception:
                pass
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
                            if _is_fake_upload_name(name):
                                name = "document.pdf"
                            else:
                                name = f"{name}.pdf"
                        return pdf2, "application/pdf", name
                    ctype = _sniff_upload_content_type(part, name, content_type)
                    if len(part) > 20 * 1024 * 1024:
                        part = part[: 20 * 1024 * 1024]
                    if _is_fake_upload_name(name):
                        name = _default_name_from_bytes(part, ctype, 0)
                    return part, ctype, name

    # Direct binary body (resumable / octet-stream)
    if len(raw) >= 32:
        ctype = _sniff_upload_content_type(raw, name, content_type)
        # Skip tiny JSON metadata
        stripped = raw.lstrip()
        if stripped[:1] in (b"{", b"[") and len(raw) < 50_000 and ctype == "application/octet-stream":
            return None, "", name
        data = raw if len(raw) <= 20 * 1024 * 1024 else raw[: 20 * 1024 * 1024]
        if _is_fake_upload_name(name):
            name = _default_name_from_bytes(data, ctype, 0)
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

    # Filename with common document/image/audio extension in this send
    if re.search(
        r'"(?:file_name|filename|fileName|name|title)"\s*:\s*"[^"]+\.(?:pdf|docx?|xlsx?|pptx?|png|jpe?g|gif|webp|txt|csv|zip|mp3|wav|m4a|aac|ogg|webm|flac|mp4|mov)"',
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
    if messages_parts_carries_file(raw_text):
        return True
    if re.search(r'"id"\s*:\s*"file-[a-zA-Z0-9_-]+"', low):
        return True
    if re.search(r'"mime_type"\s*:\s*"(?:application/|image/|audio/|video/)', low):
        if '"attachments"' in low or '"files"' in low or '"content_type"' in low:
            return True

    # Copilot / Sydney image or file payloads (base64 in send frame)
    if event_send_carries_binary_attach(raw_text):
        return True

    return False


def event_send_carries_binary_attach(raw_text: str) -> bool:
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
    names = extract_all_attachment_filenames_from_send(raw_text or "")
    return names[0] if names else ""


def extract_inline_attachment_bytes(raw_text: str) -> tuple[bytes, str, str]:
    """Pull the first inline base64 file/image from a chat Send body."""
    all_inlines = extract_all_inline_attachment_bytes(raw_text)
    if not all_inlines:
        return b"", "", ""
    return all_inlines[0]


def extract_all_inline_attachment_bytes(raw_text: str) -> list[tuple[bytes, str, str]]:
    """Pull ALL inline base64 file/image payloads (Gemini multi-image Send)."""
    if not raw_text:
        return []
    import base64

    out: list[tuple[bytes, str, str]] = []
    seen: set[str] = set()
    fname_base = extract_attachment_filename_from_send(raw_text) or "attachment"

    # Prefer structured inline_data / fileData blocks, then generic large base64 fields.
    patterns = (
        r'"(?:inline_data|inlineData|fileData|file_data)"\s*:\s*\{[^}]{0,400}?"(?:mime_type|mimeType|media_type)"\s*:\s*"([^"]+)"[^}]{0,400}?"(?:data|bytes)"\s*:\s*"([A-Za-z0-9+/=\s\\]{80,})"',
        r'"(?:data|bytes|content|image|binary|base64)"\s*:\s*"([A-Za-z0-9+/=\s\\]{200,})"',
    )
    for pi, pat in enumerate(patterns):
        for mi, m in enumerate(re.finditer(pat, raw_text, re.I | re.DOTALL)):
            if pi == 0:
                mime = (m.group(1) or "").strip()
                blob = (m.group(2) or "")
            else:
                mime = ""
                blob = (m.group(1) or "")
                m_mime = re.search(
                    r'"(?:mime_type|mimeType|media_type|content_type)"\s*:\s*"([^"]+)"',
                    raw_text[max(0, m.start() - 180): m.start() + 40],
                    re.I,
                )
                if m_mime:
                    mime = (m_mime.group(1) or "").strip()
            blob = blob.replace("\\n", "").replace("\\r", "").replace(" ", "")
            if len(blob) < 80:
                continue
            # Dedup identical payloads (same image referenced twice).
            sig = blob[:64] + f"|{len(blob)}"
            if sig in seen:
                continue
            try:
                data = base64.b64decode(blob, validate=False)
            except Exception:
                continue
            if len(data) < 32:
                continue
            seen.add(sig)
            if not mime:
                if data[:5] == b"%PDF-":
                    mime = "application/pdf"
                elif data[:2] == b"PK":
                    mime = "application/vnd.openxmlformats-officedocument"
                elif data[:3] == b"\xff\xd8\xff":
                    mime = "image/jpeg"
                elif data[:8] == b"\x89PNG\r\n\x1a\n":
                    mime = "image/png"
                elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                    mime = "image/webp"
                else:
                    mime = "application/octet-stream"
            ext = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/webp": "webp",
                "image/gif": "gif",
                "application/pdf": "pdf",
            }.get(mime.lower().split(";")[0].strip(), "bin")
            fname = fname_base if len(out) == 0 and fname_base not in ("attachment", "file", "") else f"image_{len(out) + 1}.{ext}"
            if len(out) == 0 and "." not in fname_base and fname_base not in ("attachment", "file", ""):
                fname = f"{fname_base}.{ext}"
            elif len(out) == 0 and fname_base in ("attachment", "file", ""):
                fname = f"image_1.{ext}"
            out.append((data[:20 * 1024 * 1024], mime, fname))
            if len(out) >= _UPLOAD_FILE_QUEUE_MAX:
                return out
        if out and pi == 0:
            # Structured blocks found — don't also re-scan generic fields (duplicates).
            return out
    return out


def _domain_has_pending_upload_cache(domain: str) -> bool:
    """True when a recent upload is cached for this Target Website family (peek only)."""
    aliases = upload_domain_aliases(domain)
    if not aliases:
        d = _normalize_domain(domain or "")
        aliases = [d] if d else []
    now = time.time()
    with _UPLOAD_FILE_CACHE_LOCK:
        _purge_upload_file_cache()
        for alias in aliases:
            latest = _UPLOAD_FILE_CACHE.get(f"{alias}|latest")
            if latest and (now - float(latest.get("ts") or 0)) <= _UPLOAD_LATEST_MATCH_TTL:
                return True
            for entry in _UPLOAD_FILE_QUEUES.get(_upload_queue_key(alias), []) or []:
                if (now - float(entry.get("ts") or 0)) <= _UPLOAD_LATEST_MATCH_TTL:
                    return True
    return False


def _host_from_url_header(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    try:
        if "://" not in s:
            s = "https://" + s
        return _normalize_domain(urllib.parse.urlparse(s).hostname or "")
    except Exception:
        return ""


def _resolve_upload_bind_domain(flow: http.HTTPFlow, upload_host: str) -> str:
    """Map a file-CDN / non-chat host upload to an admin Target Website.

    No product hostname hardcoding — uses Referer/Origin (chat page) or parent
    Target Website that covers this host as a subdomain.
    """
    # Prefer the page the employee is chatting on.
    for hdr in ("Referer", "Origin", "referer", "origin"):
        ref_host = _host_from_url_header(flow.request.headers.get(hdr, "") or "")
        if not ref_host:
            continue
        ok, domain, _plat = detect_target(ref_host)
        if ok and domain:
            return domain

    # Upload host itself might be a monitored target or child of one.
    ok, domain, _plat = detect_target(upload_host)
    if ok and domain:
        return domain

    # Child of a monitored parent (admin added parent only).
    get_target_domains()
    h = _normalize_domain(upload_host or "")
    best = ""
    for d in _cached_domains:
        if h == d or h.endswith("." + d):
            if len(d) > len(best):
                best = d
    return best


def _file_policy_applies_on_send(
    path: str,
    raw_text: str,
    raw_bytes: bytes = b"",
    *,
    domain: str = "",
    host: str = "",
) -> bool:
    """File extract + Guard Rules on finished chat Send — ANY admin-monitored domain.

    Not ChatGPT-only: known platform shapes OR attachment markers OR pending upload
    cache for this Target Website family.
    """
    if _is_typing_or_draft_path(path, raw_text or ""):
        return False

    body = raw_text or ""
    has_file = (
        _send_carries_attachment(body)
        or messages_parts_carries_file(body)
        or chat_carries_attachment(body)
        or event_send_carries_binary_attach(body)
    )
    confident = _is_confident_chat_send(path, raw_text, raw_bytes)
    chatish = (
        confident
        or is_chat_path(path, host, body)
        or _path_has_chat_marker(path)
    )

    # Pure file-API picks (/files, /upload, …) wait for a later chat Send.
    # Exception: custom AIs that POST file+prompt on the same upload URL.
    if _path_looks_like_upload(path) and not (confident or (has_file and chatish)):
        return False

    # Attachment markers on a chat-shaped request → always scan.
    if has_file and chatish:
        return True

    # Pending upload cache: bind on finished Send even when the wire omits file ids
    # (common on some Target Websites). Do NOT run on every text Send with an empty cache.
    if domain and _domain_has_pending_upload_cache(domain):
        if chatish:
            return True
        stripped = body.lstrip()
        if stripped[:1] in ("{", "[") and not is_noise(path, body):
            return True
    return False


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
                raw = entry.get("raw_bytes") or b""
                # ChatGPT often caches as "attachment" — still bind real bytes on Send.
                if not isinstance(raw, (bytes, bytearray)) or len(raw) < 32:
                    if not name or _is_fake_upload_name(name):
                        continue
                if not is_confident_file_upload(
                    fname=name if not _is_fake_upload_name(name) else "file.bin",
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
    skip_backend: bool = False,
    extra_context: str = "",
) -> tuple[str, bool, str, str, str, list[str], bool, str]:
    """Scan file bytes on Send only — extract by type, then apply Guard Rules (+ AI bot if configured).
    Returns (..., scan_evaluated, scan_eval_error).
    skip_backend=True: extract + local regex only (multi-file combined eval).
    extra_context: caption/other text merged into local regex + backend evaluate."""
    scanned = ""
    rule_hit = False
    rule_name = ""
    rule_action = ""
    excerpt = ""
    upload_images: list[str] = []
    scan_evaluated = False
    scan_eval_error = ""
    try:
        if raw_bytes:
            try:
                scanned = extract_upload_text_for_rules(raw_bytes, content_type, raw_text or "", file_label) or ""
            except Exception as e:
                print(f"[UnifAI Proxy] extract_upload_text_for_rules failed (allowed): {e}")
                scanned = ""
        try:
            upload_images = _upload_images_for_vision(raw_bytes or b"", content_type, file_label) if raw_bytes else []
        except Exception as e:
            print(f"[UnifAI Proxy] upload vision images failed (allowed): {e}")
            upload_images = []
        eval_blob = "\n\n".join(
            x for x in ((extra_context or "").strip(), (scanned or "").strip()) if x
        ).strip()
        if eval_blob:
            excerpt = re.sub(r"\s+", " ", eval_blob).strip()[:180]
            try:
                rule_hit, rule_name, rule_action = match_guard_rules_on_text(eval_blob)
            except Exception as e:
                print(f"[UnifAI Proxy] local file regex failed (allowed): {e}")
                rule_hit, rule_name, rule_action = False, "", ""
            rule_action = (rule_action or "").upper()
            if rule_action == "WARN":
                rule_action = "REDACT"
        # Backend: regex + bot on extracted text / vision images (when any active rules exist).
        has_regex = bool(get_guard_rules())
        run_backend = bool(
            (not skip_backend)
            and platform
            and domain
            and (eval_blob or upload_images)
            and (has_ai_bot_rules() or has_regex)
        )
        if run_backend:
            try:
                allowed, rt, action, _, _, eval_err = send_to_backend(
                    platform, domain, (eval_blob or scanned or "")[:50_000], client_ip, url, method or "POST",
                    upload_images=upload_images,
                    evaluation_only=True,
                    extracted_text=(eval_blob or scanned or "")[:50_000],
                )
                if eval_err:
                    scan_eval_error = str(eval_err).strip()
                    scan_evaluated = False
                    print(f"[UnifAI Proxy] AI bot file scan eval_error (will re-check on log): {scan_eval_error}")
                else:
                    scan_evaluated = True
                    rule_hit, rule_name, rule_action = _merge_file_scan_backend(
                        rule_hit, rule_name, rule_action, allowed, rt, action or "",
                    )
            except Exception as e:
                scan_evaluated = False
                scan_eval_error = str(e).strip()[:300] or "backend file scan failed"
                print(f"[UnifAI Proxy] AI bot file scan failed (allowed): {e}")
    except Exception as e:
        print(f"[UnifAI Proxy] file rule scan failed (allowed): {e}")
        # Keep any partial extract/local regex already computed — do not wipe on late errors.
        if not scanned:
            rule_hit = False
            rule_name = ""
            rule_action = ""
            excerpt = ""
            upload_images = []
            scan_evaluated = False
            scan_eval_error = ""
    return scanned, rule_hit, rule_name, rule_action, excerpt, upload_images, scan_evaluated, scan_eval_error
