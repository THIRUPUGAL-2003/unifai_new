import urllib.request
import urllib.error
import json

url = "https://mcp.apollo.io/mcp"

print("1. Checking Apollo.io MCP endpoint response...")
req = urllib.request.Request(
    url,
    headers={"User-Agent": "UnifAI-Test/1.0", "Accept": "application/json"},
    method="GET"
)
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print("GET Status:", r.getcode())
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print("GET HTTP Status:", e.code)
    print("Headers:")
    for k, v in e.headers.items():
        print(f"  {k}: {v}")
    print("Body:", e.read().decode())
except Exception as e:
    print("Error:", e)

print("\n2. Checking POST with JSON-RPC initialize...")
post_req = urllib.request.Request(
    url,
    data=json.dumps({
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "UnifAI", "version": "1.0"}
        },
        "id": 1
    }).encode("utf-8"),
    headers={"User-Agent": "UnifAI-Test/1.0", "Content-Type": "application/json", "Accept": "application/json"},
    method="POST"
)
try:
    with urllib.request.urlopen(post_req, timeout=10) as r:
        print("POST Status:", r.getcode())
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print("POST HTTP Status:", e.code)
    print("Headers:")
    for k, v in e.headers.items():
        print(f"  {k}: {v}")
    print("Body:", e.read().decode())
except Exception as e:
    print("Error:", e)
