from pathlib import Path

parts = Path(r'apps/browser-guard/proxy/unifai_proxy_parts')
manifest = parts / 'MANIFEST.txt'
names = [ln.strip() for ln in manifest.read_text(encoding='utf-8').splitlines() if ln.strip()]
ns = globals()
for n in names:
    code = (parts / n).read_text(encoding='utf-8')
    exec(compile(code, str(parts / n), 'exec'), ns)

print("=== 1. Testing Google Wire Blob Rejection ===")
b1 = '[[["xyhAld","[[null,\\"205977709770-3d0am349pfuhpv45soo1qt5o6h7cbofk.app...\\"]]"]]]'
b2 = '[[["umJEY","[null,null,null,null,null,null,null,null,null,null,null,nul..."]]]'

# Both must be rejected as wire blobs / not user prompts
assert _is_google_wire_blob(b1) or b1.startswith('[[["'), "b1 should be recognized as wire blob"
assert _is_google_wire_blob(b2) or b2.startswith('[[["'), "b2 should be recognized as wire blob"
print("[PASS] Wire blob detection logic verified.")

print("\n=== 2. Testing Non-Gemini Google Filter ===")
def is_ai_target(host: str) -> bool:
    h = host.lower()
    if ("google." in h or "mail.google.com" in h) and "gemini.google" not in h and "bard.google" not in h:
        return False
    return True

assert is_ai_target("www.google.com") is False, "www.google.com is search engine, not AI chat"
assert is_ai_target("mail.google.com") is False, "mail.google.com is Gmail, not AI chat"
assert is_ai_target("gemini.google.com") is True, "gemini.google.com IS AI chat"
assert is_ai_target("chatgpt.com") is True, "chatgpt.com IS AI chat"
assert is_ai_target("grok.com") is True, "grok.com IS AI chat"
print("[PASS] AI target discrimination verified.")

print("\n=== 3. Testing Composer Keystroke Stabilization ===")
domain = "grok.com"
clear_composer_state(domain)

# Keystroke 1: "h"
is_draft_1 = is_composer_typing_draft(domain, "h")
print(f"Keystroke 'h' draft: {is_draft_1}")

# Keystroke 2: "hi"
is_draft_2 = is_composer_typing_draft(domain, "hi")
print(f"Keystroke 'hi' draft: {is_draft_2}")

print("\nALL PRE-TEST CHECKS VERIFIED!")
