variable "branch" {
  type        = string
  description = "Github Action Branch Name. This will set Observe Datastream Token Name"
}

variable "observe_customer" {
  type        = string
  description = "Observe customer id"
}

variable "observe_domain" {
  type        = string
  description = "Observe domain"
  default     = "observeinc.com"
}

variable "location" {
  type        = string
  description = "Azure Location to deploy resources"
  default     = "eastus"
}
