#!/bin/sh
# Connect zen_gauss_v1 → 1Panel Ollama on srv1405395. Run as root on the server.
set -e

OLLAMA_CONTAINER="1Panel-ollama-IjuM"
UNIFAI_CONTAINER="zen_gauss_v1"
NETWORK="1panel-network"
OLLAMA_URL="http://${OLLAMA_CONTAINER}:11434"

echo "=== 1) Ollama on host ==="
curl -sf http://127.0.0.1:11434/api/tags >/dev/null && echo "OK: host Ollama" || {
  echo "FAIL: start 1Panel Ollama first"
  exit 1
}

echo ""
echo "=== 2) Attach ${UNIFAI_CONTAINER} to ${NETWORK} ==="
docker network inspect "${NETWORK}" >/dev/null 2>&1 || {
  echo "FAIL: docker network ${NETWORK} not found"
  exit 1
}
docker network connect "${NETWORK}" "${UNIFAI_CONTAINER}" 2>/dev/null || echo "Already on ${NETWORK}"

echo ""
echo "=== 3) Test from UnifAI container ==="
if docker exec "${UNIFAI_CONTAINER}" wget -qO- "${OLLAMA_URL}/api/tags" | head -c 120; then
  echo ""
  echo "OK: ${UNIFAI_CONTAINER} → ${OLLAMA_URL}"
else
  echo ""
  echo "Trying host IP fallback..."
  docker exec "${UNIFAI_CONTAINER}" wget -qO- "http://76.13.243.253:11434/api/tags" | head -c 120 || true
  OLLAMA_URL="http://76.13.243.253:11434"
fi

echo ""
echo "=== 4) Set env on running container (recreate for permanent) ==="
echo "Add to zen_gauss_v1 docker-compose / 1Panel env:"
echo "  BROWSER_AI_OLLAMA_URL=${OLLAMA_URL}"
echo ""
echo "Then rebuild image from latest code (callOllamaChatAny auto-fallback) and:"
echo "  docker compose up -d ${UNIFAI_CONTAINER} --force-recreate"
echo ""
echo "Quick test after deploy — Dashboard → Rules → Test bot with prompt: india"
