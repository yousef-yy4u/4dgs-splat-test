#!/usr/bin/env bash
# Restart the live walk viewer. Safe to re-run; kills any prior instance first.
#   ./start.sh [PORT]
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8000}"
pkill -f '[s]erve_viewer.py' 2>/dev/null || true
sleep 1
setsid python3 serve_viewer.py --port "$PORT" --out ../motion_out --stem walk \
  > /tmp/4dgs_viewer.log 2>&1 < /dev/null &
disown 2>/dev/null || true
sleep 2
echo "viewer -> http://localhost:$PORT   (log: /tmp/4dgs_viewer.log)"
curl -s "localhost:$PORT/status.json" && echo
