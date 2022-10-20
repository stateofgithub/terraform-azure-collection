### TODO:
#   - set up service insights automatically
#   - break out into separate files to make more readable
#   - automate configuring resources sending data to event hub
#   - do we still need a storage blob if we are deploying through zip?

resource "azurerm_resource_group" "observe_resource_group" {
  name     = var.resource_group_name
  location = "East US"
}

resource "azurerm_eventhub_namespace" "observe_eventhub_namespace" {
  name                = var.eventhub_namespace
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  sku                 = "Basic"

  # zone_redundant = true
  capacity            = 1

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
  sku_name            = "S1"
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

data "archive_file" "observe_collection_function" {
    # depends_on = [local_file.function_config]
  depends_on = [
    null_resource.pip,
    local_file.function_config
  ]
  type        = "zip"
  source_dir  = "./AzureFunctionAppDev/"
  output_path = "./observe_collection.zip"
}

resource "local_file" "eventhub_function_config" {
  content = templatefile("${path.module}/eventhub_function.tpl", {
    eventHubName = azurerm_eventhub.observe_eventhub.name
    connection = "EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_CONNECTION"
  })
  filename = "${path.module}/AzureFunctionAppDev/EventHubTriggerPythonDev/function.json"
}

resource "local_file" "resource_management_function_config" {
  content = templatefile("${path.module}/resource_management_function.tpl", {
    eventHubName = azurerm_eventhub.observe_eventhub.name
    schedule = "TIMER_TRIGGER_FUNCTION_SCHEDULE"
  })
  filename = "${path.module}/AzureFunctionAppDev/TimerTriggerPythonDev/function.json"
}

resource "azurerm_storage_blob" "observe_collection_blob" {
  depends_on = [
    data.archive_file.observe_collection_function
  ]
  name = "observe-${data.archive_file.observe_collection_function.output_base64sha256}-collection.zip"
  storage_account_name = azurerm_storage_account.observe_storage_account.name
  storage_container_name = azurerm_storage_container.observe_storage_container.name
  type = "Block"
  source = data.archive_file.observe_collection_function.output_path
}

resource "azurerm_linux_function_app" "observe_function_app" {
  name                = "observe-function-collection"
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
    AZURE_TENANT_ID = var.azure_tenant_id
    AZURE_CLIENT_ID = var.azure_client_id
    AZURE_CLIENT_SECRET = var.azure_client_secret
    TIMER_TRIGGER_FUNCTION_SCHEDULE = var.timer_func_schedule
    EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_NAME = var.eventhub_name
    EVENTHUB_TRIGGER_FUNCTION_EVENTHUB_CONNECTION = "${azurerm_eventhub_authorization_rule.observe_eventhub_access_policy.primary_connection_string}"
  }

  site_config {
      application_stack  {
        python_version = "3.9"
      }
  }
}

locals {
    publish_code_command = "az webapp deployment source config-zip --resource-group ${azurerm_resource_group.observe_resource_group.name} --name ${azurerm_linux_function_app.observe_function_app.name} --src ${data.archive_file.observe_collection_function.output_path}"
    pip_install_command  =  "pip install --target='./AzureFunctionAppDev/.python_packages/lib/site-packages' -r ./AzureFunctionAppDev/requirements.txt"
}

resource "null_resource" "pip" {
  triggers = {
    requirements_md5 = "${filemd5("${path.module}/AzureFunctionAppDev/requirements.txt")}"
  }
  provisioner "local-exec" {
    command = local.pip_install_command
  }
}

resource "null_resource" "function_app_publish" {
  provisioner "local-exec" {
    command = local.publish_code_command
  }
  depends_on = [
    local.publish_code_command
    ]

  triggers = {
    input_json = data.archive_file.observe_collection_function.output_md5 //only refresh if collections changed
    publish_code_command = local.publish_code_command
  }
}

