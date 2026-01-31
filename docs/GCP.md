# GCP Deployment & Architecture (Cloud Run + Pub/Sub)

**Status:** Production  
**Last updated:** 2026-01-31  

Emoji Smith runs entirely on Google Cloud Platform:

- **Cloud Run (public)**: `emoji-smith-webhook` — receives Slack Events + Interactivity, validates Slack signature, and enqueues async jobs
- **Pub/Sub**: topic + push subscription — transports jobs from webhook → worker
- **Cloud Run (private)**: `emoji-smith-worker` — processes Pub/Sub push messages and calls Slack + AI providers
- **Secret Manager**: stores secrets; Cloud Run injects them as env vars
- **Artifact Registry**: stores container images built by GitHub Actions

---

## Architecture

```mermaid
graph TB
  Slack[Slack Workspace] -->|Events + Interactive| Webhook[Cloud Run: emoji-smith-webhook]
  Webhook -->|Publish job| Topic[Pub/Sub Topic: emoji-smith-jobs]
  Topic -->|Push subscription (OIDC)| Worker[Cloud Run: emoji-smith-worker]
  Worker -->|OpenAI / Gemini| AI[AI Providers]
  Worker -->|Upload emoji / share file| Slack
  Secrets[Secret Manager] --> Webhook
  Secrets --> Worker
  CI[GitHub Actions] -->|WIF (OIDC)| AR[Artifact Registry]
  CI -->|Deploy| Webhook
  CI -->|Deploy| Worker
```

---

## Runtime Entry Points

### Webhook service
- Code: `src/emojismith/infrastructure/gcp/webhook_app.py`
- Endpoints:
  - `GET /health`
  - `POST /slack/events`
  - `POST /slack/interactive`

### Worker service
- Code: `src/emojismith/infrastructure/gcp/worker_app.py`
- Endpoints:
  - `GET /health`
  - `POST /pubsub` (Pub/Sub push handler)

---

## Security Model (High Level)

### Slack → Webhook (public)
- **Slack signature verification** is required for all non-`url_verification` requests.
- Slack secrets are provided via **Secret Manager → Cloud Run env injection**.

### Pub/Sub → Worker (private)
- Pub/Sub push subscription authenticates to the worker using **OIDC**.
- The worker should only accept requests from the Pub/Sub service account / identity configured in Terraform.

### Secrets
- No secrets are committed to git.
- Secrets live in Secret Manager and are injected into Cloud Run as env vars.

---

## Configuration (Environment Variables)

These are the key runtime env vars (set via Terraform / Cloud Run):

### Common
- `LOG_LEVEL` (recommended `INFO` in production)
- `ENVIRONMENT` (e.g., `production`)

### Webhook service
- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `PUBSUB_PROJECT`
- `PUBSUB_TOPIC`

### Worker service
- `SLACK_BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL` (default: `gpt-5`)
- `GOOGLE_API_KEY` (optional; enables Gemini/Imagen providers)

---

## CI/CD

GitHub Actions workflow:
- ` .github/workflows/deploy-gcp.yml`

High-level flow:
1. Run lint/typecheck/tests
2. Build Docker images:
   - `Dockerfile.webhook` → `emoji-smith-webhook`
   - `Dockerfile.worker` → `emoji-smith-worker`
3. Push images to Artifact Registry
4. Deploy both Cloud Run services

Authentication:
- Uses **Workload Identity Federation** (no long-lived keys).

---

## Infrastructure as Code

Terraform lives in:
- `infra_gcp/terraform/`

Notes:
- `terraform.tfstate` / `terraform.tfvars` are intentionally gitignored.
- Apply infra changes via Terraform (initial provisioning), and deploy app changes via CI/CD.

---

## Local Development

Prereqs:
- `uv` installed
- Python 3.12+

```bash
uv venv
source .venv/bin/activate
uv sync --all-extras --dev
```

Create `.env` (copy `.env.example`) and set at minimum:
- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `PUBSUB_PROJECT`
- `PUBSUB_TOPIC`

Run the webhook server locally:
```bash
python -m emojismith.dev_server
```

Expose to Slack (example):
```bash
ngrok http 8000
```

---

## Troubleshooting

### Cloud Run logs
- Use Cloud Logging (recommended), or the helper commands in `justfile`:
  - `just gcp-tail-webhook PROJECT_ID=...`
  - `just gcp-tail-worker PROJECT_ID=...`

### Pub/Sub delivery
- A non-2xx response from the worker triggers Pub/Sub retries.
- Validate the worker `/pubsub` endpoint is protected (OIDC) and reachable from the push subscription.
