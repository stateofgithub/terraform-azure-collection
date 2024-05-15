# Scripts for use in Github Actions Workflow

See diagram from overview of [flow](../workflows/ci-tests.png)


## Override Script

`create_override_collection.py` extracts branch name from either GITHUB_HEAD_REF or GITHUB_REF and uses it to create either a `branch` or a `branch_concat` variable. 

The variables are used to create override names as below for both resource group that will be created along with names of resources in the resource group:

```
rg_name = "gh-rg-" + branch
app_name = "gh-app-" + branch
storage_account_name = "ghsa" + branch_concat #Max 24 characters no capital letters,dash, underscore
key_vault_name = "ghkv" + branch_concat #Max 24 characters, no underscores/capital letters 
eventhub_namespace_name = "gh-ehns-" + branch
eventhub_name = "gh-eh-" + branch
eventhub_access_policy_name = "gh-ehap-" + branch
service_plan_name = "gh-sp-" + branch
function_app_name = "gh-fa-" + branch
```

The override file, `override.tf.json` is then used to create the resources with new names and tags in the resource group, instead of what is defined in main.tf. It is created at the root of the repo so that it can be used & recognized by the `terraform` commands correctly. 


## Set TF Variables Script

`set_additional_tf_variables.py` extracts branch name from either GITHUB_HEAD_REF or GITHUB_REF and uses it to create a `TF_VAR_branch` variable. This variable is used when running terraform module in `.github/terraform/` for the workflow. 

The variable is used so the token created in Observe customer corresponds correctly to the branch name upon `apply` and `destroy` commands.


## Query Observe Script

`query_observe.py` queries the last 30 minutes of the `Azure` Dataset in the Observe customer. It requires the following variables to be set in the Github Actions workflow:

- `OBSERVE_CUSTOMER`
- `OBSERVE_DOMAIN`
- `OBSERVE_USER_EMAIL`
- `OBSERVE_USER_PASSWORD`
- `AZURE_DATASET_ID`
- `OBSERVE_TOKEN_ID` 


The script checks whether the `Azure` dataset, with the provided `AZURE_DATASET_ID` and the unique `OBSERVE_TOKEN_ID` contains data coming from the three major sources of the collection: EventHub, ResourceManagement, VmMetrics. For each source, it verifies that the data both exists AND is not stale (30 minutes) from the current time. 

This validation check serves as an End-to-End check to ensure that the data is flowing from Azure to Observe without any issues.


