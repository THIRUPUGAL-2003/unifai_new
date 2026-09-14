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

def req(path, method="GET", json_data=None):
    url = f"{BASE_URL}{path}"
    headers = {"User-Agent": "UnifAI-QA/1.0", "Accept": "application/json"}
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

print("=" * 70)
print("TESTING ALL MCP GATEWAY ENDPOINTS ON LIVE SERVER")
print(f"Target Server: {BASE_URL}")
print("=" * 70)

# 1. Login
code, res = req("/api/session/login", "POST", {"username": ADMIN_USER, "password": ADMIN_PASS})
print(f"1. Login: HTTP {code}")

# 2. MCP Catalog (/workspace/mcp-registry)
code, res = req("/api/mcp/clients")
print(f"2. MCP Catalog (/api/mcp/clients): HTTP {code} | Total: {res.get('total_count') if isinstance(res, dict) else res}")

# 3. MCP Library (/workspace/mcp-registry/library)
code, res = req("/api/mcp/library?limit=10")
print(f"3. MCP Library (/api/mcp/library): HTTP {code} | Total Available: {res.get('total_count') if isinstance(res, dict) else res}")

# 4. MCP Tool Groups (/workspace/mcp-tool-groups)
code, res = req("/api/mcp/tool-groups")
print(f"4. Tool Groups (/api/mcp/tool-groups): HTTP {code} | Groups: {len(res.get('tool_groups', [])) if isinstance(res, dict) else res}")

# 5. Auth Sessions (/workspace/mcp-sessions)
code, res = req("/api/mcp/sessions")
print(f"5. Auth Sessions (/api/mcp/sessions): HTTP {code} | Sessions: {len(res.get('sessions', [])) if isinstance(res, dict) else res}")

# 6. OAuth Grants (/workspace/oauth-grants)
code, res = req("/api/oauth2/sessions")
print(f"6. OAuth Grants (/api/oauth2/sessions): HTTP {code} | Grants: {len(res.get('sessions', [])) if isinstance(res, dict) else res}")

# 7. MCP Settings (/workspace/mcp-settings)
code, res = req("/api/config")
mcp_url = ""
if isinstance(res, dict):
    mcp_url = res.get("mcp_external_client_url", "")
print(f"7. MCP Settings (/api/config): HTTP {code} | External Client URL: {mcp_url or 'default'}")

print("=" * 70)
