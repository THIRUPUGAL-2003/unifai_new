import re
import pathlib
from datetime import datetime

root = pathlib.Path(__file__).resolve().parents[1]
files = [
    "release/UnifAI_Guard_Setup.exe",
    "installer/staging/UnifAI_Guard.exe",
]
patterns = [
    b"unifai.dev-yp.com",
    b"unifaiv2.dev-yp.com",
    b"8081",
    b"8082",
    b"browser_ai_proxy",
]

for rel in files:
    p = root / rel
    if not p.exists():
        print(f"MISSING {rel}")
        continue
    data = p.read_bytes()
    ts = datetime.fromtimestamp(p.stat().st_mtime)
    print(f"=== {rel} ({p.stat().st_size / 1024 / 1024:.1f} MB, built {ts}) ===")
    for pat in patterns:
        label = pat.decode(errors="ignore")
        print(f"  {label}: {'YES' if pat in data else 'no'}")
    urls = sorted(set(re.findall(rb"https?://[a-zA-Z0-9._/-]+", data)))
    for u in urls:
        if b"dev-yp" in u or b"unifai" in u or b"localhost" in u:
            print(f"  URL: {u.decode(errors='ignore')}")
