# AWS Infrastructure Removal Plan (Post‑GCP Cutover)

**Status:** Executed (repo cleanup complete; AWS account teardown optional)  
**Last updated:** 2026-01-31  
**Scope:** Remove AWS code, dependencies, CI/CD, and infra-as-code from this repo (plus optional AWS account cleanup if anything remains).  
**Repo rules:** No secrets committed; do not use `git add .` or `git add -A` — stage changes explicitly (prefer `git rm` for deletions).

## Overview

With the GCP migration complete, this plan removes all AWS infrastructure, dependencies, code, and documentation from the emoji-smith codebase. Total estimated removal: ~3,500+ lines across 25+ files.

**Repo cleanup completed (2026-01-31):** AWS code/infra/dependencies removed; docs and CI updated for GCP Cloud Run + Pub/Sub. Remaining optional work is AWS account teardown (Phase 0) and removing AWS GitHub secrets/variables.

---

## Pre-Removal Verification

Before starting, verify GCP is fully operational:
```bash
# Check GCP services are responding
gcloud run services describe emoji-smith-webhook --region=us-central1
gcloud run services describe emoji-smith-worker --region=us-central1

# Confirm the Slack app URLs point at Cloud Run (NOT AWS API Gateway)
# Test end-to-end emoji generation via Slack
```

**Optional: create a safety tag:**
```bash
git tag pre-aws-cleanup
git push origin pre-aws-cleanup
```

---

## DO NOT TOUCH (GCP is already deployed and running)

The following files/directories are GCP infrastructure and must NOT be modified:

| Category | Path | Reason |
|----------|------|--------|
| Workflow | `.github/workflows/deploy-gcp.yml` | Active GCP deployment pipeline |
| Terraform | `terraform/` | GCP infrastructure already deployed |
| Source | `src/emojismith/infrastructure/gcp/` | Active GCP handlers |
| Source | `src/emojismith/infrastructure/gcp/webhook_app.py` | Running in production |
| Source | `src/emojismith/infrastructure/gcp/worker_app.py` | Running in production |
| Source | `src/emojismith/infrastructure/gcp/pubsub_job_queue.py` | Active Pub/Sub queue |
| Docker | `Dockerfile.webhook` | Used by GCP Cloud Run |
| Docker | `Dockerfile.worker` | Used by GCP Cloud Run |
| Dependencies | GCP packages in pyproject.toml | `google-cloud-pubsub`, etc. |

---

## Phase 0: Tear Down AWS Infrastructure (CDK Destroy)

**Purpose:** Remove deployed AWS resources before deleting the CDK code.

### AWS Resources to be Destroyed:

| Resource Type | Name | Notes |
|---------------|------|-------|
| Lambda | `emoji-smith-webhook` | Webhook handler |
| Lambda | `emoji-smith-worker` | Worker function |
| API Gateway | `emoji-smith-webhooks` | REST API |
| SQS Queue | `emoji-smith-processing` | Job queue |
| SQS Queue | `emoji-smith-processing-dlq` | Dead letter queue |
| IAM User | `emoji-smith-deployment-user` | GitHub Actions user |
| IAM Roles | Lambda execution roles | Auto-created by CDK |
| Secrets Manager | `emoji-smith/production` | **Backup secrets first!** |
| CloudWatch Logs | `/aws/lambda/emoji-smith-*` | Log groups |

### Pre-Destruction Checklist:

1. **Verify Slack is pointing to GCP** (not AWS API Gateway)

2. **Revoke/delete IAM access keys** for deployment user (if any were created):
```bash
aws iam list-access-keys --user-name emoji-smith-deployment-user
# Delete any keys found
```

**Note:** Secrets Manager will be destroyed with the stack (secrets already exist in GCP Secret Manager).

### Destroy Commands:

```bash
# Navigate to infra directory
cd infra

# Activate Python environment for CDK
source .venv/bin/activate || (python -m venv .venv && source .venv/bin/activate)
uv pip install -r requirements.txt

# Preview what will be destroyed
cdk diff

# Destroy the stack (requires confirmation)
cdk destroy

# Verify stack is gone
aws cloudformation describe-stacks --stack-name EmojiSmithStack 2>&1 | grep -q "does not exist"
```

### Post-CDK Cleanup (ECR not managed by stack):

```bash
# Delete ECR repository and all images (required - not managed by CDK)
aws ecr delete-repository --repository-name emoji-smith --force

# Delete any remaining CloudWatch log groups
aws logs delete-log-group --log-group-name /aws/lambda/emoji-smith-webhook 2>/dev/null || true
aws logs delete-log-group --log-group-name /aws/lambda/emoji-smith-worker 2>/dev/null || true
```

### Verification:

```bash
# Confirm no Lambda functions remain
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'emoji-smith')]"

# Confirm no SQS queues remain
aws sqs list-queues --queue-name-prefix emoji-smith

# Confirm API Gateway is gone
aws apigateway get-rest-apis --query "items[?name=='emoji-smith-webhooks']"
```

---

## Phase 1: Remove GitHub Workflows

**Delete these files:**
- `.github/workflows/deploy.yml` (AWS deployment pipeline)
- `.github/workflows/validate-lambda-package.yml` (Lambda package validator)

**Keep:**
- `.github/workflows/deploy-gcp.yml` (active GCP pipeline)
- `.github/workflows/claude.yml` (keep, but update text to remove AWS/Lambda references)

**Also remove GitHub secrets/variables no longer needed (after deleting AWS workflows):**
- Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (and any other AWS credentials)
- Variables: any AWS-specific `vars.*` (if present)

**Verification:** Push to branch, confirm GCP CI still runs.

---

## Phase 2: Remove CDK Infrastructure Directory

**Delete entire directory:**
```
infra/
├── app.py
├── cdk.json
├── requirements.txt
├── README.md
└── stacks/
    ├── __init__.py
    └── emoji_smith_stack.py
```

---

## Phase 3: Remove AWS Source Code

### 3.1 Delete Root Lambda Entry Point
- `src/webhook_handler.py`

### 3.2 Delete AWS Infrastructure Directory
```
src/emojismith/infrastructure/aws/
├── __init__.py
├── webhook_handler.py
├── worker_handler.py
└── secrets_loader.py
```

### 3.3 Delete SQS Job Queue
- `src/emojismith/infrastructure/jobs/sqs_job_queue.py`

### 3.4 Update wiring.py

**Current (src/emojismith/infrastructure/wiring.py):**
```python
from emojismith.infrastructure.aws.webhook_handler import create_webhook_handler
```

**Preferred approach (to enable deleting all AWS code):**
- Update wiring to build the handler using the Cloud Run adapter (`emojismith.infrastructure.gcp.webhook_app.create_webhook_handler`) OR delete `src/emojismith/infrastructure/wiring.py` entirely and run the Cloud Run app module directly for local dev.

### 3.5 Update local dev entry points (required)

AWS removal changes local dev: `src/emojismith/dev_server.py` should run the Cloud Run webhook app for local testing.

Update these to use the Cloud Run webhook app:
- `src/emojismith/dev_server.py`
- `run_dev.sh`
- `justfile` `dev:` task (or keep it, but make it start the Cloud Run webhook app)

---

## Phase 4: Remove AWS Tests

**Delete these test files:**
- `tests/unit/test_worker_handler.py`
- `tests/unit/infrastructure/test_cdk_stack.py`
- `tests/unit/infrastructure/jobs/test_sqs_job_queue.py`
- `tests/integration/test_sqs_job_queue_integration.py`
- `tests/integration/test_lambda_package.py`
- `tests/integration/test_dual_lambda_e2e.py`
- `tests/integration/aws/test_aws_secrets_loader.py`

**Delete empty directory:**
- `tests/integration/aws/`

**Update tests/conftest.py** - Remove lines 30-39:
```python
# DELETE THIS FIXTURE
@pytest.fixture(autouse=True)
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    ...
```

---

## Phase 4.5: Add GCP Unit Tests

**Purpose:** Maintain infrastructure layer test coverage (70% target per `tests/CLAUDE.md`) after removing AWS tests.

**Note:** Currently NO GCP-specific tests exist in the codebase.

### Tests to Create:

**`tests/unit/infrastructure/gcp/test_pubsub_job_queue.py`**
- Test `PubSubJobQueue.enqueue_job()` with mocked `google.cloud.pubsub_v1.PublisherClient`
- Test message serialization/deserialization
- Test error handling (publish failures, retries)
- Follow Arrange-Act-Assert pattern per testing guidelines

**`tests/unit/infrastructure/gcp/test_webhook_app.py`**
- Test webhook endpoint receives Slack events
- Test Slack signature verification
- Test 3-second timeout compliance (acknowledge fast, enqueue work)
- Mock Pub/Sub for job enqueueing

**`tests/unit/infrastructure/gcp/test_worker_app.py`**
- Test worker processes Pub/Sub push messages
- Test message acknowledgment flow
- Test error handling and logging
- Mock domain services (emoji generation)

### Test Guidelines (from `tests/CLAUDE.md`):
- **Mock external services** (GCP Pub/Sub, Slack API) - avoid network calls
- **Don't mock domain entities** - test actual business logic
- **Test behavior, not implementation** - focus on what the code does
- **Use descriptive test names** - `test_<scenario>_<expected_outcome>`

### Notes
- `PubSubJobQueue` reads `PUBSUB_PROJECT` and `PUBSUB_TOPIC` from env; tests should set those.
- The current implementation constructs `PublisherClient()` inside `__init__`, so tests should patch `google.cloud.pubsub_v1.PublisherClient` (per `src/emojismith/infrastructure/gcp/CLAUDE.md`).

---

## Phase 5: Remove AWS Dockerfile

**Delete:**
- `Dockerfile` (AWS Lambda worker image, uses `public.ecr.aws` base)

**Keep:**
- `Dockerfile.webhook` (GCP Cloud Run)
- `Dockerfile.worker` (GCP Cloud Run)

---

## Phase 6: Remove Build Scripts & Requirements

**Delete:**
- `scripts/build_webhook_package.sh`
- `requirements-webhook.txt`
- `requirements-webhook.lock` (if exists)

**Update/remove AWS dev helpers:**
- `scripts/dev-setup.sh` (remove SQS/AWS examples; add Pub/Sub env vars if still useful)

---

## Phase 7: Update pyproject.toml

**Remove from `[project].dependencies`:**
```toml
"boto3>=1.34.0",
"aioboto3>=13.0.0",
"mangum>=0.17.0",
```

**Remove from `[project.optional-dependencies].dev`:**
```toml
"moto[sqs,secretsmanager]>=5.0.0",
"aws-cdk-lib>=2.0.0",
"constructs>=10.0.0",
"types-boto3>=1.0.0",
```

**Remove from `[dependency-groups].dev`:**
```toml
"moto[sqs]>=5.1.6",
"aws-cdk-lib>=2.0.0",
"constructs>=10.0.0",
```

**Remove from `[dependency-groups].webhook`:**
```toml
"boto3>=1.37.3",
"mangum>=0.19.0",
```

**Update `[tool.coverage.run].omit`:**
Remove: `"src/emojismith/infrastructure/aws/webhook_handler.py"`

---

## Phase 8: Update Environment Config

**Update .env.example:**
- Remove AWS_DEFAULT_REGION, AWS_ACCOUNT_ID comments
- Ensure GCP config is present (PUBSUB_PROJECT, PUBSUB_TOPIC)

---

## Phase 9: Update Documentation

### 9.1 Create/Update Architecture Docs (GCP is production)

**Create:** `docs/GCP.md` (new source of truth)
- Include a diagram and request flow:
  - Slack → Cloud Run `emoji-smith-webhook` → Pub/Sub → Cloud Run `emoji-smith-worker` → Slack API
- Document endpoints:
  - Webhook: `POST /slack/events`, `POST /slack/interactive`, `GET /health`
  - Worker: `POST /pubsub`, `GET /health`
- Document security model at a high level:
  - Slack signature verification (webhook)
  - Pub/Sub push auth (OIDC) to worker (private)
  - Secrets via Secret Manager → env injection
- Document CI/CD at a high level:
  - GitHub Actions → Artifact Registry → Cloud Run deploy

### 9.2 ADR Updates

**Update ADR-002** to be provider-neutral (keep the decision, remove AWS specifics):
- File: `docs/adr/002-two-lambda-separation.md`
- Rename the title inside the file to “Separate Webhook and Worker Services”
- Replace “Lambda/SQS/CDK” language with “webhook service / worker service + queue”
- Add a short “Current implementation” note: Cloud Run + Pub/Sub (as of 2026-01-31)

**Update ADR-003** to remove AWS-specific language:
- File: `docs/adr/003-repository-pattern.md`
- Replace “AWS” examples with “GCP” where relevant (keep Slack/OpenAI examples)

**Create new ADR** documenting the migration:
- File: `docs/adr/004-migrate-to-gcp.md`
- Keep it short and decision-focused; link the new architecture doc from 9.1

### 9.3 Delete AWS-Only / Obsolete Docs (do not archive)

Delete these files/directories (they describe AWS/Lambda/SQS/CDK and will be misleading after removal):
- `docs/architecture/dual-lambda.md`
- `docs/architecture/cross_context_dependency_analysis.md`
- `docs/backup/CLAUDE-original-20250621.md`
- `docs/architecture/historical/` (directory)
- `docs/testing/historical/` (directory)

### 9.4 Update Remaining Docs to Reflect GCP Deployment & Architecture

Update the following so there are no AWS deployment instructions left and the architecture is described as Cloud Run + Pub/Sub:

**CLAUDE.md (root):**
- Remove "Fixed Lambda Handler Locations" section referencing AWS paths
- Replace with “Fixed Cloud Run entry points” (webhook + worker apps)

**src/CLAUDE.md:**
- Remove AWS Secrets Manager examples; reference Secret Manager + Cloud Run env injection

**src/emojismith/infrastructure/CLAUDE.md:**
- Replace Lambda handler patterns with Cloud Run app patterns (FastAPI entry points)
- Replace Secrets Manager examples with GCP Secret Manager

**.github/CLAUDE.md:**
- Remove CDK/AWS examples; describe Workload Identity Federation + Cloud Run deploy workflow

**README.md:**
- Update architecture diagram (Cloud Run webhook + Pub/Sub + Cloud Run worker)
- Replace AWS CDK deployment steps with Terraform + GitHub Actions (deploy-gcp)
- Update env var table (remove `SQS_QUEUE_URL`, add `PUBSUB_PROJECT`, `PUBSUB_TOPIC`)
- Update any links that point at deleted AWS docs (e.g., “Dual Lambda Architecture”)
- Link to `docs/GCP.md` as the canonical GCP architecture/deploy doc

**AGENTS.md:**
- Replace “AWS Lambda” wording with “GCP Cloud Run”
- Update the “Fixed Lambda Handler Locations” guidance to Cloud Run entry points

**docs/TESTING-ORGANIZATION.md** and **docs/testing/testing-guidelines.md:**
- Replace AWS examples (moto/SQS) with GCP examples (mock Pub/Sub publisher; worker push payload)

**docs/integrations/claude-github-action.md:**
- Remove AWS/Lambda/SQS examples and replace with GCP/Cloud Run/Pub/Sub equivalents

**docs/google-nano-banana-migration.md:**
- Replace AWS/Lambda/SQS/CDK references with Cloud Run/Pub/Sub/Terraform (keep provider-selection behavior)

**docs/architecture/structured-logging-design.md:**
- Replace “both Lambda functions” wording with “webhook service + worker service”
- Update file references away from `.../infrastructure/aws/...` to the GCP apps

**docs/CHANGELOG.md:**
- Add an entry for the GCP migration + AWS removal (2026-01-31)
- Remove/adjust any “planned improvements” that are AWS-only (CDK/SQS/Lambda)

---

## Phase 10: Regenerate Lock Files

```bash
uv sync --all-extras
uv lock
```

Also regenerate the pinned pip lockfiles (they are tracked in git):
```bash
uv pip compile --generate-hashes -o requirements.lock pyproject.toml
uv pip compile --extra dev --generate-hashes -o requirements-dev.lock pyproject.toml
```

---

## Phase 11: Final Verification

```bash
# Quality checks
source .venv/bin/activate
just qa

# Verify GCP imports work
python -c "from emojismith.infrastructure.gcp.webhook_app import app; print('OK')"

# Full test suite
pytest tests/ -v

# Create PR to trigger GCP CI (stage explicitly; no `git add -A`)
git checkout -b chore/remove-aws-infrastructure
git status --short
# Prefer `git rm` for deletions and `git add <file>` for modifications.
# Examples (adjust to match your actual changes):
#   git rm .github/workflows/deploy.yml .github/workflows/validate-lambda-package.yml
#   git rm Dockerfile scripts/build_webhook_package.sh requirements-webhook.txt requirements-webhook.lock
#   git rm -r infra src/emojismith/infrastructure/aws src/emojismith/infrastructure/jobs/sqs_job_queue.py tests/integration/aws
#   git add pyproject.toml uv.lock README.md CLAUDE.md .env.example run_dev.sh src/emojismith/dev_server.py
git commit -m "chore: remove AWS infrastructure after GCP migration"
git push origin chore/remove-aws-infrastructure
gh pr create --title "chore: Remove AWS infrastructure" --body "..."
```

---

## Summary

### Files to DELETE (25 files):

| Category | Files |
|----------|-------|
| Workflows | `.github/workflows/deploy.yml`, `.github/workflows/validate-lambda-package.yml` |
| CDK | `infra/` (entire directory - 6 files) |
| Source | `src/webhook_handler.py`, `src/emojismith/infrastructure/aws/` (4 files), `src/emojismith/infrastructure/jobs/sqs_job_queue.py` |
| Tests | 7 test files + `tests/integration/aws/` directory |
| Docker | `Dockerfile` |
| Scripts | `scripts/build_webhook_package.sh` |
| Requirements | `requirements-webhook.txt`, `requirements-webhook.lock` |

### Files to MODIFY (10 files):

| File | Change |
|------|--------|
| `src/emojismith/infrastructure/wiring.py` | Update or remove AWS imports |
| `tests/conftest.py` | Remove `aws_credentials` fixture |
| `pyproject.toml` | Remove 8+ AWS dependencies |
| `.env.example` | Remove AWS config |
| `CLAUDE.md` | Update architecture references |
| `src/CLAUDE.md` | Remove AWS examples |
| `src/emojismith/infrastructure/CLAUDE.md` | Remove Lambda patterns |
| `.github/CLAUDE.md` | Update to GCP architecture |
| `README.md` | Update architecture, tech stack, deployment |

### Files to CREATE (4 files):

| File | Purpose |
|------|---------|
| `docs/adr/004-migrate-to-gcp.md` | New ADR documenting decision to migrate from AWS to GCP |
| `tests/unit/infrastructure/gcp/test_pubsub_job_queue.py` | Unit tests for Pub/Sub job queue adapter |
| `tests/unit/infrastructure/gcp/test_webhook_app.py` | Unit tests for Cloud Run webhook handler |
| `tests/unit/infrastructure/gcp/test_worker_app.py` | Unit tests for Cloud Run worker handler |

---

## Rollback

If needed, recover from git:
```bash
git checkout pre-aws-cleanup -- <file-path>
```
