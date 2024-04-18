import json
import os
import re 


print( "GITHUB_HEAD_REF: " + os.getenv("GITHUB_HEAD_REF"))
print( "GITHUB_REF: " + os.getenv("GITHUB_REF"))

# Extract branch name from either GITHUB_HEAD_REF or GITHUB_REF
if os.getenv("GITHUB_HEAD_REF") is not None and os.getenv("GITHUB_HEAD_REF") != '':
    branch = os.getenv("GITHUB_HEAD_REF")
else:
    branch = os.getenv("GITHUB_REF")




# Remove /refs/heads/ from the branch name
# Replace "/" with "-" in the branch name
# Example: refs/heads/nikhil/add-CI-OB-29418 becomes nikhil-add-CI-OB-29418
branch = branch.replace("refs/heads/", "").replace("/", "-")


# Convert branch name to lowercase, remove special characters, and save to branch_concat
# Remove special characters
branch_concat = re.sub(r"[/\-]", "", branch).lower()[:20] #Max 20 characters for branch name 



print (f"Branch name: {branch}")
print (f"Branch name concat: {branch_concat}")


rg_name = "gh-rg-" + branch
app_name = "gh-app-" + branch
storage_account_name = "ghsa" + branch_concat #Max 24 characters no capital letters,dash, underscore
key_vault_name = "ghkv" + branch_concat #Max 24 characters, no underscores/capital letters 
eventhub_namespace_name = "gh-ehns-" + branch
eventhub_name = "gh-eh-" + branch
eventhub_access_policy_name = "gh-ehap-" + branch
service_plan_name = "gh-sp-" + branch
function_app_name = "gh-fa-" + branch


# Define the JSON structure
## See https://learn.microsoft.com/en-us/answers/questions/1437283/azure-policy-issue
config = {
    "terraform": {
        "backend": {
            "azurerm": {
                "resource_group_name": "rg-terraform-github-actions-state",
                "storage_account_name": "citeststfazurecollection",
                "container_name": "tfstate",
                "key": branch + "/.tfstate"
            }
        }
    },
    "resource": {
        "azurerm_resource_group": {
            "observe_resource_group": {
                "name": rg_name,
                "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        },
        "azuread_application": {
            "observe_app_registration": {
                "display_name":  app_name,
                "tags": ["terraform-ci", branch]                  
                
            }
        },
        "azurerm_storage_account": {
            "observe_storage_account": {
                "name":  storage_account_name,
                "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        },
         "azurerm_key_vault": {
            "key_vault": {
                "name": key_vault_name,
                "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        },
         "azurerm_eventhub_namespace": {
            "observe_eventhub_namespace": {
                "name": eventhub_namespace_name,
                 "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        },
         "azurerm_eventhub": {
            "observe_eventhub": {
                "name": eventhub_name,
                "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        },
         "azurerm_eventhub_authorization_rule": {
            "observe_eventhub_access_policy": {
                "name": eventhub_access_policy_name,
                "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        },
        "azurerm_service_plan": {
            "observe_service_plan": {
                "name": service_plan_name,
                "tags": {
                    "created_by": "terraform-ci", 
                    "branch": branch
                }
            }
        },

        "azurerm_linux_function_app": {
            "observe_collect_function_app": {
                "name": function_app_name,
                "tags": {
                    "created_by": "terraform-ci",
                    "branch": branch
                }
            }
        }
        
    }
}


# Write the JSON to file
with open("override.tf.json", "w") as json_file:
    print ("Writing override.tf.json.....")
    json.dump(config, json_file, indent=3)


# Open the JSON file
with open("override.tf.json", "r") as json_file:
    # Load the JSON data
    data = json.load(json_file)

# Print the contents of the JSON file
print ("Contents of override.tf.json")
print(json.dumps(data, indent=4))