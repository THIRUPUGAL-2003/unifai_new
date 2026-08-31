#!/usr/bin/env python3
"""Generate data/mcp-library.json from the public MCP Registry."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REGISTRY_BASE = "https://registry.modelcontextprotocol.io/v0.1/servers"
TARGET_SERVERS = 150
PAGE_SIZE = 100


def clean_text(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    text = text.encode("utf-8", "ignore").decode("utf-8")
    return re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", " ", text).strip()


def slugify(name: str) -> str:
    out: list[str] = []
    prev_dash = False
    for ch in name.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash and out:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")


def display_name(server: dict) -> str:
    title = (server.get("title") or "").strip()
    if title:
        return title
    name = (server.get("name") or "").strip()
    if "/" in name:
        name = name.rsplit("/", 1)[-1]
    return name.replace("-", " ").replace("_", " ").strip().title() or name


def infer_category(server: dict) -> str:
    text = " ".join(
        filter(
            None,
            [
                server.get("name", ""),
                server.get("title", ""),
                server.get("description", ""),
            ],
        )
    ).lower()
    rules = [
        ("Developer Tools", ("github", "git", "gitlab", "code", "repo")),
        ("Data", ("postgres", "sql", "database", "sqlite", "redis", "snowflake")),
        ("Search", ("search", "brave", "google", "web", "fetch")),
        ("Communication", ("slack", "discord", "teams", "email", "mail")),
        ("Productivity", ("drive", "notion", "calendar", "filesystem", "file")),
        ("Automation", ("browser", "puppeteer", "playwright", "automation")),
        ("AI", ("llm", "memory", "agent", "inference", "model")),
    ]
    for category, keywords in rules:
        if any(keyword in text for keyword in keywords):
            return category
    return "General"


def env_keys(pkg: dict) -> list[str]:
    keys: list[str] = []
    for env in pkg.get("environmentVariables") or []:
        key = (env.get("name") or "").strip()
        if key:
            keys.append(key)
    return keys


def entry_from_package(server: dict, pkg: dict) -> dict | None:
    registry_type = (pkg.get("registryType") or "").lower()
    identifier = (pkg.get("identifier") or "").strip()
    if not identifier:
        return None

    transport = (pkg.get("transport") or {}).get("type", "stdio")
    envs = env_keys(pkg)
    name = display_name(server)

    if registry_type == "npm" and transport == "stdio":
        return {
            "name": name,
            "description": clean_text(server.get("description") or ""),
            "category": infer_category(server),
            "connection_type": "stdio",
            "stdio_config": {
                "command": "npx",
                "args": ["-y", identifier],
                **({"envs": envs} if envs else {}),
            },
            "auth_type": "headers" if envs else "none",
            **({"required_header_keys": envs} if envs else {}),
            "publisher": server.get("name", "").split("/")[0],
            "tags": [t for t in re.split(r"[^a-z0-9]+", server.get("name", "").lower()) if t][:5],
        }

    if registry_type == "pypi" and transport == "stdio":
        return {
            "name": name,
            "description": clean_text(server.get("description") or ""),
            "category": infer_category(server),
            "connection_type": "stdio",
            "stdio_config": {
                "command": "uvx",
                "args": [identifier],
                **({"envs": envs} if envs else {}),
            },
            "auth_type": "headers" if envs else "none",
            **({"required_header_keys": envs} if envs else {}),
            "publisher": server.get("name", "").split("/")[0],
        }

    return None


def entry_from_remote(server: dict, remote: dict) -> dict | None:
    remote_url = (remote.get("url") or "").strip()
    if not remote_url:
        return None
    remote_type = (remote.get("type") or "streamable-http").lower()
    connection_type = "sse" if "sse" in remote_type else "http"
    return {
        "name": display_name(server),
        "description": clean_text(server.get("description") or ""),
        "category": infer_category(server),
        "connection_type": connection_type,
        "connection_url": remote_url,
        "auth_type": "none",
        "publisher": server.get("name", "").split("/")[0],
    }


def fetch_registry_page(cursor: str | None = None) -> dict:
    query = urllib.parse.urlencode({"limit": PAGE_SIZE, **({"cursor": cursor} if cursor else {})})
    url = f"{REGISTRY_BASE}?{query}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def build_catalog() -> list[dict]:
    seen_slugs: set[str] = set()
    servers: list[dict] = []
    cursor: str | None = None

    while len(servers) < TARGET_SERVERS:
        payload = fetch_registry_page(cursor)
        batch = payload.get("servers") or []
        if not batch:
            break

        for item in batch:
            server = item.get("server") or {}
            name = display_name(server)
            slug = slugify(name)
            if not slug or slug in seen_slugs:
                continue

            entry = None
            for pkg in server.get("packages") or []:
                entry = entry_from_package(server, pkg)
                if entry:
                    break
            if entry is None:
                for remote in server.get("remotes") or []:
                    entry = entry_from_remote(server, remote)
                    if entry:
                        break
            if entry is None or not entry.get("name"):
                continue

            seen_slugs.add(slug)
            servers.append(entry)
            if len(servers) >= TARGET_SERVERS:
                break

        cursor = (payload.get("metadata") or {}).get("nextCursor")
        if not cursor:
            break
        time.sleep(0.2)

    return servers


def main() -> int:
    servers = build_catalog()
    if not servers:
        print("No MCP servers generated", file=sys.stderr)
        return 1

    output = {
        "lastUpdatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "servers": servers,
    }
    out_path = sys.argv[1] if len(sys.argv) > 1 else "data/mcp-library.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Wrote {len(servers)} servers to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
