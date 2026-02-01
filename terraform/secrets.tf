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
