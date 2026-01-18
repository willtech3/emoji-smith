# Emoji Smith — GCP Migration Plan (AWS → Google Cloud)

> **Goal:** Migrate Emoji Smith from AWS (API Gateway + Lambda + SQS + Secrets Manager) to Google Cloud while staying **as close to free tier as practical**, keeping the current dual-handler architecture (fast webhook + async worker), and maintaining security posture (no secrets in repo/state, least privilege, DI).

> **Document Version:** 2.0 (Verified against official Terraform provider docs and GCP documentation on 2026-01-18)

---

## 0) Executive Summary (What We're Building)

**Target GCP architecture (serverless + low ops + low cost):**

- **Cloud Run (public) — Webhook service**
  - Receives Slack Events + Interactive requests
  - Validates Slack signature
  - Responds fast (<3s) and publishes an async job to Pub/Sub
- **Pub/Sub — Job queue**
  - Topic: `emoji-smith-jobs`
  - Push subscription delivers jobs to the worker Cloud Run endpoint using **OIDC auth**
  - Dead-letter topic for poison messages
- **Cloud Run (private) — Worker service**
  - Receives Pub/Sub push requests
  - Generates image (OpenAI / Gemini) and posts back to Slack
- **Secret Manager**
  - Stores Slack/OpenAI/Google secrets; injected into Cloud Run as env vars
- **Artifact Registry**
  - Stores container images
- **Cloud Logging**
  - Default structured logs from Cloud Run
- **Workload Identity Federation**
  - Enables GitHub Actions to deploy without service account keys

**CI/CD Pipeline:**
- GitHub Actions with Workload Identity Federation (keyless authentication)
- Parallel pipelines during transition: existing AWS pipeline continues, new GCP pipeline added
- Automated image builds and Cloud Run deployments on merge to main

---

## 1) Current State (AWS)

### 1.1 Runtime flow

1. Slack message action → **Webhook Lambda** (`src/emojismith/infrastructure/aws/webhook_handler.py`)
2. Webhook handler validates Slack signature, opens modal / acknowledges, and enqueues job to **SQS**
3. **Worker Lambda** consumes SQS events (`src/emojismith/infrastructure/aws/worker_handler.py`)
4. Worker calls OpenAI/Gemini, processes image, uploads/creates reaction via Slack

### 1.2 AWS infrastructure in repo

- CDK stack: `infra/` (API Gateway, SQS, Secrets Manager, Lambda)
- AWS-specific code: `src/emojismith/infrastructure/aws/*` and `src/emojismith/infrastructure/jobs/sqs_job_queue.py`
- Lambda Dockerfile: `Dockerfile` (uses `public.ecr.aws/lambda/python:3.12`)

---

## 2) Target GCP Architecture

```mermaid
graph TB
  Slack[Slack Workspace] -->|Events + Interactive| CRW[Cloud Run: webhook public]
  CRW -->|Publish job| PST[Pub/Sub Topic: emoji-smith-jobs]
  PST -->|Push subscription OIDC| CRK[Cloud Run: worker private]
  CRK -->|OpenAI/Gemini| AI[AI Providers]
  CRK -->|Upload emoji / react| Slack
  SM[Secret Manager] --> CRW
  SM --> CRK
  GHA[GitHub Actions] -->|Workload Identity Federation| AR[Artifact Registry]
  GHA -->|Deploy| CRW
  GHA -->|Deploy| CRK
```

### 2.1 Mapping: AWS → GCP

| AWS | GCP | Notes |
|---|---|---|
| API Gateway + Lambda (webhook) | Cloud Run service (public) | Cloud Run runs FastAPI directly and supports HTTPS endpoints. |
| SQS | Pub/Sub | Pub/Sub push subscription integrates well with Cloud Run and has generous free tier. |
| Lambda (worker container) | Cloud Run service (private) | Long-running HTTP request that processes one job; Pub/Sub retries on non-2xx. |
| Secrets Manager | Secret Manager | Inject secrets into Cloud Run without app calling Secret Manager per request. |
| CloudWatch logs | Cloud Logging | Default runtime logs; can add log-based metrics later if needed. |
| CDK | Terraform | Use Google provider; keep secrets out of state. |
| GitHub Actions + AWS credentials | GitHub Actions + Workload Identity Federation | Keyless authentication via OIDC tokens. |

### 2.2 Why Cloud Run + Pub/Sub (and not alternatives)

**Compute (webhook + worker):**
- ✅ **Chosen: Cloud Run**
  - Works naturally with FastAPI and containerized Python.
  - Supports request timeouts up to 60 minutes (worker safety margin).
  - Allows configuring concurrency (keep worker at concurrency=1 if desired).
- Alternative: **Cloud Functions (2nd gen)**
  - Also good (built on Cloud Run), but the app is already structured as FastAPI services and has two distinct runtimes; Cloud Run stays closer to current architecture.
- Alternatives rejected for a personal project: **GKE**, **Compute Engine**
  - Higher ops and baseline costs.

**Queueing:**
- ✅ **Chosen: Pub/Sub push subscription → Cloud Run**
  - Clear decoupling between webhook and worker.
  - Retries built-in; supports dead-letter topics.
  - Pub/Sub has an always-free tier for low message volumes.
- Alternative: **Cloud Tasks**
  - Great for HTTP background tasks and explicit scheduling/dispatch deadlines.
  - Likely fine cost-wise, but Pub/Sub is simpler to scale and has a very generous free tier for message throughput.

**Secrets:**
- ✅ **Chosen: Secret Manager + Cloud Run secret env injection**
  - Avoids embedding secret values in Terraform state or Cloud Run plain env vars.

---

## 3) Cost / Free-Tier Strategy

This bot serves ~7 users, so the **dominant cost will be OpenAI/Gemini usage**, not infra. The goal is to keep GCP infra within always-free where possible.

### 3.1 Free Tier Limits (Verified January 2026)

| Service | Free Tier Allowance | Our Expected Usage | Status |
|---------|--------------------|--------------------|--------|
| **Cloud Run** | 2M requests/month, 360K GB-seconds memory, 180K vCPU-seconds, 1GB egress (North America) | ~100-500 requests/month | ✅ Well under |
| **Pub/Sub** | 10 GiB messages/month | ~1-10 MB/month | ✅ Well under |
| **Secret Manager** | 6 active secret versions, 10K access operations/month | 4 secrets × 1 version = 4 versions | ✅ Under limit |
| **Artifact Registry** | 0.5 GB storage | ~200-400 MB (2 slim images) | ⚠️ Monitor closely |
| **Cloud Build** | 2,500 build-minutes/month (e2-standard-2) | ~10-50 minutes/month | ✅ Well under |
| **Cloud Logging** | 50 GiB/project/month | ~10-100 MB/month | ✅ Well under |

### 3.2 Cost Optimization Settings

- **Cloud Run webhook**: `min_instance_count = 0`, memory = `256Mi`
- **Cloud Run worker**: `min_instance_count = 0`, memory = `512Mi`, `max_instance_request_concurrency = 1`
- **Artifact Registry**: Prune old image tags monthly to stay under 0.5 GB
- **Logging**: Set log level to INFO in production (avoid DEBUG spam)

---

## 4) Terraform Migration Spec (GCP)

### 4.1 Terraform layout

Create a new directory (do not reuse `infra/` to avoid confusion during cutover):

```
infra_gcp/
  terraform/
    main.tf              # Root module composition
    versions.tf          # Provider versions
    providers.tf         # Provider configuration
    backend.tf           # GCS backend (optional)
    variables.tf         # Input variables
    outputs.tf           # Output values
    apis.tf              # Enable required APIs
    iam.tf               # Service accounts + IAM bindings
    secrets.tf           # Secret Manager resources
    artifact_registry.tf # Container registry
    cloud_run_webhook.tf # Webhook Cloud Run service
    cloud_run_worker.tf  # Worker Cloud Run service
    pubsub.tf            # Pub/Sub topics + subscriptions
    workload_identity.tf # GitHub Actions Workload Identity Federation
    cicd.tf              # CI/CD service account and permissions
```

> Decommission step later will remove `infra/` (AWS CDK) after GCP cutover.

### 4.2 versions.tf — Provider versions

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0.0"
    }
  }
}
```

### 4.3 providers.tf — Provider configuration

```hcl
provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

data "google_project" "this" {
  project_id = var.project_id
}
```

### 4.4 variables.tf — Input variables

```hcl
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "github_repo_owner" {
  description = "GitHub repository owner (organization or username)"
  type        = string
}

variable "github_repo_name" {
  description = "GitHub repository name"
  type        = string
  default     = "emoji-smith"
}

variable "github_repo_owner_id" {
  description = "GitHub repository owner ID (numeric). Find via: gh api users/OWNER --jq .id"
  type        = string
}

variable "webhook_image" {
  description = "Full image path for webhook service (e.g., REGION-docker.pkg.dev/PROJECT/emoji-smith/webhook:TAG)"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder for initial deploy
}

variable "worker_image" {
  description = "Full image path for worker service (e.g., REGION-docker.pkg.dev/PROJECT/emoji-smith/worker:TAG)"
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello" # Placeholder for initial deploy
}
```

### 4.5 apis.tf — Enable required APIs

```hcl
# Enable required GCP APIs
# Note: These must be enabled before other resources can be created

resource "google_project_service" "run" {
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "pubsub" {
  service            = "pubsub.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "artifactregistry" {
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iamcredentials" {
  service            = "iamcredentials.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "sts" {
  service            = "sts.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloudbuild" {
  service            = "cloudbuild.googleapis.com"
  disable_on_destroy = false
}
```

### 4.6 artifact_registry.tf — Container image registry

```hcl
resource "google_artifact_registry_repository" "emoji_smith" {
  location      = var.region
  repository_id = "emoji-smith"
  format        = "DOCKER"
  description   = "Docker images for Emoji Smith application"

  # Cleanup policy to stay within free tier (0.5 GB)
  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-recent-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 3
    }
  }

  depends_on = [google_project_service.artifactregistry]
}

# Output the repository URL for use in CI/CD
output "artifact_registry_url" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.emoji_smith.repository_id}"
}
```

### 4.7 secrets.tf — Secret Manager (without values in Terraform state)

```hcl
# Create secrets as infrastructure, but do NOT create secret versions with plaintext in Terraform.
# Populate secret versions out-of-band using gcloud CLI.

resource "google_secret_manager_secret" "slack_bot_token" {
  secret_id = "emoji-smith-slack-bot-token"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "slack_signing_secret" {
  secret_id = "emoji-smith-slack-signing-secret"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "openai_api_key" {
  secret_id = "emoji-smith-openai-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "emoji-smith-google-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}
```

**Populate secret versions out-of-band (one-time + on rotation):**

```bash
# Run these commands manually after terraform apply
# Each command prompts for the secret value via stdin

echo "YOUR_SLACK_BOT_TOKEN" | gcloud secrets versions add emoji-smith-slack-bot-token --data-file=-
echo "YOUR_SLACK_SIGNING_SECRET" | gcloud secrets versions add emoji-smith-slack-signing-secret --data-file=-
echo "YOUR_OPENAI_API_KEY" | gcloud secrets versions add emoji-smith-openai-api-key --data-file=-
echo "YOUR_GOOGLE_API_KEY" | gcloud secrets versions add emoji-smith-google-api-key --data-file=-
```

### 4.8 iam.tf — Service accounts and IAM bindings

```hcl
# =============================================================================
# Runtime Service Accounts (for Cloud Run services)
# =============================================================================

resource "google_service_account" "webhook_runtime" {
  account_id   = "emoji-smith-webhook"
  display_name = "Emoji Smith - Webhook (Cloud Run)"
  description  = "Runtime service account for the webhook Cloud Run service"

  depends_on = [google_project_service.iam]
}

resource "google_service_account" "worker_runtime" {
  account_id   = "emoji-smith-worker"
  display_name = "Emoji Smith - Worker (Cloud Run)"
  description  = "Runtime service account for the worker Cloud Run service"

  depends_on = [google_project_service.iam]
}

# Service account used by Pub/Sub to invoke the worker via OIDC
resource "google_service_account" "pubsub_push_invoker" {
  account_id   = "emoji-smith-pubsub-invoker"
  display_name = "Emoji Smith - Pub/Sub Push Invoker"
  description  = "Service account for Pub/Sub push subscription OIDC authentication"

  depends_on = [google_project_service.iam]
}

# =============================================================================
# Secret Manager IAM: Allow Cloud Run runtimes to read secrets
# =============================================================================

locals {
  webhook_secret_ids = [
    google_secret_manager_secret.slack_bot_token.secret_id,
    google_secret_manager_secret.slack_signing_secret.secret_id,
  ]

  worker_secret_ids = [
    google_secret_manager_secret.slack_bot_token.secret_id,
    google_secret_manager_secret.openai_api_key.secret_id,
    google_secret_manager_secret.google_api_key.secret_id,
  ]
}

resource "google_secret_manager_secret_iam_member" "webhook_secret_access" {
  for_each  = toset(local.webhook_secret_ids)
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.webhook_runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "worker_secret_access" {
  for_each  = toset(local.worker_secret_ids)
  secret_id = each.value
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker_runtime.email}"
}

# =============================================================================
# Pub/Sub IAM: Allow webhook to publish jobs
# =============================================================================

resource "google_pubsub_topic_iam_member" "webhook_publisher" {
  topic  = google_pubsub_topic.jobs.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.webhook_runtime.email}"
}

# =============================================================================
# Pub/Sub Service Agent IAM (required for OIDC push authentication)
# =============================================================================

# Get the Pub/Sub service agent identity
# IMPORTANT: This requires google-beta provider
resource "google_project_service_identity" "pubsub_agent" {
  provider = google-beta
  project  = var.project_id
  service  = "pubsub.googleapis.com"

  depends_on = [google_project_service.pubsub]
}

# Allow Pub/Sub service agent to create OIDC tokens for push subscriptions
resource "google_service_account_iam_member" "pubsub_token_creator" {
  service_account_id = google_service_account.pubsub_push_invoker.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_project_service_identity.pubsub_agent.email}"
}

# =============================================================================
# Dead Letter Queue IAM: Allow Pub/Sub to publish failed messages
# =============================================================================

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  topic  = google_pubsub_topic.jobs_dlq.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_project_service_identity.pubsub_agent.email}"
}

resource "google_pubsub_subscription_iam_member" "subscription_subscriber_for_dlq" {
  subscription = google_pubsub_subscription.jobs_push.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:${google_project_service_identity.pubsub_agent.email}"
}
```

### 4.9 cloud_run_webhook.tf — Webhook service (public)

```hcl
# =============================================================================
# Cloud Run Webhook Service (Public - accessible by Slack)
# =============================================================================
# IMPORTANT: invoker_iam_disabled requires google-beta provider

resource "google_cloud_run_v2_service" "webhook" {
  provider = google-beta  # Required for invoker_iam_disabled
  name     = "emoji-smith-webhook"
  location = var.region

  # Disable IAM check for invocations - allows Slack to call without Google auth
  invoker_iam_disabled = true

  # Allow all traffic (Slack needs to reach this)
  ingress = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.webhook_runtime.email

    # Scaling settings for free tier optimization
    scaling {
      min_instance_count = 0  # Scale to zero when idle
      max_instance_count = 2  # Limit max instances
    }

    containers {
      image = var.webhook_image

      # Resource limits (keep small for fast cold starts)
      resources {
        limits = {
          cpu    = "1"
          memory = "256Mi"
        }
        cpu_idle = true  # Only charge for CPU during requests
      }

      # Port configuration
      ports {
        container_port = 8080
      }

      # Environment variables from Secret Manager
      env {
        name = "SLACK_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.slack_bot_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "SLACK_SIGNING_SECRET"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.slack_signing_secret.secret_id
            version = "latest"
          }
        }
      }

      # Plain environment variables
      env {
        name  = "PUBSUB_TOPIC"
        value = google_pubsub_topic.jobs.id
      }

      env {
        name  = "PUBSUB_PROJECT"
        value = var.project_id
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      # Startup probe for faster scaling
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 3
        failure_threshold     = 10
      }
    }
  }

  # Traffic routing (100% to latest revision)
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.webhook_secret_access,
  ]
}

output "webhook_url" {
  description = "URL of the webhook Cloud Run service (configure in Slack app settings)"
  value       = google_cloud_run_v2_service.webhook.uri
}
```

### 4.10 cloud_run_worker.tf — Worker service (private)

```hcl
# =============================================================================
# Cloud Run Worker Service (Private - only Pub/Sub can invoke)
# =============================================================================

resource "google_cloud_run_v2_service" "worker" {
  name     = "emoji-smith-worker"
  location = var.region

  # Keep IAM enabled - only Pub/Sub push invoker can call this
  # (invoker_iam_disabled defaults to false)

  # Internal traffic only (Pub/Sub push comes from Google's network)
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.worker_runtime.email

    # Worker processes one job per request to avoid duplicate work on retries
    max_instance_request_concurrency = 1

    # Scaling settings
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    # Timeout for image generation (up to 10 minutes)
    timeout = "600s"

    containers {
      image = var.worker_image

      # Resource limits (needs more memory for image processing)
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
        cpu_idle = true
      }

      ports {
        container_port = 8080
      }

      # Environment variables from Secret Manager
      env {
        name = "SLACK_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.slack_bot_token.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openai_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name  = "LOG_LEVEL"
        value = "INFO"
      }

      # Health check
      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 0
        timeout_seconds       = 3
        period_seconds        = 5
        failure_threshold     = 10
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  depends_on = [
    google_project_service.run,
    google_secret_manager_secret_iam_member.worker_secret_access,
  ]
}

# =============================================================================
# IAM: Allow Pub/Sub push invoker to call the worker
# =============================================================================
# IMPORTANT: Use google_cloud_run_v2_service_iam_binding (not v1)
# The attribute is 'name' not 'service'

resource "google_cloud_run_v2_service_iam_binding" "worker_invoker" {
  project  = var.project_id
  location = google_cloud_run_v2_service.worker.location
  name     = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  members  = ["serviceAccount:${google_service_account.pubsub_push_invoker.email}"]
}

output "worker_url" {
  description = "URL of the worker Cloud Run service (internal only)"
  value       = google_cloud_run_v2_service.worker.uri
}
```

### 4.11 pubsub.tf — Topics and subscriptions

```hcl
# =============================================================================
# Pub/Sub Topics
# =============================================================================

resource "google_pubsub_topic" "jobs" {
  name = "emoji-smith-jobs"

  # Message retention for debugging (7 days)
  message_retention_duration = "604800s"

  depends_on = [google_project_service.pubsub]
}

resource "google_pubsub_topic" "jobs_dlq" {
  name = "emoji-smith-jobs-dlq"

  # Retain dead letters longer for investigation (14 days)
  message_retention_duration = "1209600s"

  depends_on = [google_project_service.pubsub]
}

# =============================================================================
# Pub/Sub Push Subscription
# =============================================================================

resource "google_pubsub_subscription" "jobs_push" {
  name  = "emoji-smith-jobs-push"
  topic = google_pubsub_topic.jobs.id

  # Push configuration with OIDC authentication
  push_config {
    push_endpoint = "${google_cloud_run_v2_service.worker.uri}/pubsub"

    # OIDC token for authenticating to the worker Cloud Run service
    oidc_token {
      service_account_email = google_service_account.pubsub_push_invoker.email
      # Audience defaults to the push endpoint URL, which is correct for Cloud Run
    }

    attributes = {
      x-goog-version = "v1"
    }
  }

  # Acknowledgement deadline: max 600 seconds (10 minutes)
  # Must be long enough for image generation to complete
  ack_deadline_seconds = 600

  # Retry policy for failed deliveries
  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  # Dead letter policy for poison messages
  # Note: max_delivery_attempts must be between 5 and 100
  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.jobs_dlq.id
    max_delivery_attempts = 5
  }

  # Retain unacked messages for 7 days
  message_retention_duration = "604800s"

  # Expiration policy: never expire (empty string)
  expiration_policy {
    ttl = ""
  }

  depends_on = [
    google_cloud_run_v2_service.worker,
    google_cloud_run_v2_service_iam_binding.worker_invoker,
  ]
}

# =============================================================================
# Dead Letter Subscription (for monitoring/debugging)
# =============================================================================

resource "google_pubsub_subscription" "jobs_dlq_pull" {
  name  = "emoji-smith-jobs-dlq-pull"
  topic = google_pubsub_topic.jobs_dlq.id

  # Pull subscription for manual inspection of dead letters
  # No push_config means this is a pull subscription

  ack_deadline_seconds       = 60
  message_retention_duration = "1209600s"  # 14 days

  expiration_policy {
    ttl = ""  # Never expire
  }
}
```

### 4.12 workload_identity.tf — GitHub Actions Workload Identity Federation

```hcl
# =============================================================================
# Workload Identity Pool for GitHub Actions
# =============================================================================
# This enables GitHub Actions to authenticate to GCP without service account keys
# using OIDC token exchange (Workload Identity Federation)

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Workload Identity Pool for GitHub Actions CI/CD"

  depends_on = [
    google_project_service.iam,
    google_project_service.iamcredentials,
    google_project_service.sts,
  ]
}

# =============================================================================
# Workload Identity Pool Provider (GitHub OIDC)
# =============================================================================
# SECURITY: Uses repository_owner_id (numeric) instead of repository_owner (name)
# to prevent GitHub username squatting attacks

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Actions OIDC Provider"
  description                        = "OIDC identity provider for GitHub Actions workflows"

  # Attribute mapping from GitHub OIDC token claims to Google attributes
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.aud"        = "assertion.aud"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # Attribute condition restricts which GitHub repos can authenticate
  # SECURITY: Use repository_owner_id (numeric) to prevent squatting attacks
  attribute_condition = <<-EOT
    assertion.repository_owner_id == "${var.github_repo_owner_id}" &&
    attribute.repository == "${var.github_repo_owner}/${var.github_repo_name}"
  EOT

  # OIDC configuration for GitHub Actions
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# =============================================================================
# CI/CD Service Account
# =============================================================================

resource "google_service_account" "cicd" {
  account_id   = "emoji-smith-cicd"
  display_name = "Emoji Smith - CI/CD"
  description  = "Service account for GitHub Actions deployments"

  depends_on = [google_project_service.iam]
}

# =============================================================================
# Allow GitHub Actions to impersonate the CI/CD service account
# =============================================================================

resource "google_service_account_iam_member" "cicd_workload_identity" {
  service_account_id = google_service_account.cicd.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repo_owner}/${var.github_repo_name}"
}

# =============================================================================
# CI/CD Service Account Permissions
# =============================================================================

# Permission to push images to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cicd_writer" {
  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.emoji_smith.repository_id
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.cicd.email}"
}

# Permission to deploy Cloud Run services
resource "google_project_iam_member" "cicd_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.cicd.email}"
}

# Permission to act as the runtime service accounts (required for Cloud Run deploy)
resource "google_service_account_iam_member" "cicd_act_as_webhook" {
  service_account_id = google_service_account.webhook_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cicd.email}"
}

resource "google_service_account_iam_member" "cicd_act_as_worker" {
  service_account_id = google_service_account.worker_runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.cicd.email}"
}

# =============================================================================
# Outputs for GitHub Actions workflow configuration
# =============================================================================

output "workload_identity_provider" {
  description = "Workload Identity Provider resource name (use in GitHub Actions auth)"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "cicd_service_account_email" {
  description = "CI/CD service account email (use in GitHub Actions auth)"
  value       = google_service_account.cicd.email
}
```

### 4.13 outputs.tf — All outputs

```hcl
# =============================================================================
# Terraform Outputs
# =============================================================================

output "project_id" {
  description = "GCP project ID"
  value       = var.project_id
}

output "region" {
  description = "GCP region"
  value       = var.region
}

# Webhook outputs are defined in cloud_run_webhook.tf
# Worker outputs are defined in cloud_run_worker.tf
# Artifact Registry outputs are defined in artifact_registry.tf
# Workload Identity outputs are defined in workload_identity.tf
```

---

## 5) GitHub Actions CI/CD Pipeline

### 5.1 Workflow file: `.github/workflows/deploy-gcp.yml`

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: your-gcp-project-id  # TODO: Replace with actual project ID
  REGION: us-central1
  WEBHOOK_SERVICE: emoji-smith-webhook
  WORKER_SERVICE: emoji-smith-worker

jobs:
  # ==========================================================================
  # Build and Test
  # ==========================================================================
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Run quality checks
        run: |
          uv run ruff format --check src/ tests/
          uv run ruff check src/ tests/
          uv run mypy src/
          uv run pytest tests/ -q

  # ==========================================================================
  # Build and Push Docker Images (only on main branch)
  # ==========================================================================
  build-images:
    needs: build-and-test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest

    # Required for Workload Identity Federation
    permissions:
      contents: read
      id-token: write

    outputs:
      webhook_image: ${{ steps.build-webhook.outputs.image }}
      worker_image: ${{ steps.build-worker.outputs.image }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/${{ env.PROJECT_NUMBER }}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
          service_account: emoji-smith-cicd@${{ env.PROJECT_ID }}.iam.gserviceaccount.com
          token_format: access_token

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Artifact Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGION }}-docker.pkg.dev
          username: oauth2accesstoken
          password: ${{ steps.auth.outputs.access_token }}

      - name: Build and push webhook image
        id: build-webhook
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.webhook
          push: true
          tags: |
            ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/webhook:${{ github.sha }}
            ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/webhook:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push worker image
        id: build-worker
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile.worker
          push: true
          tags: |
            ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/worker:${{ github.sha }}
            ${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/worker:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Output image tags
        run: |
          echo "webhook_image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/webhook:${{ github.sha }}" >> $GITHUB_OUTPUT
          echo "worker_image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/worker:${{ github.sha }}" >> $GITHUB_OUTPUT

  # ==========================================================================
  # Deploy to Cloud Run (only on main branch)
  # ==========================================================================
  deploy:
    needs: build-images
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest

    permissions:
      contents: read
      id-token: write

    steps:
      - name: Authenticate to Google Cloud
        id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: projects/${{ env.PROJECT_NUMBER }}/locations/global/workloadIdentityPools/github-actions-pool/providers/github-provider
          service_account: emoji-smith-cicd@${{ env.PROJECT_ID }}.iam.gserviceaccount.com

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Deploy webhook service
        run: |
          gcloud run deploy ${{ env.WEBHOOK_SERVICE }} \
            --image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/webhook:${{ github.sha }} \
            --region=${{ env.REGION }} \
            --project=${{ env.PROJECT_ID }}

      - name: Deploy worker service
        run: |
          gcloud run deploy ${{ env.WORKER_SERVICE }} \
            --image=${{ env.REGION }}-docker.pkg.dev/${{ env.PROJECT_ID }}/emoji-smith/worker:${{ github.sha }} \
            --region=${{ env.REGION }} \
            --project=${{ env.PROJECT_ID }}

      - name: Verify deployment
        run: |
          echo "Webhook URL: $(gcloud run services describe ${{ env.WEBHOOK_SERVICE }} --region=${{ env.REGION }} --format='value(status.url)')"
          echo "Worker URL: $(gcloud run services describe ${{ env.WORKER_SERVICE }} --region=${{ env.REGION }} --format='value(status.url)')"
```

### 5.2 Required GitHub Secrets/Variables

Add these to your repository settings:

| Name | Type | Value |
|------|------|-------|
| `PROJECT_NUMBER` | Variable | Your GCP project number (numeric, e.g., `123456789012`) |

> **Note:** No service account keys needed! Workload Identity Federation uses OIDC tokens.

### 5.3 Parallel Pipeline Strategy During Transition

During the transition period (Phases 1-3), maintain **both** pipelines:

1. **Existing AWS pipeline** (`.github/workflows/deploy.yml`):
   - Continues deploying to AWS on every push to main
   - Provides rollback capability
   - Remove only after Phase 4 (decommission AWS)

2. **New GCP pipeline** (`.github/workflows/deploy-gcp.yml`):
   - Add as a new workflow file
   - Can be disabled initially via `if: false` until infrastructure is ready
   - Enable once Terraform apply completes and secrets are populated

**Cutover sequence:**
1. Enable GCP pipeline after Phase 1 (infra ready)
2. Both pipelines run in parallel during Phase 2 (Slack cutover)
3. Monitor GCP for stability during Phase 3
4. Disable/remove AWS pipeline in Phase 4

---

## 6) Application Changes Required (Code Migration Spec)

### 6.1 Replace AWS webhook runtime with Cloud Run runtime

- **Remove Mangum + Lambda handler concerns** for the GCP deployment path.
- Run FastAPI directly (Cloud Run expects the container to listen on `$PORT`).
- Maintain endpoints used by Slack:
  - `POST /slack/events`
  - `POST /slack/interactive`
  - `GET /health`

**Implementation approach:**
- Add a new Cloud Run entrypoint module: `src/emojismith/infrastructure/gcp/webhook_app.py`
  - Create the FastAPI app (reusing existing `create_webhook_api(...)` wiring if possible)
  - Implement publishing to Pub/Sub via a new `PubSubJobQueue` implementing `JobQueueProducer`

### 6.2 Replace SQS publisher with Pub/Sub publisher

**New file:** `src/emojismith/infrastructure/gcp/pubsub_job_queue.py`

```python
"""Pub/Sub implementation of the JobQueueProducer protocol."""

import json
import os
from google.cloud import pubsub_v1

from emojismith.domain.repositories.job_queue_repository import JobQueueProducer


class PubSubJobQueue(JobQueueProducer):
    """Publishes jobs to Google Cloud Pub/Sub."""

    def __init__(self, project_id: str | None = None, topic_id: str | None = None):
        self.project_id = project_id or os.environ["PUBSUB_PROJECT"]
        self.topic_id = topic_id or os.environ["PUBSUB_TOPIC"]
        self._publisher = pubsub_v1.PublisherClient()
        self._topic_path = self._publisher.topic_path(self.project_id, self.topic_id)

    def enqueue_job(self, job: dict) -> str:
        """Publish a job to Pub/Sub and return the message ID."""
        data = json.dumps(job).encode("utf-8")
        future = self._publisher.publish(self._topic_path, data)
        message_id = future.result()
        return message_id
```

**Dependencies to add:** `google-cloud-pubsub>=2.0.0`

### 6.3 Replace worker SQS handler with Pub/Sub push handler

**New file:** `src/emojismith/infrastructure/gcp/worker_app.py`

```python
"""Cloud Run worker application for processing Pub/Sub push messages."""

import base64
import json
import logging
from fastapi import FastAPI, Request, HTTPException

from emojismith.application.services.emoji_service import EmojiService
# Import your wiring/DI setup

app = FastAPI()
logger = logging.getLogger(__name__)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/pubsub")
async def process_pubsub_message(request: Request):
    """
    Handle Pub/Sub push messages.

    Pub/Sub sends messages in this format:
    {
        "message": {
            "data": "<base64-encoded-job-json>",
            "messageId": "...",
            "publishTime": "..."
        },
        "subscription": "projects/.../subscriptions/..."
    }

    Return 2xx for success (message acknowledged).
    Return 5xx for failure (message will be retried).
    """
    try:
        envelope = await request.json()

        if not envelope or "message" not in envelope:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        message = envelope["message"]
        message_id = message.get("messageId", "unknown")

        # Decode the job data
        if "data" not in message:
            raise HTTPException(status_code=400, detail="Missing message data")

        job_data = base64.b64decode(message["data"]).decode("utf-8")
        job = json.loads(job_data)

        logger.info(f"Processing job from message {message_id}: {job.get('type', 'unknown')}")

        # Process the job using your existing service
        # This is where you wire up your DI container
        emoji_service = get_emoji_service()  # Your DI wiring function
        await emoji_service.process_job(job)

        logger.info(f"Successfully processed message {message_id}")
        return {"status": "ok", "messageId": message_id}

    except Exception as e:
        logger.exception(f"Error processing Pub/Sub message: {e}")
        # Return 500 to trigger Pub/Sub retry
        raise HTTPException(status_code=500, detail=str(e))
```

### 6.4 Secrets loading changes

On Cloud Run, secrets are injected as environment variables directly from Secret Manager. Remove any runtime secret-manager fetches.

**Before (AWS):**
```python
secrets = AWSSecretsLoader().load_secrets()
slack_token = secrets["SLACK_BOT_TOKEN"]
```

**After (GCP):**
```python
import os
slack_token = os.environ["SLACK_BOT_TOKEN"]  # Injected by Cloud Run
```

### 6.5 Dockerfile changes

**Dockerfile.webhook** (minimal dependencies):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install only webhook dependencies (no OpenAI, Pillow, etc.)
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY src/ ./src/

# Install the project
RUN uv sync --no-dev

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "emojismith.infrastructure.gcp.webhook_app:app", "--host", "0.0.0.0", "--port", "8080"]
```

**Dockerfile.worker** (full dependencies):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install all dependencies
RUN uv sync --no-dev --no-install-project

# Copy application code
COPY src/ ./src/

# Install the project
RUN uv sync --no-dev

ENV PORT=8080

CMD ["uv", "run", "uvicorn", "emojismith.infrastructure.gcp.worker_app:app", "--host", "0.0.0.0", "--port", "8080"]
```

---

## 7) Migration Execution Plan (Phased)

### Phase 0 — Prep & decisions

**Prerequisites:**
1. Create a new GCP project (or reuse existing) and attach billing
2. Choose region: `us-central1` (recommended for free tier and latency)
3. Get your GitHub organization/user numeric ID:
   ```bash
   gh api users/YOUR_USERNAME --jq .id
   ```
4. Install required tools: `gcloud`, `terraform`, `gh` CLI

**Configuration checklist:**
- [ ] GCP project ID noted
- [ ] GCP project number noted (numeric)
- [ ] GitHub repo owner ID noted (numeric)
- [ ] Billing account attached
- [ ] `gcloud auth login` completed
- [ ] `gcloud auth application-default login` completed

### Phase 1 — Stand up GCP infra (Terraform)

**Step 1.1: Initialize Terraform**

```bash
cd infra_gcp/terraform

# Create terraform.tfvars
cat > terraform.tfvars << EOF
project_id           = "your-project-id"
region               = "us-central1"
github_repo_owner    = "your-github-username"
github_repo_name     = "emoji-smith"
github_repo_owner_id = "12345678"  # Your numeric GitHub ID
EOF

# Initialize Terraform
terraform init
```

**Step 1.2: Apply Terraform (creates all resources except secret values)**

```bash
terraform plan -out=tfplan
terraform apply tfplan
```

**Step 1.3: Populate secrets (one-time manual step)**

```bash
# These commands prompt for each secret value
echo "xoxb-your-slack-bot-token" | gcloud secrets versions add emoji-smith-slack-bot-token --data-file=-
echo "your-slack-signing-secret" | gcloud secrets versions add emoji-smith-slack-signing-secret --data-file=-
echo "sk-your-openai-api-key" | gcloud secrets versions add emoji-smith-openai-api-key --data-file=-
echo "your-google-api-key" | gcloud secrets versions add emoji-smith-google-api-key --data-file=-
```

**Step 1.4: Update GitHub Actions workflow**

1. Add the `PROJECT_NUMBER` variable to GitHub repository settings
2. Update `PROJECT_ID` in the workflow file
3. Commit the new `.github/workflows/deploy-gcp.yml`

**Step 1.5: Verify initial deployment**

```bash
# Check webhook health
WEBHOOK_URL=$(terraform output -raw webhook_url)
curl -s "${WEBHOOK_URL}/health"

# Check worker health (internal only, verify via logs)
gcloud run services logs read emoji-smith-worker --region=us-central1 --limit=10
```

### Phase 2 — Cut over Slack to GCP

**Step 2.1: Update Slack app settings**

1. Go to https://api.slack.com/apps and select your app
2. Update **Event Subscriptions**:
   - Request URL: `{WEBHOOK_URL}/slack/events`
3. Update **Interactivity & Shortcuts**:
   - Request URL: `{WEBHOOK_URL}/slack/interactive`
4. Save changes and verify Slack's URL verification succeeds

**Step 2.2: Test end-to-end**

1. Trigger an emoji generation from Slack
2. Verify the modal opens correctly
3. Submit the form and verify emoji is generated
4. Check Cloud Logging for any errors:
   ```bash
   gcloud run services logs read emoji-smith-webhook --region=us-central1 --limit=50
   gcloud run services logs read emoji-smith-worker --region=us-central1 --limit=50
   ```

### Phase 3 — Parallel run & hardening

**Duration:** 1-7 days

**Monitoring checklist:**
- [ ] Emoji generation works end-to-end
- [ ] No errors in Cloud Logging
- [ ] Pub/Sub dead letter queue is empty
- [ ] Free tier usage within limits (check billing console)

**Keep AWS infra deployed but unused as rollback:**
- Do NOT destroy AWS resources yet
- AWS URLs are the rollback path if GCP fails

### Phase 4 — Decommission AWS

**Only proceed after GCP is stable for several days.**

**Step 4.1: Destroy AWS resources**

```bash
cd infra  # AWS CDK directory
cdk destroy --all
```

**Step 4.2: Remove AWS code from repo**

```bash
# Remove AWS infrastructure
rm -rf infra/

# Remove AWS-specific code
rm -rf src/emojismith/infrastructure/aws/
rm -f src/emojismith/infrastructure/jobs/sqs_job_queue.py

# Remove AWS Dockerfile
rm -f Dockerfile

# Update tests to remove SQS/AWS references
# (manual step - update mocks to use Pub/Sub equivalents)

# Rename GCP infra directory
mv infra_gcp/ infra/
```

**Step 4.3: Update documentation**

- Update README.md with GCP deployment instructions
- Remove AWS references from CLAUDE.md
- Update any architecture diagrams

### Phase 5 — Post-migration cleanup

1. Archive or delete old GitHub Actions workflow for AWS
2. Review and optimize Cloud Run resource limits based on actual usage
3. Set up cost alerts in GCP Console (Budget & Alerts)
4. Add Artifact Registry cleanup job (or verify cleanup policy works)

---

## 8) Rollback Plan

Rollback is quick because Slack is the single entry point:

**During Phases 1-3 (AWS still running):**

1. Go to Slack app settings
2. Change URLs back to AWS endpoints
3. Emoji generation immediately uses AWS again
4. Investigate GCP failure, fix, redeploy, then switch back

**After Phase 4 (AWS destroyed):**

1. Re-deploy AWS infrastructure: `cd infra && cdk deploy`
2. Populate AWS Secrets Manager with secrets
3. Update Slack app URLs to AWS endpoints
4. Fix GCP issues and cut back over

---

## 9) Open Questions / Decisions to Confirm

- [ ] **Idempotency:** Do we need idempotency keys for worker jobs? (Pub/Sub retries can cause duplicates)
- [ ] **Persistence:** Do we want a small persistence layer (Firestore) to store job status for better UX/debug?
- [ ] **Architecture:** Do we keep the strict "dual handler" separation as two Cloud Run services or merge with routing?
- [ ] **Image optimization:** Should we use multi-stage builds to further reduce image size?
- [ ] **Monitoring:** Set up Cloud Monitoring alerts for error rates?

---

## 10) Implementation Checklist for AI Agent

This checklist enables an AI agent to implement the migration in sequence:

### Pre-flight

- [ ] Verify `gcloud` CLI is authenticated
- [ ] Verify `terraform` is installed (>= 1.6.0)
- [ ] Verify GCP project exists and has billing enabled
- [ ] Get GitHub owner numeric ID: `gh api users/OWNER --jq .id`

### Create Terraform files

- [ ] Create `infra_gcp/terraform/` directory structure
- [ ] Create `versions.tf` (Section 4.2)
- [ ] Create `providers.tf` (Section 4.3)
- [ ] Create `variables.tf` (Section 4.4)
- [ ] Create `apis.tf` (Section 4.5)
- [ ] Create `artifact_registry.tf` (Section 4.6)
- [ ] Create `secrets.tf` (Section 4.7)
- [ ] Create `iam.tf` (Section 4.8)
- [ ] Create `cloud_run_webhook.tf` (Section 4.9)
- [ ] Create `cloud_run_worker.tf` (Section 4.10)
- [ ] Create `pubsub.tf` (Section 4.11)
- [ ] Create `workload_identity.tf` (Section 4.12)
- [ ] Create `outputs.tf` (Section 4.13)
- [ ] Create `terraform.tfvars` with actual values

### Create application code

- [ ] Create `src/emojismith/infrastructure/gcp/__init__.py`
- [ ] Create `src/emojismith/infrastructure/gcp/pubsub_job_queue.py` (Section 6.2)
- [ ] Create `src/emojismith/infrastructure/gcp/webhook_app.py` (adapt from existing)
- [ ] Create `src/emojismith/infrastructure/gcp/worker_app.py` (Section 6.3)
- [ ] Add `google-cloud-pubsub>=2.0.0` to `pyproject.toml`

### Create Docker files

- [ ] Create `Dockerfile.webhook` (Section 6.5)
- [ ] Create `Dockerfile.worker` (Section 6.5)

### Create CI/CD pipeline

- [ ] Create `.github/workflows/deploy-gcp.yml` (Section 5.1)
- [ ] Add `PROJECT_NUMBER` variable to GitHub repository settings

### Deploy infrastructure

- [ ] Run `terraform init`
- [ ] Run `terraform plan`
- [ ] Run `terraform apply`
- [ ] Populate secrets with `gcloud secrets versions add`

### Verify deployment

- [ ] Push code to trigger GitHub Actions
- [ ] Verify webhook health endpoint
- [ ] Verify worker receives Pub/Sub messages
- [ ] Update Slack app URLs
- [ ] Test end-to-end emoji generation

---

## Appendix A: Verified Terraform Resource Reference

| Resource | Provider | Key Attributes | Notes |
|----------|----------|----------------|-------|
| `google_cloud_run_v2_service` | `google-beta` (for `invoker_iam_disabled`) | `invoker_iam_disabled`, `template.scaling.min_instance_count` | Use v2 API for latest features |
| `google_cloud_run_v2_service_iam_binding` | `google` | `name` (not `service`), `location`, `role`, `members` | Different from v1 IAM binding |
| `google_pubsub_subscription` | `google` | `push_config.oidc_token`, `dead_letter_policy.max_delivery_attempts` (5-100) | ack_deadline max 600s |
| `google_project_service_identity` | `google-beta` | `service`, `email` attribute | Required for Pub/Sub OIDC |
| `google_iam_workload_identity_pool` | `google` | `workload_identity_pool_id` | No `gcp-` prefix allowed |
| `google_iam_workload_identity_pool_provider` | `google` | `oidc.issuer_uri`, `attribute_mapping`, `attribute_condition` | GitHub issuer: `https://token.actions.githubusercontent.com` |
| `google_secret_manager_secret` | `google` | `replication.auto {}` | Don't store values in Terraform |
