# CLAUDE.md - Deployment and CI/CD Guidelines

## Inheritance
- **Extends:** /CLAUDE.md (root)
- **Overrides:** None (CRITICAL RULES cannot be overridden)
- **Scope:** All GitHub Actions workflows, CI/CD pipelines, and deployment processes

## Rules

**Context:** This document provides guidelines for working with CI/CD pipelines, Terraform infrastructure, and deployment processes. Read this when configuring GitHub Actions, deploying infrastructure, or managing the deployment pipeline.

## 🚀 Deployment Philosophy

**Golden Rule:** All deployments happen through CI/CD. Manual deployments are forbidden when CI exists.

## Architecture Overview

### Dual Cloud Run Architecture
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Slack     │────▶│   Webhook    │────▶│   Pub/Sub    │────▶│    Worker    │
│   Events    │     │  Cloud Run   │     │    Topic     │     │  Cloud Run   │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                           │                                            │
                           └────────────────────────────────────────────┘
                                                │
                                        ┌───────▼────────┐
                                        │  GCP Services  │
                                        │ - Secret Mgr   │
                                        │ - Cloud Log    │
                                        │ - Artifact Reg │
                                        └────────────────┘
```

### Why Dual Cloud Run?
- **Webhook Cloud Run**: Responds within Slack's 3-second timeout (public)
- **Worker Cloud Run**: Handles time-consuming image generation (10-15s, private)
- **Better isolation**: Webhook is public, worker only accepts Pub/Sub
- **Scalability**: Pub/Sub provides buffering, retry logic, and dead-letter handling

## CI/CD Pipeline

### GitHub Actions Workflow

Our deployment pipeline runs automatically on push to main:

```yaml
name: Deploy to GCP

on:
  push:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - Code formatting (ruff format)
      - Linting + security scanning (ruff check)
      - Type checking (mypy)
      - Unit tests with coverage

  build-images:
    needs: [build-and-test]
    runs-on: ubuntu-latest
    steps:
      - Authenticate via Workload Identity Federation (keyless)
      - Build Docker images
      - Push to Artifact Registry

  deploy:
    needs: [build-images]
    runs-on: ubuntu-latest
    steps:
      - Deploy webhook Cloud Run service
      - Deploy worker Cloud Run service
```

### Environment Variables

#### Required GitHub Variables (not secrets - use Workload Identity)
```
GCP_PROJECT_ID              # Target GCP project
GCP_PROJECT_NUMBER          # GCP project number
GCP_WORKLOAD_IDENTITY_PROVIDER  # OIDC provider for keyless auth
GCP_CICD_SERVICE_ACCOUNT    # Service account for deployments
```

#### Secrets (stored in GCP Secret Manager, not GitHub)
```
slack-bot-token         # Bot user OAuth token
slack-signing-secret    # Request verification
openai-api-key          # Image generation API
google-api-key          # Gemini API (optional)
```

## Terraform Infrastructure

### Directory Organization
```
terraform/
├── providers.tf            # GCP provider config
├── variables.tf            # Input variables
├── versions.tf             # Terraform version constraints
├── apis.tf                 # Enable required GCP APIs
├── iam.tf                  # Service accounts
├── secrets.tf              # Secret Manager resources
├── pubsub.tf               # Pub/Sub topic & subscription
├── artifact_registry.tf    # Container registry
├── cloud_run_webhook.tf    # Webhook service
├── cloud_run_worker.tf     # Worker service
├── workload_identity.tf    # GitHub Actions OIDC
└── outputs.tf              # Output values
```

### Key Terraform Patterns

#### Cloud Run Service
```hcl
resource "google_cloud_run_v2_service" "webhook" {
  name     = "emoji-smith-webhook"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/emoji-smith/webhook:latest"
      
      env {
        name = "SLACK_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.slack_bot_token.secret_id
            version = "latest"
          }
        }
      }
    }
    
    service_account = google_service_account.webhook.email
  }
}
```

#### Pub/Sub with OIDC Push
```hcl
resource "google_pubsub_subscription" "worker_push" {
  name  = "emoji-smith-worker-push"
  topic = google_pubsub_topic.jobs.name

  push_config {
    push_endpoint = google_cloud_run_v2_service.worker.uri

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.dead_letter.id
    max_delivery_attempts = 5
  }
}
```

#### Workload Identity Federation
```hcl
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}
```

## Local Development

### Running Locally
```bash
# 1. Start local webhook server
python -m src.emojismith.dev_server

# 2. Expose to internet
ngrok http 8000

# 3. Update Slack app URL
# https://api.slack.com/apps/YOUR_APP_ID/event-subscriptions
```

### Docker Development
```bash
# Build webhook container
docker build -f Dockerfile.webhook -t emoji-webhook .

# Build worker container
docker build -f Dockerfile.worker -t emoji-worker .

# Run with environment
docker run -p 8080:8080 \
  -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  emoji-webhook
```

## Deployment Process

### 1. Infrastructure Changes (Manual Terraform)
```bash
cd terraform
terraform plan
terraform apply
```

### 2. Application Deployment (Automatic)
```yaml
# Triggered by merge to main
# No manual steps required
# Monitor in GitHub Actions
```

### 3. Rollback Process
```bash
# Revert commit on main
git revert HEAD
git push origin main

# CI/CD will automatically deploy previous version
```

## Monitoring and Alerts

### Cloud Logging
- Cloud Run request logs
- Application structured logs
- Error aggregation

### Setting Up Alerts (optional)
```hcl
resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "High Error Rate"
  
  conditions {
    display_name = "Error rate > 5%"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      duration        = "300s"
    }
  }
}
```

## Security Best Practices

### Service Account Least Privilege
```hcl
# Webhook only needs to publish to Pub/Sub
resource "google_pubsub_topic_iam_member" "webhook_publisher" {
  topic  = google_pubsub_topic.jobs.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.webhook.email}"
}

# Worker needs to read secrets
resource "google_secret_manager_secret_iam_member" "worker_accessor" {
  secret_id = google_secret_manager_secret.openai_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.worker.email}"
}
```

### Private Worker Service
```hcl
# Worker Cloud Run is NOT publicly accessible
resource "google_cloud_run_v2_service" "worker" {
  # ...
  ingress = "INGRESS_TRAFFIC_INTERNAL_ONLY"
}

# Only Pub/Sub can invoke it
resource "google_cloud_run_service_iam_member" "pubsub_invoker" {
  service  = google_cloud_run_v2_service.worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}
```

## Cost Optimization

### Cloud Run Configuration
- `min_instance_count = 0` (scale to zero)
- Right-size memory (webhook: 256Mi, worker: 512Mi)
- Set appropriate timeout limits

### Free Tier Awareness
- Cloud Run: 2M requests/month, 360K GB-seconds
- Pub/Sub: 10GB messages/month
- Secret Manager: 6 active secret versions, 10K access ops
- Artifact Registry: 500MB storage

## Troubleshooting Deployments

### Common Issues

1. **Workload Identity Auth Failure**
   ```bash
   # Verify the GitHub repository is allowed
   gcloud iam workload-identity-pools providers describe github-provider \
     --workload-identity-pool=github-actions \
     --location=global
   ```

2. **Docker Build Failures**
   - Check Docker daemon is running
   - Ensure sufficient disk space
   - Verify Dockerfile syntax

3. **Cloud Run Timeout**
   - Check Cloud Logging for errors
   - Verify Pub/Sub ack deadline > processing time
   - Review memory allocation

4. **Permission Errors**
   - Check service account bindings
   - Verify secret access
   - Review IAM policies

### Deployment Checklist

Before deploying:
- [ ] All tests passing
- [ ] Security scan clean
- [ ] GitHub variables configured
- [ ] GCP secrets populated
- [ ] Terraform plan reviewed
- [ ] Rollback plan ready

## Emergency Procedures

### Immediate Rollback
```bash
# If deployment causes issues
git revert HEAD --no-edit
git push origin main
```

### Disable Webhook
```bash
# Set Cloud Run to 0 max instances
gcloud run services update emoji-smith-webhook \
  --max-instances=0 \
  --region=us-central1
```

### Purge Dead Letter Queue
```bash
# View dead letter messages
gcloud pubsub subscriptions pull emoji-smith-dlq-sub --auto-ack --limit=100
```

## Quick Reference

**Terraform Commands:**
```bash
cd terraform

# Preview changes
terraform plan

# Apply changes
terraform apply

# Destroy (dev only!)
terraform destroy
```

**Never:**
- Deploy manually to production
- Skip CI/CD pipeline
- Store secrets in Terraform state or GitHub
- Commit secrets to repository
- Ignore failed deployments
- Make worker Cloud Run public
