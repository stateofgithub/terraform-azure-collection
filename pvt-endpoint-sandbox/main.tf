locals {
  is_windows    = substr(pathexpand("~"), 0, 1) == "/" ? false : true
  sleep_command = local.is_windows == true ? "Start-Sleep" : "sleep"
  #region        = lookup(var.location_abbreviation, var.location, "none-found")
  #keyvault_name = "${local.region}${var.observe_customer}${local.sub}"
  sub           = substr(data.azurerm_subscription.primary.subscription_id, -8, -1)
}

# Obtains current client config from az login, allowing terraform to run.
data "azuread_client_config" "current" {}

# Creates the alias of your Subscription to be used for association below.
data "azurerm_subscription" "primary" {}



resource "azurerm_resource_group" "sandbox_resource_group" {
  name     = "tf-pvtEndpointTest-nikhil-${var.resource_group_location}-${local.sub}"
  location = var.resource_group_location
}


# Create a virtual network and two subnets
resource "azurerm_virtual_network" "vnet" {
  name                = "example-vnet"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.sandbox_resource_group.location
  resource_group_name = azurerm_resource_group.sandbox_resource_group.name
}

resource "azurerm_subnet" "func" {
  name                 = "example-func-subnet"
  resource_group_name  = azurerm_resource_group.sandbox_resource_group.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
  private_endpoint_network_policies_enabled = true
}




resource "azurerm_storage_account" "sandbox_storage_account" {
  name                     = lower("SAtfpvtEndpointNikhil")
  resource_group_name      = azurerm_resource_group.sandbox_resource_group.name
  location                 = azurerm_resource_group.sandbox_resource_group.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Probably want to use ZRS when we got prime time
  public_network_access_enabled = true #Set to false before publishing
  allow_nested_items_to_be_public = false

  #shared_access_key_enabled = false #All requests must be authorized via Azure Active Directory

  min_tls_version = "TLS1_2"
  infrastructure_encryption_enabled = true
  account_kind = "StorageV2"
  is_hns_enabled = true

    tags = {
        "Application-Name" = "tf-pvtEndpointTest-nikhil"
        "Environment" = "sandbox"
        "Parent-Service" = "PAAS"
        "Workload-Category" = "Storage"
        "Workload-Sub-Category" = "StorageAccount"
        "Deployment-Method" = "Terraform"
  }

}


resource "azurerm_storage_container" "sandbox_storage_container" {
  name                  = lower("ContainerSAtfpvtEndpointNikhil")
  storage_account_name  = azurerm_storage_account.sandbox_storage_account.name
  container_access_type = "private"
}



resource "azurerm_private_endpoint" "pvt_endpoint" {
  name                = "example-endpoint"
  location            = azurerm_resource_group.sandbox_resource_group.location
  resource_group_name = azurerm_resource_group.sandbox_resource_group.name
  subnet_id           = azurerm_subnet.func.id

  private_service_connection {
    name                           = "example-privateserviceconnection"
    private_connection_resource_id = azurerm_storage_account.sandbox_storage_account.id
    subresource_names              = ["blob"] 
    is_manual_connection           = false
  }

 lifecycle {
    ignore_changes = [
      subnet_id
    ]
  }
}

resource "azurerm_service_plan" "sandbox_service_plan" {
  name                = "svcPlan-pvtEndpointNikhil"
  resource_group_name = azurerm_resource_group.sandbox_resource_group.name
  location            = azurerm_resource_group.sandbox_resource_group.location
  os_type             = "Linux"
  sku_name            = "Y1"

}

resource "azurerm_linux_function_app" "sandbox_function_app" {
  name                = "app-pvtEndpointNikhil"
  resource_group_name = azurerm_resource_group.sandbox_resource_group.name
  location            = azurerm_resource_group.sandbox_resource_group.location

  storage_account_name           = azurerm_storage_account.sandbox_storage_account.name  
  service_plan_id                = azurerm_service_plan.sandbox_service_plan.id
  storage_account_access_key     = azurerm_storage_account.sandbox_storage_account.primary_access_key

  site_config {}
}
