
terraform {
  backend "azurerm" {}
  required_providers {
    observe = {
      source  = "terraform.observeinc.com/observeinc/observe"
      version = ">= 0.13.3"
    }
  }
  required_version = ">= 1.0"
}


########  OBSERVE TOKEN SETUP ########
############################################

# Uses Github Actions Environment Variables for below 
# OBSERVE_CUSTOMER
# OBSERVE_DOMAIN
# OBSERVE_USER_EMAIL
# OBSERVE_USER_PASSWORD 


data "observe_workspace" "default" {
  name = "Default"
}

data "observe_datastream" "azure" {
  workspace = data.observe_workspace.default.oid
  name      = "Azure"
}

data "observe_dataset" "azure" {
  workspace = data.observe_workspace.default.oid
  name      = "Azure"
}

#Create a new token with branch name under "Azure" Datastream 
resource "observe_datastream_token" "github_actions_branch_token" {
  datastream = data.observe_datastream.azure.oid
  name       = var.branch
}
#############################################


##  AZURE TF COLLECTION ## 
#############################################
module "terraform-azure-collection" {
  source                  = "../../"
  observe_customer        = var.observe_customer
  observe_domain          = var.observe_domain
  location                = var.location
  observe_token           = observe_datastream_token.github_actions_branch_token.secret
  function_app_debug_logs = true
}

##############################################