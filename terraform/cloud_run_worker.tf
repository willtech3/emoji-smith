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
