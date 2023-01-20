locals {
  json_files      = fileset(path.module, "./PolicyFiles/*/azurepolicy.json")
  json_data       = flatten([for f in local.json_files : jsondecode(file("${path.module}/${f}"))])
  ootb_policy_ids = ["/providers/Microsoft.Authorization/policyDefinitions/9a7c7a7d-49e5-4213-bea8-6a502b6272e0"] # sql datacases
  policy_ids      = concat([for o in azurerm_policy_definition.policy : o.id], local.ootb_policy_ids)
}

resource "azurerm_management_group" "observe_management_group" {
  display_name = "Observe Management Group"
}

resource "azurerm_policy_definition" "policy" {
  for_each            = { for f in local.json_data : format("%s %s", "Observe", f.properties.displayName) => f }
  name                = "observe-${replace(replace(regex("^[^\\.]*.(.*) to a Regional Event Hub", each.value.properties.displayName)[0], "/\\(|\\)|\\//", ""), "/\\s|\\./", "-")}"
  policy_type         = "Custom"
  mode                = each.value.properties.mode
  display_name        = each.key
  management_group_id = azurerm_management_group.observe_management_group.id

  metadata = <<METADATA
  ${jsonencode(each.value.properties.metadata)}
  METADATA


  policy_rule = <<POLICY_RULE
  ${jsonencode(each.value.properties.policyRule)}
  POLICY_RULE

  parameters = <<PARAMETERS
  ${jsonencode(each.value.properties.parameters)}
  PARAMETERS

}

resource "azurerm_policy_set_definition" "observe_policy" {
  name                = "sendToObserve"
  policy_type         = "Custom"
  display_name        = "Apply Diagnostic Settings to Send to Observe)"
  management_group_id = azurerm_management_group.observe_management_group.id

  parameters = <<PARAMETERS
    {
    "azureRegions": {
        "type": "Array",
        "defaultValue": ["eastus"],
        "metadata": {
        "displayName": "Allowed Locations",
        "description": "The list of locations that can be specified when deploying resources",
        "strongType": "location"
        }
    },
    "eventHubName": {
        "type": "String",
        "defaultValue": "/subscriptions/00000000-0000-0000-0000-000000000000/resourcegroups/observeresources-000000000000-eastus/providers/microsoft.eventhub/namespaces/observeeventhubnamespace-000000000000-eastus/eventhubs/observeeventhub-000000000000-eastus",
        "metadata": {
        "displayName": "EventHub Name",
        "description": "The event hub for Azure Diagnostics",
        "strongType": "Microsoft.EventHub/Namespaces/EventHubs",
        "assignPermissions": true
        }
    },
    "eventHubRuleId": {
        "type": "String",
        "defaultValue": "/subscriptions/00000000-0000-0000-0000-000000000000/resourcegroups/observeresources-000000000000-eastus/providers/microsoft.eventhub/namespaces/observeeventhubnamespace-000000000000-eastus/authorizationrules/rootmanagesharedaccesskey",
        "metadata": {
        "displayName": "EventHubRuleID",
        "description": "The event hub RuleID for Azure Diagnostics",
        "strongType": "Microsoft.EventHub/Namespaces/AuthorizationRules",
        "assignPermissions": true
        }
    },
    "metricsEnabled": {
        "type": "String",
        "metadata": {
        "displayName": "Enable Metrics",
        "description": "Enable Metrics - True or False"
        },
        "allowedValues": [
        "True",
        "False"
        ],
        "defaultValue": "True"
    },
    "profileName": {
        "type": "String",
        "defaultValue": "observe",
        "metadata": {
        "displayName": "Profile Name for Config",
        "description": "The profile name Azure Diagnostics"
        }
    }
    }
    PARAMETERS 

  dynamic "policy_definition_reference" {
    for_each = local.policy_ids
    content {
      policy_definition_id = policy_definition_reference.value
      parameter_values = (policy_definition_reference.value == "/providers/Microsoft.Authorization/policyDefinitions/9a7c7a7d-49e5-4213-bea8-6a502b6272e0" ?
        <<VALUE
            {
            "eventHubRuleId" : {"value": "[parameters('eventHubRuleId')]"},
            "profileName": {"value": "[parameters('profileName')]"},
            "metricsEnabled": {"value": "[parameters('metricsEnabled')]"}
            }
        VALUE
        :
        <<VALUE
            {
            "azureRegions": {"value": "[parameters('azureRegions')]"},
            "eventHubName": {"value": "[parameters('eventHubName')]"},
            "eventHubRuleId" : {"value": "[parameters('eventHubRuleId')]"},
            "profileName": {"value": "[parameters('profileName')]"},
            "metricsEnabled": {"value": "[parameters('metricsEnabled')]"}
            }
        VALUE
      )

    }
  }
}