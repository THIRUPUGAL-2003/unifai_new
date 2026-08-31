#!/bin/bash
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tools/dev/stop_app.sh" "$@"
