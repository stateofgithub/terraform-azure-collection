terraform {
  backend "azurerm" {
    resource_group_name = "rg-terraform-github-actions-state"
    storage_account_name = "citeststfazurecollection"
    container_name       = "tfstate"
    key                  = "${{ steps.extract_branch.outputs.branch }}/.tfstate"
  }
}