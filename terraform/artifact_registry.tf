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
