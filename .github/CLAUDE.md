# CLAUDE.md - Deployment and CI/CD Guidelines (GCP)

## Inheritance
- **Extends:** /CLAUDE.md (root)
- **Overrides:** None (CRITICAL RULES cannot be overridden)
- **Scope:** All GitHub Actions workflows, CI/CD pipelines, and deployment processes

## Rules

**Context:** This document provides guidelines for working with CI/CD pipelines and GCP deployment (Cloud Run + Pub/Sub). Read this when changing GitHub Actions, Terraform infra, or deployment configuration.

## 🚀 Deployment Philosophy

**Golden Rule:** All deployments happen through CI/CD. Manual deployments are forbidden when CI exists.

## Architecture Overview (Production)

Emoji Smith runs on GCP with a fast webhook service and an async worker service:

```
Slack → Cloud Run (webhook, public) → Pub/Sub → Cloud Run (worker, private) → Slack API
```

Key properties:
- Webhook service responds within Slack’s 3-second timeout.
- Worker service handles image generation and Slack posting.
- Pub/Sub retries worker deliveries on non-2xx responses.

For the full architecture + operations details, see `README.md`.

## CI/CD Pipeline

### GitHub Actions Workflow

Primary workflow:
- `.github/workflows/deploy-gcp.yml`

High-level stages:
1. **Build/Test**: `ruff format --check`, `ruff check`, `mypy`, `pytest`
2. **Build Images**: `Dockerfile.webhook`, `Dockerfile.worker`
3. **Push Images**: Artifact Registry
4. **Deploy**: Cloud Run services (webhook + worker)

### Authentication (Keyless)

CI/CD uses **Workload Identity Federation (WIF)**. Do not add long-lived GCP service account keys to GitHub Secrets.

### GitHub Actions Variables (Required)

Configured in GitHub: Settings → Secrets and variables → Actions → Variables

- `GCP_PROJECT_ID`
- `GCP_PROJECT_NUMBER`
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_CICD_SERVICE_ACCOUNT`

### GitHub Actions Secrets (Required)

- `ANTHROPIC_API_KEY` (for `.github/workflows/claude.yml` only)

Application runtime secrets (Slack/OpenAI/Google keys) should live in **GCP Secret Manager** and be injected into Cloud Run by Terraform — not stored in GitHub.

## Infrastructure as Code

Terraform (GCP):
- `terraform/`

Rules:
- Keep secrets out of terraform state: use Secret Manager resources and avoid embedding secret values.
- `terraform.tfstate` and `terraform.tfvars` should remain gitignored.

## Local Development

Run the webhook service locally:
```bash
source .venv/bin/activate
uv sync --all-extras --dev
python -m emojismith.dev_server
```

Expose to Slack during local dev:
```bash
ngrok http 8000
```

## Rollback

Preferred rollback mechanisms:
1. **Revert the merge commit on `main`**. CI redeploys previous behavior.
2. **Cloud Run traffic rollback** (if you have access): shift traffic back to a previous revision.

## Monitoring & Logs

- Use **Cloud Logging** for both services (webhook + worker).
- Prefer structured JSON logs for queryability and correlation (trace/job IDs).

## Security Best Practices (GCP)

- **Least privilege** on service accounts used by Cloud Run and Pub/Sub push.
- **Protect the worker endpoint** so only Pub/Sub can invoke it (OIDC auth).
- **No secrets in GitHub** (except those required for CI tooling like `ANTHROPIC_API_KEY`).

- Deploy manually to production
- Skip CI/CD pipeline
- Use `cdk deploy` without context
- Commit secrets to repository
- Ignore failed deployments
