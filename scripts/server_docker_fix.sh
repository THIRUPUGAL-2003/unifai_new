#!/bin/sh
# Recreate Docker stack after compose service/port rename.
set -e

cd "$(dirname "$0")/.."

echo "Removing old containers..."
docker rm -f zen_gauss zen_gauss_v1 unifai_browser_ai_proxy unifai_browser_proxy unifai_broswer_proxy 2>/dev/null || true

echo "Starting updated stack..."
docker compose up -d

echo "Waiting for zen_gauss_v1..."
sleep 5

if docker exec zen_gauss_v1 wget -q -O /dev/null http://127.0.0.1:8081/health 2>/dev/null; then
  echo "OK: zen_gauss_v1 healthy on :8081"
else
  echo "WARN: health check failed — run: docker logs zen_gauss_v1 --tail 50"
fi

echo "Done."
echo "  UnifAI dashboard: http://localhost:8081"
echo "  Lab browser proxy: http://localhost:8082"
