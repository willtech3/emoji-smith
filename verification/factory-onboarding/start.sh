#!/usr/bin/env bash
# Start in-sandbox fakes (Pub/Sub publisher, OpenAI) and the unmodified production
# webhook and worker FastAPI apps. Test secrets are generated here, never supplied.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/env.sh"
mkdir -p "$FACTORY_STATE"
cd "$ROOT"

umask 077
"$PY" -c 'import secrets
print("export SLACK_SIGNING_SECRET=" + secrets.token_hex(32))
print("export SLACK_BOT_TOKEN=xoxb-factory-synthetic-" + secrets.token_hex(12))
print("export OPENAI_API_KEY=sk-factory-synthetic-" + secrets.token_hex(16))' > "$FACTORY_STATE/secrets.env"
umask 022

launch() {
  local name="$1"; shift
  nohup "$@" > "$FACTORY_STATE/$name.log" 2>&1 &
  echo $! > "$FACTORY_STATE/$name.pid"
}

wait_http() {
  local name="$1" url="$2"
  for _ in $(seq 1 90); do
    if "$PY" -c "import sys, urllib.request as u
o = u.build_opener(u.ProxyHandler({}))
sys.exit(0 if o.open('$url', timeout=2).status == 200 else 1)" 2>/dev/null; then
      echo "$name healthy at $url"
      return 0
    fi
    sleep 1
  done
  echo "$name did not become healthy at $url; last log lines:" >&2
  tail -n 60 "$FACTORY_STATE/$name.log" >&2 || true
  return 1
}

launch fake-pubsub "$PY" "$HERE/fake_pubsub.py" --grpc-port 8085 --http-port 8086
launch fake-openai "$PY" "$HERE/fake_openai.py" --port 8090
wait_http fake-pubsub http://127.0.0.1:8086/health
wait_http fake-openai http://127.0.0.1:8090/health

# Webhook: needs the signing secret and a (synthetic, non-functional) bot token at
# import time; Pub/Sub publishing goes to the fake via PUBSUB_EMULATOR_HOST.
(
  set -a
  source "$FACTORY_STATE/secrets.env"
  set +a
  unset OPENAI_API_KEY
  launch webhook "$ROOT/.venv/bin/uvicorn" emojismith.infrastructure.gcp.webhook_app:app \
    --host 0.0.0.0 --port 8080
)

# Worker: started without Slack/OpenAI credentials so it can never reach slack.com;
# only its HTTP contract (health + push envelope validation) is exercised over HTTP.
launch worker "$ROOT/.venv/bin/uvicorn" emojismith.infrastructure.gcp.worker_app:app \
  --host 0.0.0.0 --port 8081

wait_http webhook http://127.0.0.1:8080/health
wait_http worker http://127.0.0.1:8081/health
