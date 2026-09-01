#!/usr/bin/env bash
# Rebuild UnifAI Docker image and fix common config.json save errors.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"

echo "==> Ensuring data/config.json exists"
mkdir -p data
if [ ! -f data/config.json ] && [ -f configs/config.json ]; then
	cp configs/config.json data/config.json
	echo "    Copied configs/config.json -> data/config.json"
fi

if [ -f "$COMPOSE_FILE" ]; then
	if grep -q 'configs/config.json:/app/data/config.json' "$COMPOSE_FILE"; then
		echo "==> Removing conflicting config.json file bind mount from $COMPOSE_FILE"
		sed -i '/configs\/config.json:\/app\/data\/config.json/d' "$COMPOSE_FILE"
	fi
fi

echo "==> Stopping containers"
docker compose down

echo "==> Building image (no cache)"
docker build --no-cache -f transports/Dockerfile.local -t unifai-local .

echo "==> Starting containers"
docker compose up -d

echo "==> Done. Guardrails save should persist to data/config.json now."
