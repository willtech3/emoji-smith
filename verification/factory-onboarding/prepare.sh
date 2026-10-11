#!/usr/bin/env bash
# Install dependencies the way CI does (.github/workflows/deploy-gcp.yml:
# Python 3.12 + `uv sync --all-extras`). requirements*.lock are stale relative to
# uv.lock (e.g. openai 1.86.0 vs 3.1.0) and are intentionally not used.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
mkdir -p "$FACTORY_STATE"

if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
else
  python3 -m venv "$FACTORY_STATE/uv-venv"
  "$FACTORY_STATE/uv-venv/bin/python" -m pip install --quiet --upgrade uv
  UV="$FACTORY_STATE/uv-venv/bin/uv"
fi
echo "$UV" > "$FACTORY_STATE/uv-path"

cd "$ROOT"
"$UV" sync --all-extras --python 3.12

"$PY" -c "import emojismith, shared, grpc, google.pubsub_v1, openai, PIL, uvicorn; print('emoji-smith environment ready')"
