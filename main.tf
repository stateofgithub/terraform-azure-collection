module "collection" {
  for_each = toset(var.location)
  source   = "./collection"

  observe_customer               = var.observe_customer
  observe_token                  = var.observe_token
  observe_domain                 = var.observe_domain
  timer_resources_func_schedule  = var.timer_resources_func_schedule
  timer_vm_metrics_func_schedule = var.timer_vm_metrics_func_schedule
  location                       = each.value


}
module "policy" {
  source = "./policy_definition"
}

module "policy_assignment" {
  source = "./initiative_definition"

  for_each = toset(var.location)

  location            = each.value
  management_group_id = module.policy.management_group.id
  policy_set          = module.policy.policy_set
  eventhub            = module.collection[each.key].eventhubs.id
  eventhub_key        = "${trimsuffix(module.collection[each.key].eventhub_keys.id, element(split("/", module.collection[each.key].eventhub_keys.id), length(split("/", module.collection[each.key].eventhub_keys.id)) - 1))}rootmanagesharedaccesskey"
}
