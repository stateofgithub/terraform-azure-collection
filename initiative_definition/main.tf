data "azurerm_subscription" "primary" { }

resource "azurerm_management_group_policy_assignment" "observe_policy_assignment" {
  name                 = "observe-policy-${var.location}"
  policy_definition_id = var.policy_set
  management_group_id  = var.management_group_id
  location = var.location

  identity {
    type = "SystemAssigned"
  }

  parameters = <<PARAMETERS
            {
            "azureRegions": {"value": ["${var.location}"]},
            "eventHubName": {"value": "${var.eventhub}"},
            "eventHubRuleId" : {"value": "${var.eventhub_key}"}
            }
  PARAMETERS
}

resource "azurerm_role_assignment" "observe_role_assignment" {
  scope                = var.management_group_id
  role_definition_name = "Contributor"
  principal_id         = azurerm_management_group_policy_assignment.observe_policy_assignment.identity[0].principal_id
}