## Github Actions Module

This directory contains the Terraform module for the GitHub Actions workflow for creating and destroying the Observe Collection in an ephemeral Azure resource group in the `Terraform Automation` subscription 

The module is used by the GitHub Actions workflow in the `.github/workflows/ci-tests.yml` directory.


It will perform the following:
- Create a new token with current Github branch name `TF_VAR_branch` under "Azure" Datastream in the specified `TF_VAR_OBSERVE_CUSTOMER`
- Using the generated secret token from above as in input to the module, install the `terraform-azure-collection` module from root of the repo


See diagram from overview of [flow](../workflows/ci-tests.png)

## Override Files

Note that since this module is used by the GitHub Actions workflow, it's recommended to use this with an override file as done so in the workflow `.github/workflows/ci-tests.yml` to avoid polluting and keeping resource groups separate. 

The workflow `.github/workflows/ci-tests.yml` will create a new resource group for the ephemeral Azure resources based on `GITHUB_REF` in the running workflow and uses the `.github/scripts/create_override_collection.py` script. 