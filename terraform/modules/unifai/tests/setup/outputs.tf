output "service_url" {
  value = module.unifai.service_url
}

output "health_check_url" {
  value = module.unifai.health_check_url
}

output "config_json" {
  value     = module.unifai.config_json
  sensitive = true
}
