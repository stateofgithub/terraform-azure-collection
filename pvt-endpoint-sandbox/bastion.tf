
# resource "azurerm_public_ip" "example" {
#   name                = "examplepip"
#   location            = azurerm_resource_group.sandbox_resource_group.location
#   resource_group_name = azurerm_resource_group.sandbox_resource_group.name
#   allocation_method   = "Static"
#   sku                 = "Standard"
# }

# resource "azurerm_bastion_host" "example" {
#   name                = "examplebastion"
#   location            = azurerm_resource_group.sandbox_resource_group.location
#   resource_group_name = azurerm_resource_group.sandbox_resource_group.name

#   ip_configuration {
#     name                 = "configuration"
#     subnet_id            = azurerm_subnet.func.id
#     public_ip_address_id = azurerm_public_ip.example.id
#   }
# }