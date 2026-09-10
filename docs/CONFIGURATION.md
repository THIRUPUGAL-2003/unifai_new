# UnifAI Configuration Guide

This guide explains UnifAI settings — **what each one means** and what you should put.

Main file: `.env` (copy from `.env.example`).

```
cp .env.example .env
```

Never put real passwords in Git. Keep secrets only in `.env` on the server.

---

## 1. What is configuration?

| Item | Meaning |
|------|---------|
| `.env` | Master settings for your company UnifAI server |
| `configs/config.json` | App settings (MCP catalog path, etc.) |
| `configs/mcp-library.json` | List of MCP servers shown in the UI |
| `data/` | Runtime files UnifAI creates while running |

You usually only edit **`.env`**. Other files stay as shipped unless support tells you to change them.

---

## 2. Website and ports — what they mean

| Setting | What it means | Example |
|---------|---------------|---------|
| `SERVER_DOMAIN` | Public web address users open for UnifAI | `https://unifai.yourcompany.com` |
| `APP_PORT` | Port UnifAI listens on inside the server | `8081` |
| `APP_HOST` | Network bind. `0.0.0.0` = allow outside connections | `0.0.0.0` |
| `PROXY_PORT` | Port for optional office network Guard proxy | `8082` |

**Simple rule:** `SERVER_DOMAIN` must be the HTTPS URL people type in the browser. That URL must reach port `8081`.

---

## 3. Database — what they mean

| Setting | What it means | Example |
|---------|---------------|---------|
| `DB_TYPE` | Which database engine you use | `postgres` (recommended) |
| `DB_HOST` | Where the database computer is | `db.yourcompany.com` |
| `DB_PORT` | Port number of the database | `5432` |
| `DB_NAME` | Name of the UnifAI database | `unifai` |
| `DB_USER` | Database login username | `unifai` |
| `DB_PASSWORD` | Database login password | *(secret)* |
| `DB_SSL_MODE` | Encrypt connection to database? | `disable` or `require` |

**Simple rule:** Create an empty database first. UnifAI fills tables when it starts.

Other allowed `DB_TYPE` values: `mysql`, `mariadb`, `sqlite`.

---

## 4. Admin login — what they mean

| Setting | What it means | Example |
|---------|---------------|---------|
| `ADMIN_EMAIL` | First administrator email (first login) | `admin@yourcompany.com` |
| `ADMIN_PASSWORD` | First administrator password | *(strong password)* |

**Simple rule:** After first login, change this password in the product if your process requires it.

---

## 5. AI helper (Ollama) — what it means

| Setting | What it means | Example |
|---------|---------------|---------|
| `OLLAMA_URL` | Address of your Ollama / local LLM service (Guard Bot) | `http://host.docker.internal:11434` |

**Simple rule:** If you do not use Guard Bot / Ollama yet, still set a valid URL or leave your engineer’s value. UnifAI maps this to `BROWSER_AI_OLLAMA_URL` inside Docker.

---

## 6. Logs — what they mean

| Setting | What it means | Suggested value |
|---------|---------------|-----------------|
| `LOG_LEVEL` | How much detail in logs: `debug`, `info`, `warn`, `error` | `info` |
| `LOG_STYLE` | Log format: `json` (production) or `console` (dev) | `json` |
| `APP_DIR` | Folder inside container for runtime data | `/app/data` |

---

## 7. MCP catalog — what it means

| Setting / file | What it means |
|----------------|---------------|
| `configs/mcp-library.json` | Catalog of MCP servers shown in MCP Library |
| `mcp_library_url` in `configs/config.json` | Where UnifAI loads that catalog from |

Correct value:

```
file:///app/configs/mcp-library.json
```

**Simple rule:** Do not use old remote URLs that no longer work. After change, open MCP Library in UI and run **Force Sync**.

---

## 8. Optional — network Guard proxy

Only if you use the shared office proxy container:

| Setting | What it means |
|---------|---------------|
| `PROXY_PORT` | Port browsers use for the shared proxy (default `8082`) |
| Compose service `unifai_broswer_proxy` | The shared network Guard process |

Laptop Guard on each PC uses its own local settings (`backend_url`, local port `8085`) — that is separate from this `.env` file. See the Windows Guard guide.

---

## 9. After you change settings

1. Save `.env`  
2. Restart UnifAI:

```
docker compose up -d --force-recreate zen_gauss_v1
```

3. Check:

| Check | Meaning of success |
|-------|--------------------|
| Open `SERVER_DOMAIN/health` | Server is up |
| Login with admin email/password | Admin settings are correct |
| Database errors gone in logs | Database settings are correct |

---

## Quick map

| Group | Settings |
|-------|----------|
| Website | `SERVER_DOMAIN`, `APP_PORT`, `APP_HOST` |
| Database | `DB_TYPE`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_SSL_MODE` |
| Admin | `ADMIN_EMAIL`, `ADMIN_PASSWORD` |
| AI helper | `OLLAMA_URL` |
| Logs | `LOG_LEVEL`, `LOG_STYLE`, `APP_DIR` |
| Optional proxy | `PROXY_PORT` |

That is the configuration you need to understand for hosting UnifAI.
