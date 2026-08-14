output "service_url" {
  description = "URL to access the UnifAI service."
  value       = module.unifai.service_url
}

output "health_check_url" {
  description = "URL to the UnifAI health check endpoint."
  value       = module.unifai.health_check_url
}
