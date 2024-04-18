terraform {
  required_providers {
    observe = {
      source  = "terraform.observeinc.com/observeinc/observe"
      version = ">= 0.13.3"
    }
  }
  required_version = ">= 1.0"
}


data "observe_workspace" "default" {
  name = "Default"
}

data "observe_datastream" "azure" {
  workspace = data.observe_workspace.default.oid
  name      = "Azure"
}

resource "observe_datastream_token" "github_actions_branch_token" {
  datastream = data.observe_datastream.azure.oid
  name       = var.branch
}