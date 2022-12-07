variable "observe_customer" {
  type        = string
  description = "Observe customer id"
}

variable "observe_token" {
  type        = string
  description = "Observe ingest token"
}

variable "observe_domain" {
  type        = string
  description = "Observe domain"
  default = "observeinc.com"
}

# Based on NCRONTAB Expressions
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=in-process&pivots=programming-language-csharp#ncrontab-expressions

variable "timer_resources_func_schedule" {
  type        = string
  description = "Eventhub name to use for resources function"
  default     = "0 */10 * * * *"
}

variable "timer_vm_metrics_func_schedule" {
  type        = string
  description = "Eventhub name to use for vm metrics function"
  default     = "30 */5 * * * *"
}

# Use Regional Display Name for value
# https://azuretracks.com/2021/04/current-azure-region-names-reference/

variable "location" {
  type        = string
  description = "Azure Location to deploy resources"
  default     = "East US"
}
