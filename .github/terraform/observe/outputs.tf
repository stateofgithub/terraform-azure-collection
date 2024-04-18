output "observe_token" {
  description = "Observe Token for Ephemeral Branch"
  value       = observe_datastream_token.github_actions_branch_token.secret
  sensitive   = true
}