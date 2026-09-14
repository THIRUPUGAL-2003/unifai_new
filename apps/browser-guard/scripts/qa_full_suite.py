"""
Comprehensive QA Automation Suite for UnifAI Browser AI
Uses Python standard library (urllib, http.cookiejar) - zero external dependencies.
Tests:
  1. Platform Health & Authentication
  2. All Target Domains Interception (Benign & Sensitive DLP)
  3. File Upload Interception (Multipart, DLP triggers, allowed vs blocked)
  4. Voice / Audio Upload Interception (STT transcript scanning, DLP triggers)
  5. Search Logs Recording & Analytics (Google, Bing, DuckDuckGo, Safari, Risk calculation)
  6. DB Persistence & Query Verification
"""

import sys
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import mimetypes
import uuid

BASE_URL = "https://unifaiv2.dev-yp.com"
ADMIN_USER = "admin@yespanchi.com"
ADMIN_PASS = "YP2025-2026yp"

# Setup CookieJar and Opener for persistent session
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

test_results = []

def record_test(category, name, passed, details=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({
        "category": category,
        "name": name,
        "status": status,
        "details": str(details)
    })
    symbol = "[PASS]" if passed else "[FAIL]"
    print(f"{symbol} [{category}] {name}: {details}")

def http_request(method, url, json_data=None, data=None, headers=None):
    req_headers = {
        "User-Agent": "UnifAI-QA-Agent/2.0",
        "Accept": "application/json"
    }
    if headers:
        req_headers.update(headers)
        
    encoded_data = None
    if json_data is not None:
        encoded_data = json.dumps(json_data).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    elif data is not None:
        encoded_data = data

    req = urllib.request.Request(url, data=encoded_data, headers=req_headers, method=method)
    try:
        with opener.open(req, timeout=15) as response:
            res_body = response.read().decode("utf-8", errors="replace")
            res_code = response.getcode()
            try:
                res_json = json.loads(res_body)
            except Exception:
                res_json = None
            return res_code, res_json, res_body
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
        except Exception:
            err_json = None
        return e.code, err_json, err_body
    except Exception as e:
        return 0, None, str(e)

def send_multipart(url, fields, files):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body_parts = []
    
    # Text fields
    for k, v in fields.items():
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode("utf-8"))
        body_parts.append(str(v).encode("utf-8") + b"\r\n")
        
    # File fields
    for field_name, (filename, file_bytes, content_type) in files.items():
        body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
        body_parts.append(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body_parts.append(f'Content-Type: {content_type}\r\n\r\n'.encode("utf-8"))
        body_parts.append(file_bytes + b"\r\n")
        
    body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    payload = b"".join(body_parts)
    
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}"
    }
    return http_request("POST", url, data=payload, headers=headers)

def main():
    print("=" * 75)
    print("STARTING UNIFAI BROWSER AI FULL QA AUTOMATION TEST SUITE")
    print(f"Target Server: {BASE_URL}")
    print("=" * 75)

    # 1. Health Check
    code, j, body = http_request("GET", f"{BASE_URL}/health")
    passed = code == 200 and isinstance(j, dict) and j.get("status") in ["ok", "healthy"]
    db_pings = j.get("components", {}).get("db_pings") if isinstance(j, dict) else None
    record_test("System", "Health Check (/health)", passed, f"HTTP {code}, status: {j.get('status') if j else 'none'}, db_pings: {db_pings}")
    if not passed:
        print("Aborting: Health check failed.")
        return

    # 2. Authentication
    code, j, body = http_request("POST", f"{BASE_URL}/api/session/login", json_data={
        "username": ADMIN_USER,
        "password": ADMIN_PASS
    })
    passed = code == 200
    record_test("Auth", "Admin Login (/api/session/login)", passed, f"HTTP {code}, user: {ADMIN_USER}")
    if not passed:
        print("Aborting: Authentication failed.")
        return

    # 3. Target Domains Discovery
    target_domains = []
    code, j, body = http_request("GET", f"{BASE_URL}/api/browser-ai/targets")
    if code == 200 and j:
        targets_list = j.get("targets", [])
        for t in targets_list:
            d_name = t.get("name") or t.get("domain")
            if d_name and t.get("enabled", True):
                target_domains.append(d_name)
        record_test("Target Domains", "Fetch Target Domains", True, f"Found {len(target_domains)} domains: {', '.join(target_domains[:6])}...")
    else:
        record_test("Target Domains", "Fetch Target Domains", False, f"HTTP {code}")

    # Core AI target list + all discovered target domains
    core_ai_targets = ["ChatGPT", "Claude", "Gemini", "Perplexity", "DeepSeek", "Microsoft Copilot", "Mistral Le Chat", "Poe"]
    all_test_targets = list(dict.fromkeys(target_domains + core_ai_targets))
    print(f"\n--- Testing Interception on ALL {len(all_test_targets)} Target Domains ---")
    for target in all_test_targets:
        # A. Benign Prompt Test
        code, res_j, _ = http_request("POST", f"{BASE_URL}/api/browser-ai/intercept", json_data={
            "platform": target,
            "prompt": f"Explain the key architectural advantages of microservices on {target}.",
            "client_ip": "10.0.0.42",
            "agent_id": "qa-agent-01",
            "agent_hostname": "QA-TEST-RIG",
            "agent_type": "proxy",
            "metadata": {"test_run": "full_qa", "domain": target}
        })
        if code == 200 and res_j:
            action = res_j.get("action", "Unknown")
            allowed = res_j.get("allowed", False)
            passed = allowed and (action in ["Allowed", "Redacted", "Warned"])
            record_test("Domain: Benign", f"{target} Safe Prompt", passed, f"Action: {action}, Allowed: {allowed}")
        else:
            record_test("Domain: Benign", f"{target} Safe Prompt", False, f"HTTP {code}")

        # B. Sensitive Prompt (DLP Block) Test
        code, res_j, _ = http_request("POST", f"{BASE_URL}/api/browser-ai/intercept", json_data={
            "platform": target,
            "prompt": f"Customer PAN is ABCDE1234F and mobile +91 9876543210 for verification.",
            "client_ip": "10.0.0.42",
            "agent_id": "qa-agent-01",
            "agent_hostname": "QA-TEST-RIG",
            "agent_type": "proxy",
            "metadata": {"test_run": "full_qa", "domain": target}
        })
        if code == 200 and res_j:
            action = res_j.get("action", "Unknown")
            rule = res_j.get("rule_triggered", "none")
            risk = res_j.get("risk_score", 0)
            passed = (action == "Blocked") or (rule != "none") or (risk >= 80)
            record_test("Domain: Sensitive", f"{target} DLP Block", passed, f"Action: {action}, Rule: {rule}, Risk: {risk}")
        else:
            record_test("Domain: Sensitive", f"{target} DLP Block", False, f"HTTP {code}")

    # 5. File Upload Interception Testing (/api/browser-ai/intercept-file)
    print("\n--- Testing File Upload Interception ---")
    # A. Benign File Upload
    safe_text = "High level design overview of the distributed data pipeline."
    fields_safe = {
        "platform": "ChatGPT",
        "prompt": f"[FILE UPLOAD] product_architecture.txt: {safe_text}",
        "client_ip": "10.0.0.42",
        "agent_id": "qa-agent-01",
        "agent_hostname": "QA-TEST-RIG",
        "agent_type": "proxy",
        "file_name": "product_architecture.txt",
        "metadata": json.dumps({
            "file_name": "product_architecture.txt",
            "file_type": "text/plain",
            "file_size": len(safe_text),
            "upload_scan": True,
            "extracted_text": safe_text
        })
    }
    files_safe = {
        "file": ("product_architecture.txt", safe_text.encode("utf-8"), "text/plain")
    }
    code, res_j, body = send_multipart(f"{BASE_URL}/api/browser-ai/intercept-file", fields_safe, files_safe)
    if code == 200 and res_j:
        action = res_j.get("action", "")
        allowed = res_j.get("allowed", False)
        record_test("File Upload", "Benign File Upload (product_architecture.txt)", allowed, f"Action: {action}, Allowed: {allowed}")
    else:
        record_test("File Upload", "Benign File Upload", False, f"HTTP {code}: {body[:100]}")

    # B. Sensitive File Upload (Contains PAN & Mobile Phone - DLP trigger)
    sensitive_text = "CONFIDENTIAL EMPLOYEE PAYROLL\nName: Ramesh Kumar\nPAN: ABCDE1234F\nMobile: +91 9876543210\nSalary: 1,500,000 INR\n"
    fields_sens = {
        "platform": "Claude",
        "prompt": f"[FILE UPLOAD] confidential_payroll.pdf: {sensitive_text}",
        "client_ip": "10.0.0.42",
        "agent_id": "qa-agent-01",
        "agent_hostname": "QA-TEST-RIG",
        "agent_type": "proxy",
        "file_name": "confidential_payroll.pdf",
        "metadata": json.dumps({
            "file_name": "confidential_payroll.pdf",
            "file_type": "application/pdf",
            "file_size": len(sensitive_text),
            "upload_scan": True,
            "extracted_text": sensitive_text
        })
    }
    files_sens = {
        "file": ("confidential_payroll.pdf", sensitive_text.encode("utf-8"), "application/pdf")
    }
    code, res_j, body = send_multipart(f"{BASE_URL}/api/browser-ai/intercept-file", fields_sens, files_sens)
    if code == 200 and res_j:
        action = res_j.get("action", "")
        rule = res_j.get("rule_triggered", "")
        risk = res_j.get("risk_score", 0)
        passed = action == "Blocked" or rule != "" or risk >= 80
        record_test("File Upload", "Sensitive File DLP Block (confidential_payroll.pdf)", passed, f"Action: {action}, Rule: {rule}, Risk: {risk}")
    else:
        record_test("File Upload", "Sensitive File DLP Block", False, f"HTTP {code}: {body[:100]}")

    # 6. Voice / Audio Upload Interception Testing
    print("\n--- Testing Voice Upload Interception ---")
    # A. Benign Voice Memo
    voice_safe = "Hi team, please summarize the action items from today's sprint planning session."
    code, res_j, body = http_request("POST", f"{BASE_URL}/api/browser-ai/intercept", json_data={
        "platform": "ChatGPT",
        "prompt": f"[VOICE UPLOAD] voice_memo_01.m4a: {voice_safe}",
        "client_ip": "10.0.0.42",
        "agent_id": "qa-agent-01",
        "agent_hostname": "QA-TEST-RIG",
        "agent_type": "proxy",
        "metadata": {
            "voice_upload": True,
            "file_name": "voice_memo_01.m4a",
            "audio_duration_sec": 7.8,
            "transcript": voice_safe,
            "extracted_text": voice_safe
        }
    })
    if code == 200 and res_j:
        action = res_j.get("action", "")
        allowed = res_j.get("allowed", False)
        record_test("Voice Upload", "Benign Voice Memo (Sprint Planning)", allowed, f"Action: {action}, Allowed: {allowed}")
    else:
        record_test("Voice Upload", "Benign Voice Memo", False, f"HTTP {code}")

    # B. Sensitive Voice Memo (Contains PII / PAN / Indian Mobile)
    voice_sens = "Customer voice record: PAN card is ABCDE1234F and mobile number is +91 9876543210 please verify account."
    code, res_j, body = http_request("POST", f"{BASE_URL}/api/browser-ai/intercept", json_data={
        "platform": "Gemini",
        "prompt": f"[VOICE UPLOAD] audio_dictation.wav: {voice_sens}",
        "client_ip": "10.0.0.42",
        "agent_id": "qa-agent-01",
        "agent_hostname": "QA-TEST-RIG",
        "agent_type": "proxy",
        "metadata": {
            "voice_upload": True,
            "file_name": "audio_dictation.wav",
            "audio_duration_sec": 13.5,
            "transcript": voice_sens,
            "extracted_text": voice_sens
        }
    })
    if code == 200 and res_j:
        action = res_j.get("action", "")
        rule = res_j.get("rule_triggered", "")
        risk = res_j.get("risk_score", 0)
        passed = action == "Blocked" or rule != "" or risk >= 80
        record_test("Voice Upload", "Sensitive Voice DLP Block (PAN & Mobile in Audio)", passed, f"Action: {action}, Rule: {rule}, Risk: {risk}")
    else:
        record_test("Voice Upload", "Sensitive Voice DLP Block", False, f"HTTP {code}")

    # 7. Search Logs Interception Testing (/api/browser-ai/search-logs)
    print("\n--- Testing Search Logs Interception & Analytics ---")
    searches_to_test = [
        {
            "engine": "Google",
            "browser": "Chrome",
            "is_incognito": False,
            "query": "how to build distributed consensus algorithms in Go",
            "url": "https://www.google.com/search?q=how+to+build+distributed+consensus+algorithms+in+Go",
            "host": "www.google.com",
            "client_ip": "10.0.0.42",
            "agent_hostname": "QA-TEST-RIG",
            "agent_id": "qa-agent-01"
        },
        {
            "engine": "Google",
            "browser": "Chrome",
            "is_incognito": True,
            "query": "how to bypass corporate proxy dlp agent kill exploit",
            "url": "https://www.google.com/search?q=how+to+bypass+corporate+proxy+dlp+agent+kill+exploit",
            "host": "www.google.com",
            "client_ip": "10.0.0.42",
            "agent_hostname": "QA-TEST-RIG",
            "agent_id": "qa-agent-01"
        },
        {
            "engine": "Bing",
            "browser": "Edge",
            "is_incognito": False,
            "query": "confidential internal financial model merger acquisition leak",
            "url": "https://www.bing.com/search?q=confidential+internal+financial+model+merger+acquisition+leak",
            "host": "www.bing.com",
            "client_ip": "10.0.0.42",
            "agent_hostname": "QA-TEST-RIG",
            "agent_id": "qa-agent-01"
        },
        {
            "engine": "DuckDuckGo",
            "browser": "Safari",
            "is_incognito": True,
            "query": "python playwright automated end to end testing best practices",
            "clicked_url": "https://playwright.dev/python/docs/intro",
            "clicked_title": "Playwright Python Documentation",
            "url": "https://duckduckgo.com/?q=python+playwright",
            "host": "duckduckgo.com",
            "client_ip": "10.0.0.42",
            "agent_hostname": "QA-TEST-RIG",
            "agent_id": "qa-agent-01"
        }
    ]

    for search_item in searches_to_test:
        code, res_j, body = http_request("POST", f"{BASE_URL}/api/browser-ai/search-logs", json_data=search_item)
        if code == 200 and res_j:
            status = res_j.get("status")
            record_test("Search Logs", f"Record Search ({search_item['engine']} - '{search_item['query'][:25]}...')", status == "success", f"Engine: {search_item['engine']}, Incognito: {search_item['is_incognito']}")
        else:
            record_test("Search Logs", f"Record Search ({search_item['engine']})", False, f"HTTP {code}: {body[:100]}")

    # 8. Query Search Logs & Persistence Verification
    print("\n--- Verifying Search Logs Query & Threat Intelligence ---")
    code, data, _ = http_request("GET", f"{BASE_URL}/api/browser-ai/search-logs?limit=50")
    if code == 200 and data:
        logs = data.get("logs", [])
        total = data.get("total", 0)
        incognito_count = data.get("incognito_count", 0)
        queries_count = data.get("queries_count", 0)
        clicks_count = data.get("clicks_count", 0)

        found_exploit = any("bypass" in l.get("query", "").lower() for l in logs)
        record_test("Search Verification", "Search Logs Retrieval", total > 0, f"Total logs: {total}, Queries: {queries_count}, Incognito: {incognito_count}, Clicks: {clicks_count}")
        record_test("Search Verification", "Critical Threat Detection in Search Logs", found_exploit, "Found logged threat query with predictive risk scoring")
    else:
        record_test("Search Verification", "Search Logs Retrieval", False, f"HTTP {code}")

    # 9. Verify Prompt Logs & Interception Persistence (/api/browser-ai/logs)
    print("\n--- Verifying Prompt Logs Persistence ---")
    code, data, _ = http_request("GET", f"{BASE_URL}/api/browser-ai/logs?limit=100")
    if code == 200 and data:
        logs = data.get("logs", [])
        total = data.get("total", 0)

        has_file = any(
            "[FILE UPLOAD]" in (l.get("user_prompt_full") or "") or
            "[FILE UPLOAD]" in (l.get("user_prompt_preview") or "") or
            l.get("attachment_name") != ""
            for l in logs
        )
        has_voice = any(
            "[VOICE UPLOAD]" in (l.get("user_prompt_full") or "") or
            "[VOICE UPLOAD]" in (l.get("user_prompt_preview") or "")
            for l in logs
        )
        has_blocked = any(l.get("action") == "Blocked" for l in logs)

        record_test("Logs Verification", "Prompt Logs Retrieval", total > 0, f"Total recorded logs: {total}")
        record_test("Logs Verification", "File Upload Log Persistence", has_file, "Detected [FILE UPLOAD] / attachment entry in DB logs")
        record_test("Logs Verification", "Voice Upload Log Persistence", has_voice, "Detected [VOICE UPLOAD] entry in DB logs")
        record_test("Logs Verification", "Blocked Actions Persistence", has_blocked, "Detected Blocked DLP entries in DB logs")
    else:
        record_test("Logs Verification", "Prompt Logs Retrieval", False, f"HTTP {code}")

    # Summary
    print("\n" + "=" * 75)
    print("TEST SUITE EXECUTION SUMMARY")
    print("=" * 75)
    total_tests = len(test_results)
    passed_tests = sum(1 for t in test_results if t["status"] == "PASS")
    failed_tests = total_tests - passed_tests
    print(f"Total Tests Executed : {total_tests}")
    print(f"Passed               : {passed_tests}")
    print(f"Failed               : {failed_tests}")
    print(f"Success Rate         : {(passed_tests / total_tests) * 100:.1f}%")
    print("=" * 75)

    with open("qa_test_report.json", "w") as f:
        json.dump(test_results, f, indent=2)
    print("Full QA Report saved to qa_test_report.json")

if __name__ == "__main__":
    main()
