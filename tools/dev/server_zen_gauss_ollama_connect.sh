#!/bin/sh
# Connect UnifAI container → Ollama. Values come from env (no hardcoded hosts).
# Required: OLLAMA_URL (or BROWSER_AI_OLLAMA_URL), optional UNIFAI_CONTAINER / DOCKER_NETWORK
set -e

OLLAMA_URL="${BROWSER_AI_OLLAMA_URL:-${OLLAMA_URL:-http://127.0.0.1:11434}}"
UNIFAI_CONTAINER="${UNIFAI_CONTAINER:-zen_gauss_v1}"
NETWORK="${DOCKER_NETWORK:-1panel-network}"

echo "=== 1) Ollama health ==="
curl -sf "${OLLAMA_URL}/api/tags" >/dev/null && echo "OK: ${OLLAMA_URL}" || {
  echo "FAIL: Ollama not reachable at ${OLLAMA_URL} — set OLLAMA_URL in .env"
  exit 1
}

echo ""
echo "=== 2) Attach ${UNIFAI_CONTAINER} to ${NETWORK} (optional) ==="
if docker network inspect "${NETWORK}" >/dev/null 2>&1; then
  docker network connect "${NETWORK}" "${UNIFAI_CONTAINER}" 2>/dev/null || echo "Already on ${NETWORK}"
else
  echo "WARN: network ${NETWORK} not found (set DOCKER_NETWORK if needed)"
fi

echo ""
echo "=== 3) Test from UnifAI container ==="
if docker exec "${UNIFAI_CONTAINER}" wget -qO- "${OLLAMA_URL}/api/tags" | head -c 120; then
  echo ""
  echo "OK: ${UNIFAI_CONTAINER} → ${OLLAMA_URL}"
else
  echo "FAIL: container cannot reach ${OLLAMA_URL}"
  echo "Set BROWSER_AI_OLLAMA_URL / OLLAMA_URL to a URL reachable from the container"
  exit 1
fi

echo ""
echo "Add to UnifAI compose / .env:"
echo "  OLLAMA_URL=${OLLAMA_URL}"
echo "  BROWSER_AI_OLLAMA_URL=${OLLAMA_URL}"
