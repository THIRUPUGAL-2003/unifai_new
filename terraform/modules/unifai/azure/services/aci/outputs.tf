output "container_group_name" {
  description = "Name of the Azure Container Group."
  value       = azurerm_container_group.unifai.name
}

output "fqdn" {
  description = "FQDN of the container group."
  value       = azurerm_container_group.unifai.fqdn
}

output "ip_address" {
  description = "Public IP address of the container group."
  value       = azurerm_container_group.unifai.ip_address
}

output "service_url" {
  description = "URL to access the UnifAI service."
  value       = "http://${azurerm_container_group.unifai.fqdn}:${var.container_port}"
}

output "health_check_url" {
  description = "URL to the UnifAI health check endpoint."
  value       = "http://${azurerm_container_group.unifai.fqdn}:${var.container_port}${var.health_check_path}"
}
