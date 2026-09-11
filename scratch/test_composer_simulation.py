from pathlib import Path
import threading
import time

parts = Path(r'apps/browser-guard/proxy/unifai_proxy_parts')
manifest = parts / 'MANIFEST.txt'
names = [ln.strip() for ln in manifest.read_text(encoding='utf-8').splitlines() if ln.strip()]
ns = globals()
for n in names:
    code = (parts / n).read_text(encoding='utf-8')
    exec(compile(code, str(parts / n), 'exec'), ns)

domain = "grok.com"
clear_composer_state(domain)

results = []
results_lock = threading.Lock()

def send_prompt(text: str, delay: float):
    time.sleep(delay)
    if is_composer_typing_draft(domain, text):
        return
    stable = wait_if_composer_unstable(domain, text)
    if stable:
        # In real proxy: is_duplicate_event deduplicates
        if not is_duplicate_event(domain, stable, ttl=3):
            mark_duplicate_event(domain, stable)
            with results_lock:
                results.append(stable)

# Simulate typing "h", "hi", "hi how are you" in Grok
t1 = threading.Thread(target=send_prompt, args=("h", 0.0))
t2 = threading.Thread(target=send_prompt, args=("hi", 0.15))
t3 = threading.Thread(target=send_prompt, args=("hi how are you", 0.35))

t1.start()
t2.start()
t3.start()

t1.join()
t2.join()
t3.join()

time.sleep(0.5)
print("\nFINAL COMMITTED RESULTS:", results)
assert results == ["hi how are you"], f"Expected only ['hi how are you'] but got {results}"
print("TEST PASSED 100% PERFECTLY!")
