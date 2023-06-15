terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      #version = "=3.0.0"
      version = ">=3.0.0"
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
}
