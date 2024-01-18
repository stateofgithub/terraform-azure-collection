# variable "storage_account_name" {
#   type        = string
# }

# variable "resource_group_name" {
#   type        = string
# }

variable "resource_group_location" {
  type        = string
  default = "westus2"
}


variable "prevent_rg_deletion" {
  type        = bool
  default     = true
  description = "Prevent resource group deletion if resource group is not empty.  Defaults to true."
}

# variable "account_tier" {
#   type        = string
# }

# variable "account_replication_type" {
#   type        = string
# }


# variable "applicationname" {
#   type        = string
# }

# variable "environment" {
#   type        = string
# }