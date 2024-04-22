
output "observe_token_id" {
  description = "Observe Token ID for Ephemeral Branch"
  value       = module.observe.observe_token_id
}

output "azure_datastream_id" {
  description = "Azure Datastream"
  value       = module.observe.azure_datastream_id
} 