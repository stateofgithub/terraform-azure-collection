## Data Collection Module Installation

1. Install [Azure's CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
   
2. Ensure Azure CLI is properly installed by logging into Azure
     ```
    az login
    ```
    You should receive a token from your browser that looks like:
    ```
    [
      {
        "cloudName": "AzureCloud",
        "homeTenantId": "########-####-####-####-############",
        "id": "########-####-####-####-############",
        "isDefault": true,
        "managedByTenants": [],
        "name": "Acme Inc",
        "state": "Enabled",
        "tenantId": "########-####-####-####-############",
        "user": {
          "name": "joe@somecompany.com",
          "type": "user"
        }
      }
    ]
    ```
3.  Install [Azure's Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Cmacos%2Ccsharp%2Cportal%2Cbash#install-the-azure-functions-core-tools)

4. Clone Observe's Terraform Collection Module ([terraform-azure-collection](https://github.com/observeinc/terraform-azure-collection)) repo locally
```
    git clone git@github.com:observeinc/terraform-azure-collection.git
```

5. Assign Application Variables

    Inside the root of the terraform-azure-collection create a file named **`azure.auto.tfvars`**. The contents of that file will be:

```
observe_customer = "<OBSERVE_CUSTOMER_ID>"
observe_token = "<DATASTREAM_INGEST_TOKEN>"
observe_domain = "<OBSERVE_DOMAIN(i.e. observe-staging.com)>"
timer_resources_func_schedule = "<TIMER_TRIGGER_FUNCTION_SCHEDULE>" 
timer_vm_metrics_func_schedule = "<TIMER_TRIGGER_FUNCTION_SCHEDULE>"
location = "<AZURE_REGIONAL_NAME>"
```

> Note: Default values are assigned for **`timer_resources_func_schedule`** and **`timer_vm_metrics_func_schedule`**, both based on **[NCRONTAB](https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-timer?tabs=in-process&pivots=programming-language-csharp#ncrontab-examples)**
>
> **`location`'s** value is [Azure's Regional Name](https://azuretracks.com/2021/04/current-azure-region-names-reference/) and is "eastus" by default

6. Deploy the Application
   
   Inside the root directory of the terraform-azure-collection module run the following commands:

  ```
      terraform init
      terraform apply -auto-approve
  ```

Collection should begin shortly

## Azure Resource Configuration

To receive logs and metrics for resources please add the appropriate diagnostic settings to each.  See "Azure Resource Configuration" section in [Observe's Azure Integration page](https://docs.observeinc.com/en/latestcontent/integrations/azure/azure.html) for more info.


## Removing Observe's Azure Collection Module ##

1. Remove the terraform-azure-collection module by running the following in the root directory:
```
    terraform destroy
```
>Note: You may encounter the following bug in the Azure provider during your destroy:
```
  Error: Deleting service principal with object ID "########-####-####-####-############", got status 403
  
  ServicePrincipalsClient.BaseClient.Delete(): unexpected status 403 with OData error:
  Authorization_RequestDenied: Insufficient privileges to complete the operation.
```
>If this happens execute simply remove the azuread_service_principal.observe_service_principal from terraform state and continue the destroy
```
  terraform state rm azuread_service_principal.observe_service_principal
  terraform destroy
```
