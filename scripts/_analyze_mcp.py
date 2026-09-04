#!/usr/bin/env python3
"""Analyze mcp-library.json for likely broken auth / missing icons."""
import json
import re
from pathlib import Path
from urllib.parse import urlparse

data = json.loads(Path("configs/mcp-library.json").read_text(encoding="utf-8"))
servers = data["servers"]

supabase_none = []
auth_none_http = 0
missing_url = []
stdio = 0
http = 0
has_icon = 0

for s in servers:
    if s.get("icon_url"):
        has_icon += 1
    ct = s.get("connection_type")
    if ct == "stdio":
        stdio += 1
    else:
        http += 1
    url = s.get("connection_url") or ""
    auth = (s.get("auth_type") or "none").lower()
    if not url and ct != "stdio":
        missing_url.append(s.get("name"))
    if auth == "none" and ct != "stdio":
        auth_none_http += 1
    if "supabase.co" in url and auth == "none":
        supabase_none.append({"name": s.get("name"), "url": url})

print(f"total={len(servers)} http={http} stdio={stdio} with_icon_url={has_icon}")
print(f"http+auth_none={auth_none_http}")
print(f"supabase+auth_none={len(supabase_none)}")
for x in supabase_none[:20]:
    print(f"  - {x['name']}: {x['url']}")
print(f"missing_url={missing_url[:10]}")
