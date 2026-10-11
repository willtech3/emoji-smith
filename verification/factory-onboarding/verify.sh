#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
set -a
source "$FACTORY_STATE/secrets.env"
set +a
exec "$PY" "$HERE/verify.py"
