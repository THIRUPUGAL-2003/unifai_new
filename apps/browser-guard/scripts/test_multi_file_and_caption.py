import json
import urllib.request
import urllib.error
import http.cookiejar
import uuid

BASE_URL = "https://unifaiv2.dev-yp.com"
ADMIN_USER = "admin@yespanchi.com"
ADMIN_PASS = "YP2025-2026yp"

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

def http_req(method, path, json_data=None, data=None, headers=None):
    url = f"{BASE_URL}{path}"
    h = {"User-Agent": "UnifAI-QA/1.0", "Accept": "application/json"}
    if headers:
        h.update(headers)
    payload = None
    if json_data is not None:
        h["Content-Type"] = "application/json"
        payload = json.dumps(json_data).encode("utf-8")
    elif data is not None:
        payload = data

    req = urllib.request.Request(url, data=payload, headers=h, method=method)
    try:
        with opener.open(req, timeout=12) as r:
            body = r.read().decode("utf-8")
            try:
                return r.getcode(), json.loads(body)
            except Exception:
                return r.getcode(), body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body
    except Exception as e:
        return 0, str(e)

def send_multipart(path, fields, files):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body_parts = []
    for k, v in fields.items():
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body_parts.append(str(v).encode("utf-8") + b"\r\n")
    for field_name, (filename, file_bytes, content_type) in files.items():
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body_parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode("utf-8"))
        body_parts.append(file_bytes + b"\r\n")
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    payload = b"".join(body_parts)
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    return http_req("POST", path, data=payload, headers=headers)

print("=" * 75)
print("LIVE QA TEST: MULTI-FILE UPLOAD + USER TYPED TEXT (CAPTION) + BLOCK UPLOAD")
print(f"Target Server: {BASE_URL}")
print("=" * 75)

# Login
code, res = http_req("POST", "/api/session/login", {"username": ADMIN_USER, "password": ADMIN_PASS})
print(f"1. Admin Login: HTTP {code}")

# Scenario 1: Multi-file Upload + User Text (Caption)
# User types: "Here are the two project files for Q4 analysis"
# File 1: clean_spec.txt
# File 2: sensitive_salary.pdf (Contains PAN: ABCDE1234F & Mobile: +91 9876543210)
user_caption = "Here are the two project files for Q4 analysis, please summarize"
file1_text = "Clean Project Specification Document: Version 2.4. All systems operational."
file2_text = "CONFIDENTIAL SALARY LIST\nName: Priya Sharma\nPAN: ABCDE1234F\nMobile: +91 9876543210\n"

# Combined extracted text as prepared by Proxy
combined_extracted = f"USER_CAPTION:\n{user_caption}\n\n[FILE:clean_spec.txt]\n{file1_text}\n\n[FILE:sensitive_salary.pdf]\n{file2_text}"

prompt_formatted = f"[FILE UPLOAD] 2 files: clean_spec.txt, sensitive_salary.pdf | {user_caption}"

fields = {
    "platform": "ChatGPT",
    "prompt": prompt_formatted,
    "client_ip": "10.0.0.99",
    "agent_id": "qa-multi-agent",
    "agent_hostname": "QA-MULTI-RIG",
    "agent_type": "proxy",
    "file_name": "clean_spec.txt, sensitive_salary.pdf",
    "metadata": json.dumps({
        "file_name": "clean_spec.txt, sensitive_salary.pdf",
        "file_type": "application/pdf",
        "upload_scan": True,
        "extracted_text": combined_extracted,
        "multi_file_count": 2,
        "user_caption": user_caption
    })
}
files = {
    "file1": ("clean_spec.txt", file1_text.encode("utf-8"), "text/plain"),
    "file2": ("sensitive_salary.pdf", file2_text.encode("utf-8"), "application/pdf")
}

code, res_j = send_multipart("/api/browser-ai/intercept-file", fields, files)
action = res_j.get("action") if isinstance(res_j, dict) else ""
rule = res_j.get("rule_triggered") if isinstance(res_j, dict) else ""
print(f"2. Multi-File + Caption Interception: HTTP {code} | Action: {action} | Rule: {rule}")

# Scenario 2: User Types Sensitive Text directly in Caption while uploading Clean File
# File is clean, but user typed: "Please analyze this file, my mobile is +91 9876543210"
user_caption_sens = "Please analyze this spec, and call me at +91 9876543210 for questions."
combined_extracted_caption_sens = f"USER_CAPTION:\n{user_caption_sens}\n\n[FILE:clean_spec.txt]\n{file1_text}"

fields_caption_sens = {
    "platform": "Claude",
    "prompt": f"[FILE UPLOAD] clean_spec.txt | {user_caption_sens}",
    "client_ip": "10.0.0.99",
    "agent_id": "qa-multi-agent",
    "agent_hostname": "QA-MULTI-RIG",
    "agent_type": "proxy",
    "file_name": "clean_spec.txt",
    "metadata": json.dumps({
        "file_name": "clean_spec.txt",
        "file_type": "text/plain",
        "upload_scan": True,
        "extracted_text": combined_extracted_caption_sens,
        "multi_file_count": 1,
        "user_caption": user_caption_sens
    })
}
files_single = {
    "file": ("clean_spec.txt", file1_text.encode("utf-8"), "text/plain")
}
code, res_caption = send_multipart("/api/browser-ai/intercept-file", fields_caption_sens, files_single)
action_caption = res_caption.get("action") if isinstance(res_caption, dict) else ""
rule_caption = res_caption.get("rule_triggered") if isinstance(res_caption, dict) else ""
print(f"3. Clean File + Sensitive Caption Interception: HTTP {code} | Action: {action_caption} | Rule: {rule_caption}")

# Scenario 3: Global / Control Block Upload (Any file blocked regardless of content)
fields_block_all = {
    "platform": "Gemini",
    "prompt": "[FILE UPLOAD] public_notes.txt — Blocked (Block Upload)",
    "client_ip": "10.0.0.99",
    "agent_id": "qa-multi-agent",
    "agent_hostname": "QA-MULTI-RIG",
    "agent_type": "proxy",
    "file_name": "public_notes.txt",
    "metadata": json.dumps({
        "file_name": "public_notes.txt",
        "upload_scan": True,
        "is_blocked": True,
        "blocked_reason": "Block Upload",
        "extracted_text": "Clean public notes file."
    })
}
files_clean = {
    "file": ("public_notes.txt", b"Clean public notes file.", "text/plain")
}
code, res_block_all = send_multipart("/api/browser-ai/intercept-file", fields_block_all, files_clean)
action_block_all = res_block_all.get("action") if isinstance(res_block_all, dict) else ""
status_block_all = res_block_all.get("status") if isinstance(res_block_all, dict) else ""
print(f"4. Block Upload (Global/Policy) Interception: HTTP {code} | Action: {action_block_all} | Status: {status_block_all}")

# Scenario 4: Verify Database Persistence & Display of Caption + Multi-Files
code, logs_data = http_req("GET", "/api/browser-ai/logs?search=FILE+UPLOAD&limit=10")
logs = logs_data.get("logs", []) if isinstance(logs_data, dict) else []
print(f"5. DB Verification: Found {len(logs)} recent file upload logs in PostgreSQL")

found_multi = False
found_caption = False
for l in logs[:5]:
    preview = l.get("user_prompt_preview") or l.get("user_prompt_full") or ""
    print(f"   -> Log Entry: {preview[:90]}... | Action: {l.get('action')}")
    if "2 files" in preview or "clean_spec.txt, sensitive_salary.pdf" in preview:
        found_multi = True
    if "Please analyze" in preview or "Here are the two project files" in preview:
        found_caption = True

print("=" * 75)
print(f"Multi-File Intercepted: {'PASS' if action == 'Blocked' else 'FAIL'}")
print(f"Sensitive Caption Intercepted: {'PASS' if action_caption == 'Blocked' else 'FAIL'}")
print(f"Block Upload Policy Intercepted: {'PASS' if action_block_all == 'Blocked' else 'FAIL'}")
print(f"Caption Visible in DB Logs: {'PASS' if found_caption else 'FAIL'}")
print("=" * 75)
