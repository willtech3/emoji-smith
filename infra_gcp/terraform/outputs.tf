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
