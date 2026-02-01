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
# Observability IAM: Allow runtimes to write traces + metrics
# =============================================================================

resource "google_project_iam_member" "webhook_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.webhook_runtime.email}"

  depends_on = [google_project_service.cloudtrace]
}

resource "google_project_iam_member" "worker_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.worker_runtime.email}"

  depends_on = [google_project_service.cloudtrace]
}

resource "google_project_iam_member" "webhook_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.webhook_runtime.email}"

  depends_on = [google_project_service.monitoring]
}

resource "google_project_iam_member" "worker_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.worker_runtime.email}"

  depends_on = [google_project_service.monitoring]
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
