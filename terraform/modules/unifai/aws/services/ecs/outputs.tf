output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = local.cluster_name
}

output "service_name" {
  description = "Name of the ECS service."
  value       = aws_ecs_service.unifai.name
}

output "task_definition_arn" {
  description = "ARN of the ECS task definition."
  value       = aws_ecs_task_definition.unifai.arn
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer (if created)."
  value       = var.create_load_balancer ? aws_lb.unifai[0].dns_name : null
}

output "service_url" {
  description = "URL to access the UnifAI service."
  value       = var.create_load_balancer ? "http://${aws_lb.unifai[0].dns_name}" : null
}

output "health_check_url" {
  description = "URL to the UnifAI health check endpoint."
  value       = var.create_load_balancer ? "http://${aws_lb.unifai[0].dns_name}${var.health_check_path}" : null
}
