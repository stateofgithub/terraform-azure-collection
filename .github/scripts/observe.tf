# Configure the observe provider
provider "observe" {}

# Look up existing workspace 
data "observe_workspace" "default" {
  name = "Default"
}