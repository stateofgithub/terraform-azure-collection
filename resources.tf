#Register resource providers that are not registerd by default in new subscription 

resource "azurerm_resource_provider_registration" "web" {
  name = "Microsoft.Web"
}

resource "azurerm_resource_provider_registration" "key_vault" {
  name = "Microsoft.KeyVault"
}

resource "azurerm_resource_provider_registration" "event_hub" {
  name = "Microsoft.EventHub"
}