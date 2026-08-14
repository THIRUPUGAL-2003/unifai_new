# =============================================================================
# AWS EKS Service Module — Outputs
# =============================================================================

output "cluster_name" {
  description = "Name of the EKS cluster."
  value       = var.create_cluster ? aws_eks_cluster.this[0].name : null
}

output "cluster_endpoint" {
  description = "Endpoint URL of the EKS cluster API server."
  value       = var.create_cluster ? aws_eks_cluster.this[0].endpoint : null
}

output "namespace" {
  description = "Kubernetes namespace where UnifAI is deployed."
  value       = kubernetes_namespace.unifai.metadata[0].name
}

output "service_name" {
  description = "Name of the Kubernetes service exposing UnifAI."
  value       = kubernetes_service.unifai.metadata[0].name
}

output "service_url" {
  description = "Internal cluster URL for the UnifAI service."
  value       = "http://${kubernetes_service.unifai.metadata[0].name}.${kubernetes_namespace.unifai.metadata[0].name}.svc.cluster.local"
}

output "health_check_url" {
  description = "Internal cluster URL for the UnifAI health check endpoint."
  value       = "http://${kubernetes_service.unifai.metadata[0].name}.${kubernetes_namespace.unifai.metadata[0].name}.svc.cluster.local${var.health_check_path}"
}
