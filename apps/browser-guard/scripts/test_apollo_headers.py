import urllib.request
import urllib.error
import json

url = "https://mcp.apollo.io/mcp"
test_key = "rUdGun33AUZx4ZF4V0VVkA"

headers_to_test = [
    {"Authorization": f"Bearer {test_key}"},
    {"Authorization": test_key},
    {"x-api-key": test_key},
    {"X-Api-Key": test_key},
    {"X-API-KEY": test_key},
    {"api-key": test_key},
    {"Apollo-Api-Key": test_key},
]

payload = json.dumps({
    "jsonrpc": "2.0",
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "UnifAI", "version": "1.0"}
    },
    "id": 1
}).encode("utf-8")

for h in headers_to_test:
    req_headers = {"User-Agent": "UnifAI/1.0", "Content-Type": "application/json"}
    req_headers.update(h)
    req = urllib.request.Request(url, data=payload, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"Header: {h} -> HTTP {r.getcode()} SUCCESS!")
            print(r.read().decode())
            break
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"Header: {h} -> HTTP {e.code}: {body}")
    except Exception as e:
        print(f"Header: {h} -> Error: {e}")
