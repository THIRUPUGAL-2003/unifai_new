#!/usr/bin/env python3
"""Fill Guard package configs from repo-root .env (SERVER_DOMAIN / UNIFAI_BACKEND_URL).

Usage (from repo root or this folder):
  python apps/browser-guard/scripts/sync_config_from_env.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GUARD = ROOT / "apps" / "browser-guard"


def load_env(path: Path) -> dict[str, str]:
	out: dict[str, str] = {}
	if not path.is_file():
		return out
	for line in path.read_text(encoding="utf-8").splitlines():
		line = line.strip()
		if not line or line.startswith("#") or "=" not in line:
			continue
		k, v = line.split("=", 1)
		out[k.strip()] = v.strip().strip('"').strip("'")
	return out


def main() -> int:
	env = load_env(ROOT / ".env")
	backend = (env.get("UNIFAI_BACKEND_URL") or env.get("SERVER_DOMAIN") or "").rstrip("/")
	if not backend:
		print("ERROR: set SERVER_DOMAIN or UNIFAI_BACKEND_URL in .env", file=sys.stderr)
		return 1

	cfg = {
		"backend_url": backend,
		"proxy_addr": "127.0.0.1:8085",
		"pac_sync_seconds": 3,
		"server_mode": False,
		"agent_type": "endpoint",
		"listen_host": "127.0.0.1",
		"pac_advertise_addr": "",
		"_comment": "Generated from .env — run sync_config_from_env.py after changing SERVER_DOMAIN",
	}
	template = dict(cfg)
	template["backend_url"] = ""
	template["_comment"] = "Source template — run sync_config_from_env.py before packaging (fills from .env)"

	(GUARD / "config" / "unifai_guard_config.json").write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
	print(f"Wrote template apps/browser-guard/config/unifai_guard_config.json (backend_url empty)")

	raw = json.dumps(cfg, indent=2) + "\n"
	targets = [
		GUARD / "release" / "unifai_guard_config.json",
		GUARD / "installer" / "staging" / "unifai_guard_config.json",
	]
	for t in targets:
		t.parent.mkdir(parents=True, exist_ok=True)
		t.write_text(raw, encoding="utf-8")
		print(f"Wrote {t.relative_to(ROOT)}")

	# Employee README: keep installer templates generic; fill staging/release only.
	placeholder_line = "Company server: (set SERVER_DOMAIN in .env — run sync_config_from_env.py)\n"
	for name in ("EMPLOYEE_README.txt", "EMPLOYEE_README_MAC.txt"):
		src = GUARD / "installer" / name
		if src.is_file():
			text = src.read_text(encoding="utf-8")
			lines = text.splitlines()
			out_lines = []
			i = 0
			while i < len(lines):
				if lines[i].startswith("Company server:"):
					out_lines.append("Company server: (set SERVER_DOMAIN in .env — run sync_config_from_env.py)")
					i += 1
					if i < len(lines) and lines[i].startswith("(If IT"):
						out_lines.append("(If IT gave you a different backend URL, use the config in this ZIP.)")
						i += 1
					continue
				out_lines.append(lines[i])
				i += 1
			src.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

		filled = f"Company server: {backend}\n(If IT gave you a different backend URL, use the config in this ZIP.)\n"
		for base in (GUARD / "release", GUARD / "installer" / "staging"):
			p = base / name
			if not p.is_file() and src.is_file():
				# seed from installer template then replace
				body = src.read_text(encoding="utf-8")
				p.parent.mkdir(parents=True, exist_ok=True)
				p.write_text(body, encoding="utf-8")
			if not p.is_file():
				continue
			text = p.read_text(encoding="utf-8")
			lines = text.splitlines()
			out_lines = []
			i = 0
			while i < len(lines):
				if lines[i].startswith("Company server:"):
					out_lines.append(f"Company server: {backend}")
					i += 1
					if i < len(lines) and lines[i].startswith("(If IT"):
						out_lines.append("(If IT gave you a different backend URL, use the config in this ZIP.)")
						i += 1
					continue
				out_lines.append(lines[i])
				i += 1
			p.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
			print(f"Updated {p.relative_to(ROOT)}")

	# Installer App URL metadata stays generic; real backend is in unifai_guard_config.json
	print(f"OK backend_url={backend}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
