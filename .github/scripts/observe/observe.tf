terraform {
  required_providers {
    observe = {
      source  = "terraform.observeinc.com/observeinc/observe"
      version = ">= 0.13.3"
    }
  }
  required_version = ">= 1.0"
}

# Configure the observe provider
provider "observe" {}

resource "observe_datastream_token" "github_actions_branch_token" {
  datastream = data.observe_datastream.example.oid
  name       = var.branch
}