#!/bin/bash
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/tools/dev/start_app.sh" "$@"
