variable "observe_domain" {
  type        = string
  description = "Observe domain"
  default = "observeinc.com"
}

variable "observe_customer" {
  type        = string
  description = "Observe customer id"
}

variable "observe_token" {
  type        = string
  description = "Observe ingest token"
}

variable "eventhub_namespace" {
  type        = string
  description = "Eventhub namespace to use for function"
}

variable "eventhub_name" {
  type        = string
  description = "Eventhub name to use for function"
}

variable "resource_group_name" {
  type        = string
  description = "Eventhub name to use for function"
}

# To be used if "az login" and "azuread_client_config" not used 

# variable "azure_tenant_id" {
#   type        = string
#   description = "Eventhub name to use for function"
# }

# variable "azure_client_id" {
#   type        = string
#   description = "Eventhub name to use for function"
# }

# variable "azure_client_secret" {
#   type        = string
#   description = "Eventhub name to use for function"
# }

variable "timer_func_schedule" {
  type        = string
  description = "Eventhub name to use for function"
  default     = "0 */1 * * * *"
}

variable "timer_func_schedule_vm" {
  type        = string
  description = "Eventhub name to use for function"
  default     = "30 */1 * * * *"
}

variable "location" {
  type        = string
  description = "Eventhub name to use for function"
  default     = "East US"
}