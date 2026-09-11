from pathlib import Path

parts = Path(r'apps/browser-guard/proxy/unifai_proxy_parts')
manifest = parts / 'MANIFEST.txt'
names = [ln.strip() for ln in manifest.read_text(encoding='utf-8').splitlines() if ln.strip()]
ns = globals()
for n in names:
    code = (parts / n).read_text(encoding='utf-8')
    exec(compile(code, str(parts / n), 'exec'), ns)

sample = b'[[["xyhAld","[[null,\\"205977709770-3d0am349pfuhpv45soo1qt5o6h7cbofk.app...\\"]]"]]]'
res = extract_prompt_universal(sample, 'application/json', host='www.google.com')
print('RESULT FOR xyhAld:', repr(res))

sample2 = b'f.req=[[["k06x8e","[\\"deepseek\\",1]"]]]'
res2 = extract_prompt_universal(sample2, 'application/x-www-form-urlencoded', host='mail.google.com')
print('RESULT FOR Gmail deepseek:', repr(res2))

sample3 = b'f.req=[[["k06x8e","[\\"d\\",1]"]]]'
res3 = extract_prompt_universal(sample3, 'application/x-www-form-urlencoded', host='mail.google.com')
print('RESULT FOR Gmail d:', repr(res3))

sample_grok1 = b'{"message": "h"}'
res_grok1 = extract_prompt_universal(sample_grok1, 'application/json', host='grok.com')
print('RESULT FOR Grok h:', repr(res_grok1))

sample_grok2 = b'{"message": "hi"}'
res_grok2 = extract_prompt_universal(sample_grok2, 'application/json', host='grok.com')
print('RESULT FOR Grok hi:', repr(res_grok2))
