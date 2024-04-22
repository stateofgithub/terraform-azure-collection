output "observe_token" {
  description = "Observe Token for Ephemeral Branch"
  value       = observe_datastream_token.github_actions_branch_token.secret
  sensitive   = true
}

output "observe_token_id" {
  description = "Observe Token ID for Ephemeral Branch"
  value       = observe_datastream_token.github_actions_branch_token.id
}

output "azure_datastream_id" {
  description = "Azure Datastream"
  value       = data.observe_datastream.azure.id
} 