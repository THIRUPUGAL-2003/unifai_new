# =============================================================================
# ACI Service Module - Azure Container Instances for UnifAI
# =============================================================================

locals {
  # Convert CPU millicores to ACI decimal cores (e.g. 500 -> 0.5, 1000 -> 1.0)
  cpu_cores = var.cpu >= 100 ? var.cpu / 1000 : var.cpu

  # Convert memory MB to GB for ACI (e.g. 1024 -> 1.0, 2048 -> 2.0)
  memory_gb = var.memory / 1024
}

# =============================================================================
# Container Group
# =============================================================================

resource "azurerm_container_group" "unifai" {
  name                = "${var.name_prefix}-aci"
  location            = var.region
  resource_group_name = var.resource_group_name
  os_type             = "Linux"
  ip_address_type     = "Public"
  dns_name_label      = var.name_prefix
  tags                = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  container {
    name   = "unifai"
    image  = var.image
    cpu    = local.cpu_cores
    memory = local.memory_gb

    ports {
      port     = var.container_port
      protocol = "TCP"
    }

    # Config injected as secure env var, written to file via command override
    secure_environment_variables = {
      UNIFAI_CONFIG = var.config_json
    }

    # Write config from env var to file, then start UnifAI
    commands = [
      "/bin/sh",
      "-c",
      "if [ -n \"$UNIFAI_CONFIG\" ]; then printf '%s' \"$UNIFAI_CONFIG\" > /app/data/config.json; else echo 'ERROR: UNIFAI_CONFIG not set' >&2 && exit 1; fi && exec /app/docker-entrypoint.sh /app/main",
    ]

    liveness_probe {
      http_get {
        path = var.health_check_path
        port = var.container_port
      }
      initial_delay_seconds = 30
      period_seconds        = 10
    }
  }
}
