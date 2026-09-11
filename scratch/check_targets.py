import urllib.request
import json

try:
    req = urllib.request.urlopen("http://localhost:8080/api/browser-ai/targets", timeout=3)
    data = json.loads(req.read())
    print("TARGETS COUNT:", len(data.get("targets", [])))
    for t in data.get("targets", []):
        if any(w in t.get("domain", "") for w in ("google", "gmail", "grok", "x.ai", "x.com")):
            print(f"Domain: {t.get('domain')} | Platform: {t.get('platform_name')} | Monitored: {t.get('monitored')}")
except Exception as e:
    print("Error querying targets:", e)
