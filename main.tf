### TODO:
#   - set up service insights automatically
#   - break out into separate files to make more readable
#   - automate configuring resources sending data to event hub

resource "azurerm_resource_group" "observe_resource_group" {
  name     = "observe-resources"
  location = "East US"
}

resource "azurerm_eventhub_namespace" "observe_eventhub_namespace" {
  name                = "observeEventhubNamesapce"
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  sku                 = "Basic"

  zone_redundant = true
  capacity            = 1

  tags = {
    created_by = "Observe Terraform"
  }
}

resource "azurerm_eventhub" "observe_eventhub" {
  name                = "observeeventhub"
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

resource "azurerm_eventhub_namespace_authorization_rule" "observe_eventhub_namespace_access_policy" {
  name                = "observeSharedAccessPolicy"
  namespace_name      = azurerm_eventhub_namespace.observe_eventhub_namespace.name
  resource_group_name = azurerm_resource_group.observe_resource_group.name

  listen = true
  send   = true
  manage = false
}

resource "azurerm_service_plan" "observe_service_plan" {
  name                = "observe-service-plan"
  location            = azurerm_resource_group.observe_resource_group.location
  resource_group_name = azurerm_resource_group.observe_resource_group.name
  os_type             = "Linux"
  sku_name            = "EP1"
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

# create the template file config_json separately from the archive_file block
resource "local_file" "function_config" {
  content = templatefile("${path.module}/function.tpl", {
    eventHubName = azurerm_eventhub.observe_eventhub.name
    connection = "OBSERVE_EVENTHUB_CONNECTION_STRING"
  })
  filename = "${path.module}/AzureFunctionAppDev/EventHubTriggerPythonDev/function.json"
}

resource "azurerm_storage_blob" "observe_collection_blob" {
  depends_on = [
    data.archive_file.observe_collection_function
  ]
  # name = "${data.archive_file.observe_collection_function.output_base64sha256}.zip"
  name = "${filesha256(data.archive_file.observe_collection_function.output_path)}.zip"
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
    FUNCTIONS_WORKER_RUNTIME = "python"
    WEBSITE_RUN_FROM_PACKAGE = 1
    AzureWebJobsDisableHomepage = true
    OBSERVE_DOMAIN = var.observe_domain
    OBSERVE_CUSTOMER_ID = var.observe_customer
    OBSERVE_DATASTREAM_TOKEN = var.observe_ingest_token
    OBSERVE_EVENTHUB_CONNECTION_STRING = "${azurerm_eventhub_authorization_rule.observe_eventhub_access_policy.primary_connection_string}"
  }

  site_config {}
}

locals {
    publish_code_command = "az  webapp deployment source config-zip --resource-group ${azurerm_resource_group.observe_resource_group.name} --name ${azurerm_linux_function_app.observe_function_app.name} --src ${data.archive_file.observe_collection_function.output_path}"
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
  depends_on = [local.publish_code_command]
  triggers = {
    input_json = filemd5(data.archive_file.observe_collection_function.output_path) //only refresh if collections changed
    publish_code_command = local.publish_code_command
  }
}

# resource "azurerm_monitor_diagnostic_setting" "observe_diagnostics" {
#   name               = "send_to_observe"
#   target_resource_id = resource.azurerm_linux_function_app.observe_function_app.id
#   eventhub_name  = resource.azurerm_eventhub.observe_eventhub.name
#   eventhub_authorization_rule_id = resource.azurerm_eventhub_namespace_authorization_rule.observe_eventhub_namespace_access_policy.id

#   log {
#     category = "FunctionAppLogs"
#     enabled  = true

#     # retention_policy {
#     #   enabled = false
#     # }
#   }

#   metric {
#     category = "AllMetrics"

#     retention_policy {
#       enabled = false
#     }
#   }
# }