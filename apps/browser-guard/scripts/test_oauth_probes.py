import json
import urllib.request
import urllib.error
import http.cookiejar

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
        with opener.open(r, timeout=15) as response:
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

api_req("/api/session/login", "POST", {"username": ADMIN_USER, "password": ADMIN_PASS})

# Test a set of top popular MCP servers
test_candidates = [
    {"name": "Apollo", "url": "https://mcp.apollo.io/mcp"},
    {"name": "Canva", "url": "https://mcp.canva.com/mcp"},
    {"name": "Airtable", "url": "https://mcp.airtable.com/mcp"},
    {"name": "Linear", "url": "https://mcp.linear.app/mcp"},
    {"name": "Notion", "url": "https://mcp.notion.com/mcp"},
    {"name": "Slack", "url": "https://mcp.slack.com/mcp"},
    {"name": "GitHub", "url": "https://mcp.github.com/mcp"},
    {"name": "Stripe", "url": "https://mcp.stripe.com/mcp"},
    {"name": "Zendesk", "url": "https://mcp.zendesk.com/mcp"},
]

results = []
for item in test_candidates:
    name = item["name"]
    server_url = item["url"]
    
    # 1. Test initiating OAuth with empty client_id (DCR)
    payload = {
        "name": f"test_probe_{name.lower()}",
        "connection_type": "http",
        "connection_string": {"value": server_url, "ref": ""},
        "is_code_mode_client": False,
        "is_ping_available": True,
        "auth_type": "oauth",
        "oauth_config": {
            "client_id": {"value": "", "ref": ""},
            "server_url": server_url
        },
        "tools_to_execute": ["*"],
        "allow_on_all_virtual_keys": True
    }
    
    code, res = api_req("/api/mcp/client", "POST", payload)
    auth_url = None
    dcr_status = "Failed"
    browser_page_status = "N/A"
    browser_page_note = ""
    
    if isinstance(res, dict) and res.get("status") == "pending_oauth":
        dcr_status = "Pending OAuth"
        auth_url = res.get("authorize_url")
        # Try fetching the authorize URL with browser user-agent
        try:
            req_b = urllib.request.Request(auth_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            with urllib.request.urlopen(req_b, timeout=10) as b_resp:
                browser_page_status = f"HTTP {b_resp.status} (Login Page Loaded)"
                browser_page_note = b_resp.geturl()[:80]
        except urllib.error.HTTPError as be:
            err_body = be.read().decode("utf-8", errors="ignore").strip()[:100]
            browser_page_status = f"HTTP {be.code}"
            browser_page_note = err_body.replace("\n", " ")
        except Exception as e:
            browser_page_status = "Error"
            browser_page_note = str(e)[:60]
    else:
        err_msg = res.get("error", {}).get("message") if isinstance(res, dict) else str(res)
        browser_page_note = (err_msg or "DCR not supported")[:100]
    
    print(f"[{name}] DCR: {dcr_status} | Browser Page: {browser_page_status} | Note: {browser_page_note[:60]}")
    results.append({
        "name": name,
        "dcr_status": dcr_status,
        "browser_page_status": browser_page_status,
        "note": browser_page_note
    })

