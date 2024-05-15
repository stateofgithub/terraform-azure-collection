# NOTE: Azure Functions Core Tools must be installed locally
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Cmacos%2Ccsharp%2Cportal%2Cbash#install-the-azure-functions-core-tools
locals {
  is_windows    = substr(pathexpand("~"), 0, 1) == "/" ? false : true
  sleep_command = local.is_windows == true ? "Start-Sleep" : "sleep"
  region        = lookup(var.location_abbreviation, var.location, "none-found")
  keyvault_name = "${local.region}${var.observe_customer}${local.sub}"
  sub           = substr(data.azurerm_subscription.primary.subscription_id, -8, -1)
}

# Obtains current client config from az login, allowing terraform to run.
data "azuread_client_config" "current" {}

# Creates the alias of your Subscription to be used for association below.
data "azurerm_subscription" "primary" {}

# https://petri.com/understanding-azure-app-registrations/#:~:text=Azure%20App%20registrations%20are%20an,to%20use%20an%20app%20registration.
resource "azuread_application" "observe_app_registration" {
  display_name = "observeApp-${var.observe_customer}-${var.location}-${local.sub}"
  owners       = [data.azuread_client_config.current.object_id]
}

# Creates an auth token that is used by the app to call APIs.
resource "azuread_application_password" "observe_password" {
  application_id = azuread_application.observe_app_registration.id
}

# Creates a Service "Principal" for the "observe" app.
resource "azuread_service_principal" "observe_service_principal" {
  client_id = azuread_application.observe_app_registration.client_id
}

resource "azurerm_key_vault" "key_vault" {
  name                = local.keyvault_name
  location            = var.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  tenant_id           = data.azuread_client_config.current.tenant_id

  sku_name = "standard"
}

resource "azurerm_key_vault_access_policy" "user" {
  key_vault_id = azurerm_key_vault.key_vault.id
  tenant_id    = data.azuread_client_config.current.tenant_id
  object_id    = data.azuread_client_config.current.object_id


  secret_permissions = [
    "Backup",
    "Restore",
    "Get",
    "Set",
    "List",
    "Delete",
    "Purge",
  ]
}

resource "azurerm_key_vault_access_policy" "app" {
  key_vault_id = azurerm_key_vault.key_vault.id
  tenant_id    = data.azuread_client_config.current.tenant_id
  object_id    = lookup(azurerm_linux_function_app.observe_collect_function_app.identity[0], "principal_id")


  secret_permissions = [
    "Backup",
    "Restore",
    "Get",
    "Set",
    "List",
    "Delete",
    "Purge",
  ]
}

resource "azurerm_key_vault_secret" "observe_token" {
  name         = "observe-token"
  value        = var.observe_token
  key_vault_id = azurerm_key_vault.key_vault.id

  # Required so the user running this can get the result of the call.
  depends_on = [
    azurerm_key_vault_access_policy.user,
  ]
}

resource "azurerm_key_vault_secret" "observe_password" {
  name         = "observe-password"
  value        = azuread_application_password.observe_password.value
  key_vault_id = azurerm_key_vault.key_vault.id

  # Required so the user running this can get the result of the call.
  depends_on = [
    azurerm_key_vault_access_policy.user,
  ]
}


# Assigns the created service principal a role in current Azure Subscription.
# https://learn.microsoft.com/en-us/azure/azure-monitor/roles-permissions-security#monitoring-reader
# https://learn.microsoft.com/en-us/azure/azure-monitor/roles-permissions-security#security-considerations-for-monitoring-data
resource "azurerm_role_assignment" "observe_role_assignment" {
  scope                = data.azurerm_subscription.primary.id
  role_definition_name = "Monitoring Reader"
  principal_id         = azuread_service_principal.observe_service_principal.object_id
}

resource "azurerm_resource_group" "observe_resource_group" {
  name     = "observeResources-${var.observe_customer}-${var.location}-${local.sub}"
  location = var.location
}

#
resource "azurerm_eventhub_namespace" "observe_eventhub_namespace" {
  name                = local.keyvault_name
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  sku                 = "Standard"
  capacity            = 2

  tags = {
    created_by = "Observe Terraform"
  }
}

resource "azurerm_eventhub" "observe_eventhub" {
  name                = "observeEventHub-${var.observe_customer}-${var.location}-${local.sub}"
  namespace_name      = azurerm_eventhub_namespace.observe_eventhub_namespace.name
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  partition_count     = 32
  message_retention   = 7
}

resource "azurerm_eventhub_authorization_rule" "observe_eventhub_access_policy" {
  name                = "observeSharedAccessPolicy-${var.observe_customer}-${var.location}-${local.sub}"
  namespace_name      = azurerm_eventhub_namespace.observe_eventhub_namespace.name
  eventhub_name       = azurerm_eventhub.observe_eventhub.name
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  listen              = true
  send                = false
  manage              = false
}

resource "azurerm_service_plan" "observe_service_plan" {
  name                = "observeServicePlan-${var.observe_customer}${var.location}-${local.sub}"
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_storage_account" "observe_storage_account" {
  name                     = lower("${var.observe_customer}${local.region}${local.sub}")
  resource_group_name      = azurerm_resource_group.observe_resource_group.name
  location                 = azurerm_resource_group.observe_resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Probably want to use ZRS when we got prime time
}

resource "azurerm_storage_container" "observe_storage_container" {
  name                  = lower("container${var.observe_customer}${local.region}-${local.sub}")
  storage_account_name  = azurerm_storage_account.observe_storage_account.name
  container_access_type = "private"
}

resource "azurerm_linux_function_app" "observe_collect_function_app" {
  name                = "observeApp-${var.observe_customer}-${var.location}-${local.sub}"
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  service_plan_id     = azurerm_service_plan.observe_service_plan.id

  storage_account_name       = azurerm_storage_account.observe_storage_account.name
  storage_account_access_key = azurerm_storage_account.observe_storage_account.primary_access_key

  app_settings = {
    WEBSITE_RUN_FROM_PACKAGE                      = var.func_url
    AzureWebJobsDisableHomepage                   = true
    OBSERVE_DOMAIN                                = var.observe_domain
    OBSERVE_CUSTOMER                              = var.observe_customer
    OBSERVE_TOKEN                                 = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.observe_token.id})"
    AZURE_TENANT_ID                               = data.azuread_client_config.current.tenant_id
    AZURE_CLIENT_ID                               = azuread_application.observe_app_registration.client_id
    AZURE_CLIENT_SECRET                           = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.observe_password.id})"
    AZURE_CLIENT_LOCATION                         = lower(replace(var.location, " ", ""))
    timer_resources_func_schedule                 = var.timer_resources_func_schedule
    timer_vm_metrics_func_schedule                = var.timer_vm_metrics_func_schedule
    EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_NAME       = azurerm_eventhub.observe_eventhub.name
    EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_CONNECTION = "${azurerm_eventhub_authorization_rule.observe_eventhub_access_policy.primary_connection_string}"
    # Pending resolution of https://github.com/hashicorp/terraform-provider-azurerm/issues/18026
    # APPINSIGHTS_INSTRUMENTATIONKEY = azurerm_application_insights.observe_insights.instrumentation_key 
  }

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.9"
    }
  }
}

#### Event Hub Debug 
data "azurerm_eventhub_namespace_authorization_rule" "root_namespace_access_policy" {
  name                = "RootManageSharedAccessKey"
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  namespace_name      = azurerm_eventhub_namespace.observe_eventhub_namespace.name
}

resource "azurerm_monitor_diagnostic_setting" "observe_collect_function_app" {
  count                          = var.function_app_debug_logs ? 1 : 0
  name                           = "observeAppDiagnosticSetting-${var.observe_customer}-${var.location}-${local.sub}"
  target_resource_id             = azurerm_linux_function_app.observe_collect_function_app.id
  eventhub_name                  = azurerm_eventhub.observe_eventhub.name
  eventhub_authorization_rule_id = data.azurerm_eventhub_namespace_authorization_rule.root_namespace_access_policy.id
  enabled_log {
    category = "FunctionAppLogs"
  }
  metric {
    category = "AllMetrics"
  }
}



# Pending resolution of https://github.com/hashicorp/terraform-provider-azurerm/issues/18026
# resource "azurerm_application_insights" "observe_insights" {
#   name                = "observeApplicationInsights"
#   location            = azurerm_resource_group.observe_resource_group.location
#   resource_group_name = azurerm_resource_group.observe_resource_group.name
#   application_type    = "web"
# }
