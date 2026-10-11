#!/usr/bin/env bash
# Reset the fakes' recorders and write the synthetic Slack workspace fixture.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
exec "$PY" "$HERE/verify.py" --seed
