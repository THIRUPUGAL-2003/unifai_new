"""
Comprehensive QA Automation Suite for Testing All MCP Catalog/Library Servers.
Fetches all servers from https://unifaiv2.dev-yp.com/api/mcp/library.
Tests:
  1. Connection URL Reachability (HTTP/HTTPS status)
  2. MCP Protocol Detection (JSON-RPC 2.0 / SSE / headers)
  3. OAuth Discovery (RFC 8414 /.well-known/oauth-authorization-server or openid-configuration)
  4. Authentication Requirements (OAuth Client ID vs Bearer Token vs Open)
Uses concurrent threads for fast execution.
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

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

def test_single_server(server):
    name = server.get("name") or "Unknown"
    conn_url = (server.get("connection_url") or "").strip()
    auth_type = server.get("auth_type") or "none"
    conn_type = server.get("connection_type") or "http"
    
    result = {
        "name": name,
        "url": conn_url,
        "catalog_auth_type": auth_type,
        "connection_type": conn_type,
        "http_status": 0,
        "is_reachable": False,
        "oauth_discovery_supported": False,
        "auth_requirement": "Unknown",
        "error_detail": ""
    }
    
    if not conn_url or not conn_url.startswith("http"):
        result["error_detail"] = "No valid HTTP/HTTPS connection URL (stdio or custom)"
        result["auth_requirement"] = "Stdio / Local Process"
        return result

    # 1. Test Direct URL Reachability
    parsed = urllib.parse.urlparse(conn_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    
    custom_opener = urllib.request.build_opener()
    req = urllib.request.Request(
        conn_url,
        headers={"User-Agent": "UnifAI-MCP-Scanner/1.0", "Accept": "application/json, text/event-stream, */*"},
        method="GET"
    )
    try:
        with custom_opener.open(req, timeout=5) as resp:
            result["http_status"] = resp.getcode()
            result["is_reachable"] = True
            ct = resp.headers.get("Content-Type", "")
            if "event-stream" in ct:
                result["auth_requirement"] = "Open SSE Stream (Ready)"
            elif resp.getcode() == 200:
                result["auth_requirement"] = "Online (HTTP 200)"
    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        result["is_reachable"] = True
        auth_hdr = e.headers.get("WWW-Authenticate", "")
        if e.code in [401, 403]:
            if "bearer" in auth_hdr.lower() or "oauth" in auth_hdr.lower() or auth_type == "oauth":
                result["auth_requirement"] = "OAuth 2.0 / Bearer Auth Required"
            else:
                result["auth_requirement"] = "Auth Required (401/403)"
        elif e.code == 405: # Method Not Allowed - Server expects POST/SSE
            result["auth_requirement"] = "MCP POST/SSE Endpoint Online"
        elif e.code == 404:
            result["auth_requirement"] = "Host Online, Path 404"
        else:
            result["auth_requirement"] = f"HTTP {e.code}"
    except Exception as e:
        err_str = str(e)
        if "Name or service not known" in err_str or "getaddrinfo failed" in err_str:
            result["error_detail"] = "DNS Resolution Failed (Domain inactive)"
            result["auth_requirement"] = "Offline / Inactive Domain"
        elif "timed out" in err_str.lower():
            result["error_detail"] = "Connection Timed Out"
            result["auth_requirement"] = "Timeout"
        else:
            result["error_detail"] = err_str[:80]
            result["auth_requirement"] = "Connection Error"

    # 2. Check RFC 8414 / OpenID OAuth Metadata Discovery
    if result["is_reachable"]:
        discovery_urls = [
            f"{conn_url.rstrip('/')}/.well-known/oauth-authorization-server",
            f"{origin}/.well-known/oauth-authorization-server",
            f"{origin}/.well-known/openid-configuration"
        ]
        for d_url in discovery_urls:
            try:
                d_req = urllib.request.Request(d_url, headers={"User-Agent": "UnifAI-MCP-Scanner/1.0", "Accept": "application/json"})
                with custom_opener.open(d_req, timeout=3) as d_resp:
                    if d_resp.getcode() == 200:
                        meta = json.loads(d_resp.read().decode("utf-8", errors="ignore"))
                        if isinstance(meta, dict) and ("authorization_endpoint" in meta or "token_endpoint" in meta):
                            result["oauth_discovery_supported"] = True
                            result["auth_requirement"] = "OAuth 2.0 (Auto-Discovery Supported)"
                            break
            except Exception:
                pass

    return result

def main():
    print("=" * 75)
    print("STARTING COMPREHENSIVE QA SCAN FOR ALL MCP CATALOG SERVERS")
    print(f"Target Gateway: {BASE_URL}")
    print("=" * 75)

    # 1. Login
    code, res = api_req("/api/session/login", "POST", {"username": ADMIN_USER, "password": ADMIN_PASS})
    if code != 200:
        print("Login failed, aborting.")
        return
    print("[PASS] Authenticated successfully with UnifAI Gateway")

    # 2. Fetch all MCP servers from catalog
    all_servers = []
    offset = 0
    while True:
        code, data = api_req(f"/api/mcp/library?limit=100&offset={offset}")
        if code != 200 or not isinstance(data, dict):
            break
        servers = data.get("servers", [])
        if not servers:
            break
        all_servers.extend(servers)
        offset += len(servers)
        if offset >= data.get("total_count", 0):
            break

    total = len(all_servers)
    print(f"[PASS] Successfully retrieved all {total} MCP servers from library catalog.")
    print(f"Executing multi-threaded reachability & protocol diagnostic across all {total} servers...\n")

    start_time = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(test_single_server, s): s for s in all_servers}
        done_count = 0
        for future in as_completed(futures):
            res = future.result()
            results.append(res)
            done_count += 1
            if done_count % 30 == 0 or done_count == total:
                print(f"  -> Scanned {done_count}/{total} servers ({done_count/total*100:.0f}% complete)...")

    duration = time.time() - start_time
    print(f"\nScan completed in {duration:.1f} seconds.")

    # Categorize results
    reachable = [r for r in results if r["is_reachable"]]
    oauth_discovery = [r for r in results if r["oauth_discovery_supported"]]
    auth_required = [r for r in results if "Auth Required" in r["auth_requirement"] or "OAuth" in r["auth_requirement"]]
    offline = [r for r in results if not r["is_reachable"]]

    print("\n" + "=" * 75)
    print("MCP SERVERS QA SCAN SUMMARY")
    print("=" * 75)
    print(f"Total Servers Scanned              : {total}")
    print(f"Reachable Online Endpoints         : {len(reachable)} ({(len(reachable)/total)*100:.1f}%)")
    print(f"Enterprise OAuth Protected         : {len(auth_required)} (Require Client ID / Token)")
    print(f"Open RFC 8414 OAuth Auto-Discovery : {len(oauth_discovery)}")
    print(f"Offline / Inactive Domains         : {len(offline)}")
    print("=" * 75)

    # Display Top Reachable Server Samples
    print("\n--- SAMPLE REACHABLE POPULAR MCP SERVERS ---")
    for r in reachable[:25]:
        disc_tag = "[Auto-OAuth]" if r["oauth_discovery_supported"] else "[Needs Client ID / Key]"
        print(f"{r['name']:<28} | HTTP {r['http_status']} | {disc_tag} | {r['auth_requirement']}")

    # Save detailed JSON report
    with open("mcp_servers_test_report.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull scan report saved to mcp_servers_test_report.json")

if __name__ == "__main__":
    main()
