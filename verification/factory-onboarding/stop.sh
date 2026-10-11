#!/usr/bin/env bash
# Stop every process started by start.sh. Always succeeds.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
for name in worker webhook fake-openai fake-pubsub; do
  pidfile="$FACTORY_STATE/$name.pid"
  [ -f "$pidfile" ] || continue
  pid="$(cat "$pidfile")"
  if kill "$pid" 2>/dev/null; then
    for _ in $(seq 1 10); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
done
rm -f "$FACTORY_STATE/secrets.env"
exit 0
