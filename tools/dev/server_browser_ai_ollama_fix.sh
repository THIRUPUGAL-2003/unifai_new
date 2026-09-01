#!/bin/sh
# Wire AI Guard Bot → Ollama on srv1405395 (same host as unifaiv2.dev-yp.com).
# Run on the server as root:  sh tools/dev/server_browser_ai_ollama_fix.sh
set -e

OLLAMA_URL="${BROWSER_AI_OLLAMA_URL:-http://127.0.0.1:11434}"

echo "=== 1) Ollama health (host) ==="
if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null; then
  echo "FAIL: Ollama not reachable at ${OLLAMA_URL}"
  echo "      Fix 1Panel Ollama app first, then re-run."
  exit 1
fi
echo "OK: Ollama at ${OLLAMA_URL}"

echo ""
echo "=== 2) Find UnifAI backend container ==="
CID=""
for name in zen_gauss_v1 unifai unifai-api UnifAI; do
  cid="$(docker ps -q -f "name=${name}" 2>/dev/null | head -1)"
  if [ -n "$cid" ]; then
    CID="$cid"
    CNAME="$(docker inspect -f '{{.Name}}' "$CID" | sed 's#^/##')"
    echo "Found: $CNAME ($CID)"
    break
  fi
done

if [ -z "$CID" ]; then
  echo "WARN: No known UnifAI container. Listing candidates:"
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}' | grep -E '8081|unifai|zen_gauss' || docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}'
  echo ""
  echo "Set UNIFAI_CONTAINER=<name> and re-run, or add BROWSER_AI_OLLAMA_URL in 1Panel UnifAI app env:"
  echo "  BROWSER_AI_OLLAMA_URL=${OLLAMA_URL}"
  exit 1
fi

if [ -n "${UNIFAI_CONTAINER:-}" ]; then
  CID="$(docker ps -q -f "name=${UNIFAI_CONTAINER}" | head -1)"
  CNAME="${UNIFAI_CONTAINER}"
fi

echo ""
echo "=== 3) Test Ollama from inside backend container ==="
# From Docker, 127.0.0.1 is the container itself — use host IP or host.docker.internal.
DOCKER_OLLAMA="${BROWSER_AI_OLLAMA_URL:-http://host.docker.internal:11434}"
if docker exec "$CID" wget -q -O - "${DOCKER_OLLAMA}/api/tags" 2>/dev/null | head -c 120; then
  echo ""
  echo "OK: container can reach Ollama at ${DOCKER_OLLAMA}"
  OLLAMA_FOR_CONTAINER="$DOCKER_OLLAMA"
else
  PUB="http://76.13.243.253:11434"
  if docker exec "$CID" wget -q -O - "${PUB}/api/tags" 2>/dev/null | head -c 120; then
    echo ""
    echo "OK: container can reach Ollama at ${PUB}"
    OLLAMA_FOR_CONTAINER="$PUB"
  else
    echo "FAIL: backend container cannot reach Ollama."
    echo "Add to UnifAI docker-compose / 1Panel env:"
    echo "  BROWSER_AI_OLLAMA_URL=http://host.docker.internal:11434"
    echo "  extra_hosts: host.docker.internal:host-gateway"
    exit 1
  fi
fi

echo ""
echo "=== 4) Set env + restart backend ==="
ENV_FILE="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/app/data"}}{{.Source}}{{end}}{{end}}' "$CID" 2>/dev/null || true)"
COMPOSE_DIR=""
# 1Panel apps often live under /opt/1panel/apps/
for d in /opt/1panel/apps/unifai/unifai /opt/1panel/apps/zen_gauss/zen_gauss "$(dirname "$0")/../.."; do
  if [ -f "$d/docker-compose.yml" ]; then
    COMPOSE_DIR="$d"
    break
  fi
done

if [ -n "$COMPOSE_DIR" ] && [ -f "$COMPOSE_DIR/.env" ]; then
  echo "Patching $COMPOSE_DIR/.env"
  if grep -q '^BROWSER_AI_OLLAMA_URL=' "$COMPOSE_DIR/.env" 2>/dev/null; then
    sed -i "s|^BROWSER_AI_OLLAMA_URL=.*|BROWSER_AI_OLLAMA_URL=${OLLAMA_FOR_CONTAINER}|" "$COMPOSE_DIR/.env"
  else
    echo "BROWSER_AI_OLLAMA_URL=${OLLAMA_FOR_CONTAINER}" >>"$COMPOSE_DIR/.env"
  fi
  (cd "$COMPOSE_DIR" && docker compose up -d --force-recreate)
  echo "Restarted via docker compose in $COMPOSE_DIR"
else
  echo "No compose .env found — recreate container with env (manual 1Panel step):"
  echo "  BROWSER_AI_OLLAMA_URL=${OLLAMA_FOR_CONTAINER}"
  docker restart "$CID"
  echo "Restarted $CNAME (env must be set in 1Panel for persistent fix)."
fi

sleep 4
echo ""
echo "=== 5) Backend health ==="
if docker exec "$CID" wget -q -O /dev/null http://127.0.0.1:8081/health 2>/dev/null; then
  echo "OK: UnifAI healthy on :8081"
else
  echo "WARN: health check failed — docker logs $CNAME --tail 30"
fi

echo ""
echo "Done. Test in dashboard: Browser AI → Rules → AI Guard Bot → Test"
