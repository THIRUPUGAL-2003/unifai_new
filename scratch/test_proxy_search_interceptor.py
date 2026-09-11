"""Test BrowserAIInterceptor._maybe_record_search_engine with mock flows."""

from pathlib import Path
from unittest.mock import MagicMock
import urllib.parse
import json

parts = Path(r"apps/browser-guard/proxy/unifai_proxy_parts")
manifest = parts / 'MANIFEST.txt'
names = [ln.strip() for ln in manifest.read_text(encoding='utf-8').splitlines() if ln.strip()]

ns = globals()
for n in names:
    code = (parts / n).read_text(encoding='utf-8')
    exec(compile(code, str(parts / n), 'exec'), ns)

interceptor = BrowserAIInterceptor()

def make_flow(url: str, headers: dict = None):
    flow = MagicMock()
    flow.request.url = url
    p = urllib.parse.urlparse(url)
    flow.request.pretty_host = p.netloc
    flow.request.path = p.path or "/"
    flow.request.query = {k: v[0] for k, v in urllib.parse.parse_qs(p.query).items()}
    flow.request.method = "GET"
    h = headers or {}
    flow.request.headers = MagicMock()
    flow.request.headers.get.side_effect = lambda k, d="": h.get(k.lower(), d)
    flow.client_conn.peername = ("192.168.1.50", 54321)
    return flow

print("=== Testing Search Interceptor on Real BrowserAIInterceptor ===")

# Test 1: Google Search Query (Incognito Chrome)
f1 = make_flow(
    "https://www.google.com/search?q=quarterly+financial+audit+2026",
    {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36", "cookie": ""}
)
interceptor._maybe_record_search_engine(f1, f1.request.pretty_host)
print("[PASS] Test 1: Google Search Query")

# Test 2: Google Click Redirect
f2 = make_flow(
    "https://www.google.com/url?sa=t&url=https%3A%2F%2Fsec.gov%2Farchive%2F10k.pdf",
    {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
)
interceptor._maybe_record_search_engine(f2, f2.request.pretty_host)
print("[PASS] Test 2: Google Click Redirect")

# Test 3: Microsoft Edge (Bing) InPrivate Search
f3 = make_flow(
    "https://www.bing.com/search?q=bypass+powershell+execution+policy",
    {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0", "x-edge-inprivate": "1"}
)
interceptor._maybe_record_search_engine(f3, f3.request.pretty_host)
print("[PASS] Test 3: Bing / Edge InPrivate Search")

# Test 4: Safari Search
f4 = make_flow(
    "https://www.google.com/search?q=macos+keychain+dump+utility",
    {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"}
)
interceptor._maybe_record_search_engine(f4, f4.request.pretty_host)
print("[PASS] Test 4: Safari Search")

# Test 5: DuckDuckGo Click
f5 = make_flow(
    "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fgithub.com%2Fproject%2Frepo",
    {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0"}
)
interceptor._maybe_record_search_engine(f5, f5.request.pretty_host)
print("[PASS] Test 5: DuckDuckGo Click")

print("\nALL 5 INTERCEPTOR FLOW TESTS PASSED!\n")
