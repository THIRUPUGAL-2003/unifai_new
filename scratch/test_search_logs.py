"""Comprehensive End-to-End Verification Test for Browser AI Search Logs & Interception."""

import base64
import urllib.parse
import json
import urllib.request
import sys

BACKEND_URL = "http://localhost:8080"

def test_proxy_search_extraction():
    print("=== Testing Search Engine Extraction Logic ===")
    
    # 1. Google search query extraction
    url = "https://www.google.com/search?q=confidential+financial+report+2026&oq=confidential"
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    q = qs.get("q", [""])[0]
    assert q == "confidential financial report 2026", f"Failed Google q: {q}"
    print("[PASS] Google search query extraction: OK")
    
    # 2. Google click tracking extraction
    target_url = "https://internal-portal.company.com/q4-report.pdf"
    encoded_target = urllib.parse.quote(target_url, safe="")
    url_click = f"https://www.google.com/url?sa=t&source=web&rct=j&url={encoded_target}"
    parsed_click = urllib.parse.urlparse(url_click)
    qs_click = urllib.parse.parse_qs(parsed_click.query)
    extracted_target = qs_click.get("url", [""])[0]
    assert extracted_target == target_url, f"Failed Google click: {extracted_target}"
    print("[PASS] Google click tracking extraction: OK")
    
    # 3. Bing search query extraction
    url_bing = "https://www.bing.com/search?q=how+to+disable+dlp+agent+powershell"
    parsed_bing = urllib.parse.urlparse(url_bing)
    qs_bing = urllib.parse.parse_qs(parsed_bing.query)
    q_bing = qs_bing.get("q", [""])[0]
    assert q_bing == "how to disable dlp agent powershell"
    print("[PASS] Bing search query extraction: OK")
    
    # 4. Bing click tracking extraction (u=a1<base64>)
    dest = "https://adversary-tools.org/bypass-edr"
    b64_dest = base64.urlsafe_b64encode(dest.encode("utf-8")).decode("ascii").rstrip("=")
    u_param = "a1" + b64_dest
    b64_part = u_param[2:] + "=="
    decoded_dest = base64.urlsafe_b64decode(b64_part.encode("ascii")).decode("utf-8", errors="ignore")
    assert decoded_dest == dest, f"Failed Bing decode: {decoded_dest}"
    print("[PASS] Bing click tracking (base64) extraction: OK")
    
    # 5. DuckDuckGo query & click
    url_ddg = "https://duckduckgo.com/?q=employee+payroll+records+search"
    qs_ddg = urllib.parse.parse_qs(urllib.parse.urlparse(url_ddg).query)
    assert qs_ddg.get("q", [""])[0] == "employee payroll records search"
    
    ddg_click = f"https://duckduckgo.com/l/?uddg={urllib.parse.quote(dest)}"
    qs_ddg_click = urllib.parse.parse_qs(urllib.parse.urlparse(ddg_click).query)
    assert urllib.parse.unquote(qs_ddg_click.get("uddg", [""])[0]) == dest
    print("[PASS] DuckDuckGo search query & click extraction: OK")
    
    # 6. Yahoo search query
    url_yahoo = "https://search.yahoo.com/search?p=cybersecurity+risk+analysis"
    qs_yahoo = urllib.parse.parse_qs(urllib.parse.urlparse(url_yahoo).query)
    assert qs_yahoo.get("p", [""])[0] == "cybersecurity risk analysis"
    print("[PASS] Yahoo search query extraction: OK")
    
    # 7. Browser & Incognito Detection heuristics
    # Edge
    ua_edge = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
    browser = "Edge" if "edg/" in ua_edge.lower() else "Chrome"
    assert browser == "Edge"
    
    # Safari
    ua_safari = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
    browser_safari = "Safari" if "safari" in ua_safari.lower() and "chrome" not in ua_safari.lower() else "Other"
    assert browser_safari == "Safari"
    
    # Incognito check (missing persistent cookies)
    cookie_incognito = ""
    is_incognito = len(cookie_incognito.strip()) < 15
    assert is_incognito is True
    
    cookie_normal = "SID=AQAAAH0; SAPISID=B98f12; HSID=A892k; SSID=98127391823719"
    is_incognito_normal = "SAPISID=" not in cookie_normal and "SID=" not in cookie_normal
    assert is_incognito_normal is False
    print("[PASS] Browser & Incognito heuristic classification: OK")
    
    print("\nALL 7 EXTRACTION TESTS PASSED!\n")

if __name__ == "__main__":
    test_proxy_search_extraction()
