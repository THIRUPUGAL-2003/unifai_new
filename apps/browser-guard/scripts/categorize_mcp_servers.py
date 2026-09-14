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

# Fetch all servers
all_servers = []
offset = 0
while True:
    code, res = req(f"/api/mcp/library?limit=100&offset={offset}")
    if code != 200 or not isinstance(res, dict):
        break
    servers = res.get("servers", [])
    if not servers:
        break
    all_servers.extend(servers)
    offset += len(servers)
    if offset >= res.get("total_count", 0):
        break

print(f"Total fetched: {len(all_servers)}")

auth_counts = {}
for s in all_servers:
    at = s.get("auth_type") or "none"
    ct = s.get("connection_type") or "http"
    key = f"{at} ({ct})"
    auth_counts[key] = auth_counts.get(key, 0) + 1

print("Distribution:")
for k, v in sorted(auth_counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

no_auth = [s for s in all_servers if (s.get("auth_type") or "none") == "none"]
print(f"\nServers with auth_type='none' ({len(no_auth)}):")
for s in no_auth[:15]:
    print(f"  - {s.get('name')} | conn={s.get('connection_type')} | url={s.get('connection_url')}")
