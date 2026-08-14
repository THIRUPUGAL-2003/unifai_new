output "service_name" {
  description = "Name of the Cloud Run service."
  value       = google_cloud_run_v2_service.unifai.name
}

output "service_url" {
  description = "URL to access the UnifAI service."
  value = (
    var.domain_name != null
    ? "https://${var.domain_name}"
    : google_cloud_run_v2_service.unifai.uri
  )
}

output "health_check_url" {
  description = "URL to the UnifAI health check endpoint."
  value = (
    var.domain_name != null
    ? "https://${var.domain_name}${var.health_check_path}"
    : "${google_cloud_run_v2_service.unifai.uri}${var.health_check_path}"
  )
}
