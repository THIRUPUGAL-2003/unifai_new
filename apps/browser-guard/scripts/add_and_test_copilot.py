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

print("=" * 70)
print("LIVE QA VALIDATION: MICROSOFT COPILOT TARGET DOMAIN")
print(f"Target Server: {BASE_URL}")
print("=" * 70)

# 1. Login
code, res = http_req("POST", "/api/session/login", {"username": ADMIN_USER, "password": ADMIN_PASS})
print(f"1. Admin Login: HTTP {code}, Role: {res.get('role') if isinstance(res, dict) else 'fail'}")

# 2. Verify Copilot Target Domain in Target List
code, res = http_req("GET", "/api/browser-ai/targets")
targets = res.get("targets", []) if isinstance(res, dict) else []
copilot_target = next((t for t in targets if "copilot" in (t.get("domain") or "").lower()), None)
if copilot_target:
    print(f"2. Copilot Target In DB: YES (ID: {copilot_target.get('id')}, Domain: {copilot_target.get('domain')}, Monitored: {copilot_target.get('monitored')})")
else:
    print("2. Copilot Target In DB: NOT FOUND")

# 3. Verify PAC File inclusion
code, pac_res = http_req("GET", "/api/browser-ai/pac")
pac_text = pac_res if isinstance(pac_res, str) else json.dumps(pac_res)
pac_has_copilot = "copilot.microsoft.com" in pac_text
print(f"3. PAC Auto-Config Includes Copilot: {'YES' if pac_has_copilot else 'NO'}")

# 4. Live Test: Safe Prompt on Copilot
safe_prompt = "How do I optimize database connection pooling in Go and Node.js?"
code, safe_res = http_req("POST", "/api/browser-ai/intercept", {
    "platform": "copilot.microsoft.com",
    "prompt": safe_prompt,
    "client_ip": "10.0.0.88",
    "agent_id": "copilot-qa-agent",
    "agent_hostname": "DESKTOP-COPILOT-QA",
    "agent_type": "proxy",
    "metadata": {"test": "copilot_live_safe"}
})
action_safe = safe_res.get("action") if isinstance(safe_res, dict) else "fail"
allowed_safe = safe_res.get("allowed") if isinstance(safe_res, dict) else False
print(f"4. Safe Prompt Test: HTTP {code} | Action: {action_safe} | Allowed: {allowed_safe}")

# 5. Live Test: Sensitive Prompt (DLP Block) on Copilot
sens_prompt = "Here is employee PAN number ABCDE1234F and mobile +91 9876543210 please update records."
code, sens_res = http_req("POST", "/api/browser-ai/intercept", {
    "platform": "copilot.microsoft.com",
    "prompt": sens_prompt,
    "client_ip": "10.0.0.88",
    "agent_id": "copilot-qa-agent",
    "agent_hostname": "DESKTOP-COPILOT-QA",
    "agent_type": "proxy",
    "metadata": {"test": "copilot_live_dlp"}
})
action_sens = sens_res.get("action") if isinstance(sens_res, dict) else "fail"
rule_sens = sens_res.get("rule_triggered") if isinstance(sens_res, dict) else ""
risk_sens = sens_res.get("risk_score") if isinstance(sens_res, dict) else 0
print(f"5. Sensitive Prompt (DLP Block) Test: HTTP {code} | Action: {action_sens} | Rule: {rule_sens} | Risk: {risk_sens}")

# 6. Live Test: File Upload Interception on Copilot
file_content = "CONFIDENTIAL FINANCIAL AUDIT\nPAN: ABCDE1234F\nContact: +91 9876543210\n"
fields = {
    "platform": "copilot.microsoft.com",
    "prompt": f"[FILE UPLOAD] copilot_audit.pdf: {file_content}",
    "client_ip": "10.0.0.88",
    "agent_id": "copilot-qa-agent",
    "agent_hostname": "DESKTOP-COPILOT-QA",
    "agent_type": "proxy",
    "file_name": "copilot_audit.pdf",
    "metadata": json.dumps({
        "file_name": "copilot_audit.pdf",
        "file_type": "application/pdf",
        "file_size": len(file_content),
        "upload_scan": True,
        "extracted_text": file_content
    })
}
files = {"file": ("copilot_audit.pdf", file_content.encode("utf-8"), "application/pdf")}
code, file_res = send_multipart("/api/browser-ai/intercept-file", fields, files)
action_file = file_res.get("action") if isinstance(file_res, dict) else "fail"
rule_file = file_res.get("rule_triggered") if isinstance(file_res, dict) else ""
print(f"6. File Upload DLP Interception Test: HTTP {code} | Action: {action_file} | Rule: {rule_file}")

# 7. Live Test: Voice Upload Interception on Copilot
voice_text = "Dictation for Copilot: Customer PAN is ABCDE1234F and mobile is +91 9876543210"
code, voice_res = http_req("POST", "/api/browser-ai/intercept", {
    "platform": "copilot.microsoft.com",
    "prompt": f"[VOICE UPLOAD] copilot_voice.wav: {voice_text}",
    "client_ip": "10.0.0.88",
    "agent_id": "copilot-qa-agent",
    "agent_hostname": "DESKTOP-COPILOT-QA",
    "agent_type": "proxy",
    "metadata": {
        "voice_upload": True,
        "file_name": "copilot_voice.wav",
        "transcript": voice_text,
        "extracted_text": voice_text
    }
})
action_voice = voice_res.get("action") if isinstance(voice_res, dict) else "fail"
rule_voice = voice_res.get("rule_triggered") if isinstance(voice_res, dict) else ""
print(f"7. Voice Upload DLP Interception Test: HTTP {code} | Action: {action_voice} | Rule: {rule_voice}")

# 8. Check Database Logs for Copilot Entries
code, logs_res = http_req("GET", "/api/browser-ai/logs?search=copilot&limit=10")
copilot_logs = logs_res.get("logs", []) if isinstance(logs_res, dict) else []
total_copilot_logs = logs_res.get("total", 0) if isinstance(logs_res, dict) else 0
print(f"8. Database Persistence for Copilot: Total Logs Recorded = {total_copilot_logs}")

print("=" * 70)
if action_safe == "Allowed" and action_sens == "Blocked" and action_file == "Blocked" and action_voice == "Blocked" and total_copilot_logs > 0:
    print("ALL COPILOT TARGET DOMAIN LIVE CHECKS PASSED SUCCESSFULLY! (100% WORKING)")
else:
    print("SOME CHECKS DID NOT MEET CRITERIA")
print("=" * 70)
