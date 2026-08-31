#!/bin/bash
# One-shot server fix for UnifAI Docker (run as root on srv1405395)
# Usage: cd /opt/projects/unifai_new && bash scripts/server_docker_fix.sh

set -e
cd "$(dirname "$0")/.."
echo "=== UnifAI server fix ==="

echo "[1/6] Stop and remove ALL old containers..."
docker rm -f zen_gauss zen_gauss_v1 unifai_browser_ai_proxy unifai_browser_proxy unifai_broswer_proxy 2>/dev/null || true

echo "[2/6] Fix data folder permissions (UID 1000)..."
mkdir -p data/logs data/pdf data/attachments
chown -R 1000:1000 data
chmod -R 755 data

echo "[3/6] Ensure config.json exists in data..."
if [ ! -f data/config.json ] && [ -f config.json ]; then
  cp config.json data/config.json
fi

echo "[4/6] Pull latest code (optional)..."
git pull 2>/dev/null || echo "  (git pull skipped or failed — continuing)"

echo "[5/6] Start fresh containers..."
docker compose up -d

echo "[6/6] Wait and check health..."
sleep 5
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
if docker exec zen_gauss_v1 wget -q -O /dev/null http://127.0.0.1:8081/health 2>/dev/null; then
  echo "OK: Backend health check PASSED"
else
  echo "WARN: Backend not healthy yet — check logs:"
  echo "  docker logs zen_gauss_v1 --tail 50"
fi
echo ""
echo "Test DNS from container:"
docker exec zen_gauss_v1 nslookup getunifai.ai 2>/dev/null || echo "  DNS still failing — check server network"
echo "=== Done ==="
