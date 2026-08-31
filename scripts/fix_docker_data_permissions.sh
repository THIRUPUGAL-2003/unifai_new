#!/bin/sh
# Fix ./data permissions for zen_gauss_v1 (container runs as UID 1000).
# Run once on the server from project root:
#   cd /opt/projects/unifai_new && sh scripts/fix_docker_data_permissions.sh

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/data"

mkdir -p "$DATA/logs" "$DATA/pdf" "$DATA/attachments"

if [ "$(id -u)" -eq 0 ]; then
  chown -R 1000:1000 "$DATA"
  chmod -R 755 "$DATA"
  echo "OK: $DATA owned by 1000:1000"
else
  sudo chown -R 1000:1000 "$DATA"
  sudo chmod -R 755 "$DATA"
  echo "OK: $DATA owned by 1000:1000 (via sudo)"
fi

ls -la "$DATA"
