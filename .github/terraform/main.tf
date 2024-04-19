module "observe" {
  source = "./observe/"
  branch = var.branch
}


module "terraform-azure-collection" {
  source           = "../../"
  observe_customer = var.observe_customer
  observe_domain   = var.observe_domain
  location         = var.location
  observe_token    = module.observe.observe_token #Reference Output of observe module token value as input to token for collection

}

terraform {
  backend "azurerm" {
    resource_group_name = "rg-terraform-github-actions-state"
    storage_account_name = "citeststfazurecollection"
    container_name = "tfstate"
    key = var.branch + "/.tfstate"
  }
}

