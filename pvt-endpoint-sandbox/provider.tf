terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.86.0"
    }
  }
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = var.prevent_rg_deletion
    }
  }
  #storage_use_azuread = true 
}


# This requires that the User/Service Principal being used has the associated Storage roles -
# which are added to new Contributor/Owner role-assignments,
# but have not been backported by Azure to existing role-assignments.