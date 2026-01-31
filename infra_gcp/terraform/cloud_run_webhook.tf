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
        value = google_pubsub_topic.jobs.name
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
