output "eventhub_name" {
  description = "Eventhub name used for Observe collection."
  value       = azurerm_eventhub.observe_eventhub.name
}

output "eventhub_namespace_id" {
  description = "Resource ID of the eventhub namespace used for Observe collection."
  value       = azurerm_eventhub_namespace.observe_eventhub_namespace.id
}
