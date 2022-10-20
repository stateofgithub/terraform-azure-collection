To begin Azure collection, first clone this repo locally:

git clone git@github.com:observeinc/terraform-azure-collection.git

Next we need to create our variables that will get injected in to the app.  Create a file at the root of this repo and name it `azure.auto.tfvars`.
The contents of that file should be:

    observe_customer = "<OBSERVE_CUSTOMER_ID>"
    observe_token = "<DATASTREAM_INGEST_TOKEN>"
    observe_domain = "<OBSERVE_DOMAIN(i.e. observe-staging.com)>"
    eventhub_namespace = "<EVENTHUB_NAMESPACE>"
    eventhub_name = "<EVENTHUB_NAME>"
    resource_group_name = "<RESOURCE_GROUP>"
    azure_tenant_id = "<AZURE_TENANT_ID>"
    azure_client_id = "<AZURE_CLIENT_ID>"
    azure_client_secret = "<AZURE_CLIENT_SECRET>"
    timer_func_schedule = "<TIMER_TRIGGER_FUNCTION_SCHEDULE>"

Next we need to login to Azure from the CLI:

    az login

Now we are ready to deploy.  You should just need to run:

    terraform init
    terraform apply -auto-approve

Collection should begin shortly
