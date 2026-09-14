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

code, res = req("/api/session/login", "POST", {"username": ADMIN_USER, "password": ADMIN_PASS})
print("Login:", code)

payload = {
    "name": "AWS_Marketplace",
    "connection_type": "http",
    "connection_string": {"value": "https://marketplace-mcp.us-east-1.api.aws/", "ref": ""},
    "is_code_mode_client": False,
    "is_ping_available": True,
    "auth_type": "oauth",
    "oauth_config": {
        "client_id": {"value": "", "ref": ""},
        "server_url": "https://marketplace-mcp.us-east-1.api.aws/"
    },
    "tools_to_execute": ["*"],
    "allow_on_all_virtual_keys": True
}

code, res = req("/api/mcp/client", "POST", payload)
print("AWS Marketplace Install Result:")
print("HTTP Code:", code)
print("Response:", res)
