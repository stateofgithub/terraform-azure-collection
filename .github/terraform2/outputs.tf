
output "observe_token_id" {
  description = "Observe Token ID for Ephemeral Branch"
  value       = observe_datastream_token.github_actions_branch_token.id
}

output "azure_dataset_id" {
  description = "Azure Dataset Id"
  value       = data.observe_dataset.azure.id
} 