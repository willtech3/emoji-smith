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
