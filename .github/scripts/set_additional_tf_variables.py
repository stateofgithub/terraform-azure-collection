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

env_file = os.getenv('GITHUB_ENV')
with open(env_file, "a") as myfile:
    myfile.write("TF_VAR_branch=" + branch)

print ("TF_VAR_branch set to " + branch + "for .github/terraform/main.tf")
