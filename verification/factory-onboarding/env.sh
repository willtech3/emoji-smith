# Sourced by the Factory onboarding scripts. Synthetic, non-secret configuration only.
# Generated test secrets live in "$FACTORY_STATE/secrets.env" (created by start.sh).
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export ROOT
export FACTORY_STATE="${FACTORY_STATE_DIR:-/tmp/emoji-smith-factory}"
PY="$ROOT/.venv/bin/python"
export PY

# Pub/Sub: the unmodified google-cloud-pubsub PublisherClient switches to an insecure
# channel with anonymous credentials when PUBSUB_EMULATOR_HOST is set.
export PUBSUB_PROJECT="factory-test-project"
export PUBSUB_TOPIC="emoji-smith-jobs"
export PUBSUB_EMULATOR_HOST="127.0.0.1:8085"

# OpenAI SDK honours OPENAI_BASE_URL; points at the in-sandbox fake (fake_openai.py).
export OPENAI_BASE_URL="http://127.0.0.1:8090/v1"
export OPENAI_CHAT_MODEL="gpt-5"

# Telemetry exporters stay disabled so no Google Cloud credentials are needed.
export TRACING_ENABLED="false"
export METRICS_ENABLED="false"
export ENVIRONMENT="factory-test"
export LOG_LEVEL="INFO"
export PYTHONPATH="$ROOT/src"

# Never route loopback traffic through a sandbox proxy (httpx, urllib and gRPC).
export NO_PROXY="127.0.0.1,localhost${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY"
export no_grpc_proxy="127.0.0.1,localhost"

# No real cloud credentials or provider keys are used by this recipe.
unset GOOGLE_APPLICATION_CREDENTIALS GOOGLE_API_KEY
