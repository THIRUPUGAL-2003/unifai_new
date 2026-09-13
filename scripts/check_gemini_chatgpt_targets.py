#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
import http.cookiejar
from collections import Counter
from pathlib import Path

env = {}
for line in Path(r"c:\Users\sakth\OneDrive\ドキュメント\Desktop\unify - Copy\.env").read_text(encoding="utf-8").splitlines():
	line = line.strip()
	if not line or line.startswith("#") or "=" not in line:
		continue
	k, v = line.split("=", 1)
	env[k.strip()] = v.strip()

base = env["SERVER_DOMAIN"].rstrip("/")
password = env["ADMIN_PASSWORD"]
username = env.get("ADMIN_EMAIL") or "admin@yespanchi.com"
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def req(method, path, data=None, token=None):
	body = None if data is None else json.dumps(data).encode()
	r = urllib.request.Request(base + path, data=body, method=method)
	r.add_header("Content-Type", "application/json")
	r.add_header("Accept", "application/json")
	if token:
		r.add_header("Authorization", "Bearer " + token)
	try:
		with opener.open(r, timeout=60) as resp:
			raw = resp.read().decode()
			return resp.status, json.loads(raw) if raw else {}
	except urllib.error.HTTPError as e:
		raw = e.read().decode()
		try:
			j = json.loads(raw)
		except Exception:
			j = {"raw": raw[:400]}
		return e.code, j


code, j = req("POST", "/api/session/login", {"username": username, "password": password})
token = j.get("token")
for c in cj:
	if c.name == "token":
		token = token or c.value

code, j = req("GET", "/api/browser-ai/targets", token=token)
targets = j.get("targets") or []
print("targets", len(targets))
for t in sorted(targets, key=lambda x: x.get("domain") or ""):
	d = t.get("domain") or ""
	if any(x in d for x in ("gemini", "google", "chatgpt", "openai", "oai", "perplexity", "pplx")):
		print(
			f"{d:40} mon={t.get('monitored')} role={(t.get('host_role') or '-'):5} "
			f"plat={t.get('platform_name')} hits={t.get('intercepted_count')} parent={bool(t.get('parent_id'))}"
		)

code, j = req("GET", "/api/browser-ai/logs?limit=30", token=token)
logs = j.get("logs") or []
print("logs_sample", len(logs), "total", j.get("total"))
plats = Counter((l.get("platform") or l.get("platform_name") or "?") for l in logs)
print("platforms", dict(plats))
for l in logs[:8]:
	print(
		"-",
		(l.get("platform") or l.get("platform_name")),
		(l.get("action") or l.get("status")),
		(l.get("domain") or "")[:40],
		repr((l.get("prompt") or l.get("user_prompt") or "")[:50]),
	)
