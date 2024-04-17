import json
import os
import re 



# Extract branch name from either GITHUB_HEAD_REF or GITHUB_REF
branch = os.getenv("GITHUB_HEAD_REF")
if branch is None:
    branch = os.getenv("GITHUB_REF", "")
branch = branch.replace("refs/heads/", "")

# Replace "/" with "-" in the branch name
branch = branch.replace("/", "-")


# Append the modified branch name to GITHUB_OUTPUT
if os.getenv("CI"):
    with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
        f.write(f"branch={branch}\n")

# Convert branch name to lowercase, remove special characters, and save to branch_concat
# Remove special characters
branch_remove_special = re.sub(r"[/\-]", "", branch)
# Convert to lowercase
branch_lowercase = branch_remove_special.lower()
# Concatenate to 20 characters
branch_concat = branch_lowercase[:20]

# Append the concat branch name to GITHUB_OUTPUT
if os.getenv("CI"):
    with open(os.getenv("GITHUB_OUTPUT"), "a") as f:
        f.write(f"branch_concat={branch_concat}\n")

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
                "name": "gh-rg" + branch
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