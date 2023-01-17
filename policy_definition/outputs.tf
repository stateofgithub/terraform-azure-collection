output "policy_definitions" {
  value = azurerm_policy_definition.policy
}

output "management_group" {
  value = azurerm_management_group.observe_management_group
}

output "policy_set" {
  value = azurerm_policy_set_definition.observe_policy.id
}