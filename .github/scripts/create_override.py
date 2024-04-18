import json
import os
import re 


print( "GITHUB_HEAD_REF: " + os.getenv("GITHUB_HEAD_REF"))
print( "GITHUB_REF: " + os.getenv("GITHUB_REF"))

# Extract branch name from either GITHUB_HEAD_REF or GITHUB_REF
if os.getenv("GITHUB_HEAD_REF") is not None and os.getenv("GITHUB_HEAD_REF") is not '':
    branch = os.getenv("GITHUB_HEAD_REF")
else:
    branch = os.getenv("GITHUB_REF")


# Remove /refs/heads/ from the branch name
# Replace "/" with "-" in the branch name
# Example: refs/heads/nikhil/add-CI-OB-29418 becomes nikhil-add-CI-OB-29418
branch = branch.replace("refs/heads/", "").replace("/", "-")


# Convert branch name to lowercase, remove special characters, and save to branch_concat
# Remove special characters
branch_concat = re.sub(r"[/\-]", "", branch).lower()[:20]



print (f"Branch name: {branch}")
print (f"Branch name concat: {branch_concat}")


# Define the JSON structure
config = {
    "terraform": {
        "backend": {
            "azurerm": {}
        }
    },
    "resource": {
        "azurerm_resource_group": {
            "observe_resource_group": {
                "name": "gh-rg-" + branch,
                "tags": {
                    "created_by": "terraform-ci"
                }
            }
        },
        "azuread_application": {
            "observe_app_registration": {
                "display_name":  "gh-app-" + branch
            }
        },
        "azurerm_storage_account": {
            "observe_storage_account": {
                "name": "ghsa" + branch_concat
            }
        },
         "azurerm_key_vault": {
            "key_vault": {
                "name": "gh-kv-" + branch
            }
        },
         "azurerm_eventhub_namespace": {
            "observe_eventhub_namespace": {
                "name": "gh-ehns-" + branch
            }
        },
         "azurerm_eventhub": {
            "observe_eventhub": {
                "name": "gh-eh-" + branch
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