output "namespace" {
  description = "Kubernetes namespace where UnifAI is deployed."
  value       = kubernetes_namespace_v1.unifai.metadata[0].name
}

output "service_name" {
  description = "Name of the Kubernetes service."
  value       = kubernetes_service_v1.unifai.metadata[0].name
}

output "service_url" {
  description = "URL to access the UnifAI service."
  value = (
    var.domain_name != null
    ? "http://${var.domain_name}"
    : "http://${kubernetes_service_v1.unifai.metadata[0].name}.${kubernetes_namespace_v1.unifai.metadata[0].name}.svc.cluster.local"
  )
}

output "health_check_url" {
  description = "URL to the UnifAI health check endpoint."
  value = (
    var.domain_name != null
    ? "http://${var.domain_name}/health"
    : "http://${kubernetes_service_v1.unifai.metadata[0].name}.${kubernetes_namespace_v1.unifai.metadata[0].name}.svc.cluster.local/health"
  )
}
