#!/usr/bin/env python3
"""
Syncs backend_url in Browser Guard configuration files and READMEs with SERVER_DOMAIN from the repository root .env file.

Usage:
    python apps/browser-guard/scripts/sync_config_from_env.py
    or (from apps/browser-guard directory):
    python scripts/sync_config_from_env.py
"""

from __future__ import annotations

import json
import os
import re
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_repo_root() -> str:
    """Locate the repo root containing .env or .git."""
    start = os.path.abspath(os.path.dirname(__file__))
    current = start
    for _ in range(5):
        if os.path.exists(os.path.join(current, ".env")) or os.path.exists(os.path.join(current, "docker-compose.yml")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return os.path.abspath(os.path.join(start, "..", ".."))


def read_server_domain(repo_root: str) -> str:
    """Extract SERVER_DOMAIN from .env or environment variable."""
    env_domain = os.environ.get("SERVER_DOMAIN", "").strip()
    if env_domain:
        return env_domain

    env_path = os.path.join(repo_root, ".env")
    if not os.path.isfile(env_path):
        env_example = os.path.join(repo_root, ".env.example")
        if os.path.isfile(env_example):
            env_path = env_example
        else:
            return ""

    try:
        with open(env_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "SERVER_DOMAIN":
                        clean_val = v.strip().strip("'\"")
                        if clean_val:
                            return clean_val
    except Exception as e:
        print(f"[sync_config_from_env] Error reading .env: {e}", file=sys.stderr)

    return ""


def update_json_config(path: str, server_domain: str, repo_root: str) -> bool:
    """Update backend_url in a unifai_guard_config.json file."""
    if not os.path.isfile(path):
        return False
    rel_path = os.path.relpath(path, repo_root).replace("\\", "/")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return False

        old_url = data.get("backend_url", "")
        data["backend_url"] = server_domain
        data["_comment"] = "Generated from .env — run sync_config_from_env.py after changing SERVER_DOMAIN"

        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        print(f"[sync_config_from_env] Updated {rel_path}: {old_url} -> {server_domain}")
        return True
    except Exception as e:
        print(f"[sync_config_from_env] Failed updating {rel_path}: {e}", file=sys.stderr)
        return False


def update_readme(path: str, server_domain: str, repo_root: str) -> bool:
    """Update 'Company server: ...' line in a README text file."""
    if not os.path.isfile(path):
        return False
    rel_path = os.path.relpath(path, repo_root).replace("\\", "/")
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        new_content = re.sub(
            r"Company server:\s*https?://[^\s\n]+",
            f"Company server: {server_domain}",
            content,
        )

        if new_content != content:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new_content)
            print(f"[sync_config_from_env] Updated {rel_path} company server URL.")
            return True
        return False
    except Exception as e:
        print(f"[sync_config_from_env] Failed updating {rel_path}: {e}", file=sys.stderr)
        return False


def main() -> int:
    repo_root = find_repo_root()
    server_domain = read_server_domain(repo_root)

    if not server_domain:
        print(
            "[sync_config_from_env ERROR] SERVER_DOMAIN is not set in .env and not found in environment!",
            file=sys.stderr,
        )
        return 1

    print(f"[sync_config_from_env] Target SERVER_DOMAIN from .env: {server_domain}")

    bg_dir = os.path.join(repo_root, "apps", "browser-guard")

    config_files = [
        os.path.join(bg_dir, "config", "unifai_guard_config.json"),
        os.path.join(bg_dir, "release", "unifai_guard_config.json"),
        os.path.join(bg_dir, "installer", "staging", "unifai_guard_config.json"),
    ]

    readme_files = [
        os.path.join(bg_dir, "release", "EMPLOYEE_README.txt"),
        os.path.join(bg_dir, "release", "EMPLOYEE_README_MAC.txt"),
        os.path.join(bg_dir, "installer", "staging", "EMPLOYEE_README.txt"),
        os.path.join(bg_dir, "installer", "staging", "EMPLOYEE_README_MAC.txt"),
    ]

    updated = 0
    for cfg in config_files:
        if update_json_config(cfg, server_domain, repo_root):
            updated += 1

    for rd in readme_files:
        if update_readme(rd, server_domain, repo_root):
            updated += 1

    print(f"[sync_config_from_env] Successfully verified/synced {updated} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
