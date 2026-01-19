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
