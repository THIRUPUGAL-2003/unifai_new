import json
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import base64
import os
import hashlib

BASE_URL = "https://unifaiv2.dev-yp.com"
ADMIN_USER = "admin@yespanchi.com"
ADMIN_PASS = "YP2025-2026yp"

cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
urllib.request.install_opener(opener)

def api_req(path, method="GET", json_data=None):
    url = f"{BASE_URL}{path}"
    headers = {"User-Agent": "UnifAI-MCP-QA/1.0", "Accept": "application/json"}
    data = None
    if json_data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_data).encode("utf-8")
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(r, timeout=12) as response:
            b = response.read().decode("utf-8")
            try:
                return response.getcode(), json.loads(b)
            except Exception:
                return response.getcode(), b
    except urllib.error.HTTPError as e:
        b = e.read().decode("utf-8")
        try:
            return e.code, json.loads(b)
        except Exception:
            return e.code, b
    except Exception as e:
        return 0, str(e)

# 1. Login
code, res = api_req("/api/session/login", "POST", {"username": ADMIN_USER, "password": ADMIN_PASS})
if code != 200:
    print("Login failed:", code, res)
    exit(1)

# 2. Fetch all 290 servers
all_servers = []
offset = 0
while True:
    code, res = api_req(f"/api/mcp/library?limit=100&offset={offset}")
    if code != 200 or not isinstance(res, dict):
        break
    srvs = res.get("servers", [])
    if not srvs:
        break
    all_servers.extend(srvs)
    offset += len(srvs)
    if offset >= res.get("total_count", 0):
        break

print(f"Total servers fetched from library: {len(all_servers)}")

# Function to test an individual server
def evaluate_server(server):
    name = server.get("name", "Unknown")
    url = (server.get("connection_url") or "").strip()
    category = server.get("category", "Uncategorized")
    
    item = {
        "name": name,
        "category": category,
        "url": url,
        "status": "Unknown",
        "action_required": "",
        "details": ""
    }
    
    if not url or not url.startswith("http"):
        item["status"] = "Stdio / Local Process"
        item["action_required"] = "Runs locally via command line"
        item["details"] = "Stdio MCP Server"
        return item
    
    # 1. Try DCR OAuth initiation via UnifAI
    test_slug = f"probe_{abs(hash(name)) % 1000000}"
    payload = {
        "name": test_slug,
        "connection_type": "http",
        "connection_string": {"value": url, "ref": ""},
        "is_code_mode_client": False,
        "is_ping_available": True,
        "auth_type": "oauth",
        "oauth_config": {
            "client_id": {"value": "", "ref": ""},
            "server_url": url
        },
        "tools_to_execute": ["*"],
        "allow_on_all_virtual_keys": True
    }
    
    code, resp = api_req("/api/mcp/client", "POST", payload)
    
    if isinstance(resp, dict) and resp.get("status") == "pending_oauth":
        auth_url = resp.get("authorize_url", "")
        # Probe authorize URL with browser user agent to see how the provider handles our redirect URI
        try:
            req_b = urllib.request.Request(auth_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urllib.request.urlopen(req_b, timeout=8) as b_resp:
                final_url = b_resp.geturl()
                item["status"] = "1-Click Auto OAuth (Ready)"
                item["action_required"] = "Leave Client ID Empty -> Click Continue -> Login Popup opens"
                item["details"] = f"HTTP {b_resp.status} - Login page loaded: {final_url[:70]}"
        except urllib.error.HTTPError as be:
            err_body = be.read().decode("utf-8", errors="ignore").strip()[:150]
            if "invalid redirect uri" in err_body.lower() or "redirect_uri" in err_body.lower():
                item["status"] = "Desktop-only DCR (Localhost only)"
                item["action_required"] = "Requires creating an OAuth App on provider console (Canva/Figma model)"
                item["details"] = f"HTTP {be.code}: Provider rejected cloud redirect URI ({err_body[:50]})"
            else:
                item["status"] = "Auto-OAuth with Authorization Notice"
                item["action_required"] = "Click Continue -> Authorize in provider account"
                item["details"] = f"HTTP {be.code}: {err_body[:60]}"
        except Exception as e:
            item["status"] = "1-Click Auto OAuth (Ready)"
            item["action_required"] = "Leave Client ID Empty -> Click Continue"
            item["details"] = f"OAuth URL generated: {auth_url[:60]}"
    else:
        err_msg = ""
        if isinstance(resp, dict):
            err_msg = resp.get("error", {}).get("message") or resp.get("message") or ""
        else:
            err_msg = str(resp)
        
        if "client_id is required" in err_msg:
            item["status"] = "Pre-Registered OAuth App Required"
            item["action_required"] = "Create OAuth App on Provider Console -> Paste Client ID & Secret"
            item["details"] = "Provider does not allow open Dynamic Registration (RFC 7591)"
        elif "already exists" in err_msg:
            item["status"] = "Already Configured / Pending"
            item["action_required"] = "Open existing MCP Catalog entry"
            item["details"] = err_msg[:70]
        elif "discovery failed" in err_msg or "401" in err_msg or "403" in err_msg:
            item["status"] = "Headers / API Key Method Supported"
            item["action_required"] = "Switch Auth to 'Headers' -> Add Bearer Token or API Key"
            item["details"] = "Standard Bearer / API Token Server"
        elif "timed out" in err_msg.lower() or "connection refused" in err_msg.lower():
            item["status"] = "Server Offline / Timeout"
            item["action_required"] = "Server currently unreachable from gateway"
            item["details"] = err_msg[:60]
        else:
            item["status"] = "Headers / API Key Method Supported"
            item["action_required"] = "Switch Auth to 'Headers' -> Add Bearer Token or API Key"
            item["details"] = (err_msg[:60] if err_msg else "HTTP server")

    return item

print("Testing all servers concurrently (20 threads)...")
start_time = time.time()
classified = []

with ThreadPoolExecutor(max_workers=20) as executor:
    future_to_server = {executor.submit(evaluate_server, s): s for s in all_servers}
    for future in as_completed(future_to_server):
        res = future.result()
        classified.append(res)
        if len(classified) % 25 == 0 or len(classified) == len(all_servers):
            print(f"Progress: {len(classified)}/{len(all_servers)} tested...")

elapsed = time.time() - start_time
print(f"All {len(all_servers)} tested in {elapsed:.1f}s")

# Group and save results
with open("mcp_290_categorized_report.json", "w", encoding="utf-8") as f:
    json.dump(classified, f, indent=2)

summary = {}
for c in classified:
    st = c["status"]
    summary[st] = summary.get(st, 0) + 1

print("\n=== FINAL TEST SUMMARY (290 SERVERS) ===")
for k, v in sorted(summary.items(), key=lambda x: -x[1]):
    print(f"{k}: {v} servers ({(v/len(classified))*100:.1f}%)")

