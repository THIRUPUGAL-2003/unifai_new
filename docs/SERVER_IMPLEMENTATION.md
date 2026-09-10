# UnifAI Server Hosting Guide

This guide shows how to put UnifAI on your server and check that it works.

---

## Before you start

You need these ready:

| You need | Meaning |
|----------|---------|
| A server with Docker | Docker and Docker Compose installed |
| A PostgreSQL database | Empty database + username + password |
| A website address (HTTPS) | Example: `https://unifai.yourcompany.com` |
| This UnifAI project folder | On the server |

Your website address must send traffic to port **8081** on that server.

---

## Step 1 — Create settings

Run these in the project folder:

```
mkdir -p data
cp .env.example .env
```

Open the `.env` file and set these values:

| Setting | What to type | Example |
|---------|--------------|---------|
| `SERVER_DOMAIN` | Your public UnifAI URL | `https://unifai.yourcompany.com` |
| `APP_PORT` | Keep as | `8081` |
| `APP_HOST` | Keep as | `0.0.0.0` |
| `DB_TYPE` | Keep as | `postgres` |
| `DB_HOST` | Database server address | `db.yourcompany.com` |
| `DB_PORT` | Database port | `5432` |
| `DB_NAME` | Database name | `unifai` |
| `DB_USER` | Database user | `unifai` |
| `DB_PASSWORD` | Database password | *(your secret)* |
| `DB_SSL_MODE` | Usually | `disable` |
| `ADMIN_EMAIL` | First login email | `admin@yourcompany.com` |
| `ADMIN_PASSWORD` | First login password | *(strong password)* |
| `OLLAMA_URL` | Local AI helper URL (if used) | `http://host.docker.internal:11434` |
| `LOG_LEVEL` | Keep as | `info` |
| `LOG_STYLE` | Keep as | `json` |
| `APP_DIR` | Keep as | `/app/data` |

Also check:

| File | Must be true |
|------|----------------|
| `configs/mcp-library.json` | File exists |
| `configs/config.json` | Contains `mcp_library_url` = `file:///app/configs/mcp-library.json` |

If Docker Compose mentions `1panel-network`, run this once:

```
docker network create 1panel-network
```

(Or ask your engineer to remove that network line from `docker-compose.yml`.)

---

## Step 2 — Build and start UnifAI

```
docker build -f deploy/docker/Dockerfile.local -t unifai-local:latest .
docker compose up -d zen_gauss_v1
```

Wait about 1–2 minutes for the first start.

---

## Step 3 — Check it works

Replace `your-domain` with your real `SERVER_DOMAIN`.

| Do this | You should see |
|---------|----------------|
| Open `https://your-domain/health` | OK status in JSON |
| Open `https://your-domain` | UnifAI login page |
| Login with `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Dashboard opens |
| Open `https://your-domain/api/browser-ai/targets` | JSON data (not a login HTML page) |

Useful commands:

```
docker compose ps
docker compose logs -f zen_gauss_v1
```

---

## Step 4 — HTTPS (important)

| Point | Detail |
|-------|--------|
| UnifAI listens on | Port `8081` |
| Your job | Put SSL (HTTPS) in front with reverse proxy / 1Panel / load balancer |
| `SERVER_DOMAIN` | Must match the public HTTPS address users open |

---

## Step 5 — Stop or restart

Stop UnifAI:

```
docker compose stop zen_gauss_v1
```

Or remove containers (files stay):

```
docker compose down
```

After you change `.env`, restart like this:

```
docker compose up -d --force-recreate zen_gauss_v1
```

Note: this does **not** delete your PostgreSQL database.

---

## Optional — office network Guard proxy

Only if your company uses a shared network proxy (not laptop Guard):

```
docker compose up -d unifai_broswer_proxy
```

Default proxy port: `8082`.

---

## Quick summary

1. Fill `.env`  
2. Build and start  
3. Open `/health` and login  
4. Keep HTTPS in front of port 8081  

That is all for server hosting.
