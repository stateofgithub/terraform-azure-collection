# Obtains current client config from az login, allowing terraform to run.
data "azuread_client_config" "current" { }

# Creates the alias of your Subscription to be used for association below.
data "azurerm_subscription" "primary" { }

# Registers a required Application in Azure Active Directory
# It's essentially a service that assigns the user as the owner of the application.
# The application inherits the credentials of the user who ran terraform.  
#   Note: some users may want to use a service account instead.

resource "azuread_application" "observe_app_registration" {
  display_name = "observe"
  owners = [data.azuread_client_config.current.object_id]
}

# Creates an auth token that is used by the app to call APIs.
resource "azuread_application_password" "observe_password" {
  application_object_id = azuread_application.observe_app_registration.object_id
}

# Creates a Service "Principal" for the "observe" app.
resource "azuread_service_principal" "observe_service_principal" {
  application_id = azuread_application.observe_app_registration.application_id
}

# Assigns the created service principal a role in current Azure Subscription.
resource "azurerm_role_assignment" "observe_role_assignment" {
  scope                = data.azurerm_subscription.primary.id
  role_definition_name = "Monitoring Reader"
  principal_id         = azuread_service_principal.observe_service_principal.object_id
}

resource "azurerm_resource_group" "observe_resource_group" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_eventhub_namespace" "observe_eventhub_namespace" {
  name                = var.eventhub_namespace
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  sku                 = "Basic"
  capacity            = 4

  tags = {
    created_by = "Observe Terraform"
  }
}

resource "azurerm_eventhub" "observe_eventhub" {
  name                = var.eventhub_name
  namespace_name      = azurerm_eventhub_namespace.observe_eventhub_namespace.name
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  partition_count     = 4
  message_retention   = 1
}

resource "azurerm_eventhub_authorization_rule" "observe_eventhub_access_policy" {
  name                = "observeSharedAccessPoicy"
  namespace_name      = azurerm_eventhub_namespace.observe_eventhub_namespace.name
  eventhub_name       = azurerm_eventhub.observe_eventhub.name
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  listen              = true
  send                = false
  manage              = false
}

resource "azurerm_service_plan" "observe_service_plan" {
  name                = "observe-service-plan"
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  os_type             = "Linux"
  sku_name            = "Y1"
}

resource "azurerm_storage_account" "observe_storage_account" {
  name                     = "observeterraformstorage"
  resource_group_name      = azurerm_resource_group.observe_resource_group.name
  location                 = azurerm_resource_group.observe_resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Probably want to use ZRS when we got prime time
}

resource "azurerm_storage_container" "observe_storage_container" {
  name                  = "observe-collection"
  storage_account_name  = azurerm_storage_account.observe_storage_account.name
  container_access_type = "private"
}

resource "azurerm_linux_function_app" "observe_collect_function" {
  name                = "observe-collection-${var.observe_customer}-${azurerm_resource_group.observe_resource_group.location}"
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  service_plan_id     = azurerm_service_plan.observe_service_plan.id

  storage_account_name       = azurerm_storage_account.observe_storage_account.name
  storage_account_access_key = azurerm_storage_account.observe_storage_account.primary_access_key

  app_settings = {
    WEBSITE_RUN_FROM_PACKAGE = 1
    AzureWebJobsDisableHomepage = true
    OBSERVE_DOMAIN = var.observe_domain
    OBSERVE_CUSTOMER = var.observe_customer
    OBSERVE_TOKEN = var.observe_token
    AZURE_TENANT_ID = data.azuread_client_config.current.tenant_id
    AZURE_CLIENT_ID = azuread_application.observe_app_registration.application_id
    AZURE_CLIENT_SECRET = azuread_application_password.observe_password.value
    timer_resources_func_schedule = var.timer_func_schedule
    timer_vm_metrics_func_schedule = var.timer_func_schedule_vm
    EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_NAME = var.eventhub_name
    EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_CONNECTION = "${azurerm_eventhub_authorization_rule.observe_eventhub_access_policy.primary_connection_string}"
  }

  site_config {
      application_stack  {
        python_version = "3.9"
      }
  }
}

# NOTE: Azure Functions Core Tools must be installed locally
# https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Cmacos%2Ccsharp%2Cportal%2Cbash#install-the-azure-functions-core-tools
locals {
    publish_code_command = "cd ObserveFunctionApp && func azure functionapp publish ${azurerm_linux_function_app.observe_collect_function.name}"
    # pip_install_command  =  "pip install --target='./ObserveFunctionApp/.python_packages/lib/site-packages' -r ./ObserveFunctionApp/requirements.txt --platform manylinux1_x86_64 --only-binary=:all:"
}

resource "null_resource" "function_app_publish" {
  provisioner "local-exec" {
    command = local.publish_code_command
  }
  depends_on = [
    local.publish_code_command,
    azurerm_linux_function_app.observe_collect_function
    ]
  triggers = {
    publish_code_command = local.publish_code_command
  }
}