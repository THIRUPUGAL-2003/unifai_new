output "cluster_name" {
  description = "Name of the GKE cluster."
  value       = try(google_container_cluster.unifai[0].name, null)
}

output "cluster_endpoint" {
  description = "Endpoint of the GKE cluster."
  value       = try(google_container_cluster.unifai[0].endpoint, null)
}

output "namespace" {
  description = "Kubernetes namespace where UnifAI is deployed."
  value       = kubernetes_namespace.unifai.metadata[0].name
}

output "service_name" {
  description = "Name of the Kubernetes service."
  value       = kubernetes_service.unifai.metadata[0].name
}

output "ingress_ip" {
  description = "Static IP address of the Ingress (if domain_name is set)."
  value       = try(google_compute_global_address.unifai[0].address, null)
}

output "service_url" {
  description = "URL to access the UnifAI service."
  value = (
    var.domain_name != null
    ? "http://${var.domain_name}"
    : "http://${kubernetes_service.unifai.metadata[0].name}.${kubernetes_namespace.unifai.metadata[0].name}.svc.cluster.local"
  )
}

output "health_check_url" {
  description = "URL to the UnifAI health check endpoint."
  value = (
    var.domain_name != null
    ? "http://${var.domain_name}${var.health_check_path}"
    : "http://${kubernetes_service.unifai.metadata[0].name}.${kubernetes_namespace.unifai.metadata[0].name}.svc.cluster.local${var.health_check_path}"
  )
}
