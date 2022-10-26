#! /usr/local/bin/python3

import azure.functions as func
import json
import logging

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.sql import SqlManagementClient
from observe.utils import BaseHandler


RESOURCES_HANDLER = None

# Constant URL parameters for the SDK request.
LIST_EXPAND = "createdTime,changedTime,provisioningState"
LIST_FILTER = "resourceType eq 'Microsoft.Compute/virtualMachines'"


class ResourcesHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "ResourceManagement"
        self._reset_state()

    async def _get_resources_in_subscription(self, sub_id: str) -> list:
        """
        Get resources using a combination of different APIs.
        """
        # Create a client for each of the following services, and call their
        # corresponding APIs to get the full resource information.

        #
        # Microsoft.Compute/virtualMachines
        #
        compute_client = ComputeManagementClient(
            self.azure_credentials, sub_id)
        vms = compute_client.virtual_machines.list_all()

        #
        # Microsoft.Sql/servers
        # Microsoft.Sql/servers/databases
        #
        sql_client = SqlManagementClient(self.azure_credentials, sub_id)
        servers_itr = sql_client.servers.list()
        servers = []
        databases = []
        # Iterate through all the SQL servers and list all the databases in each server.
        for s in servers_itr:
            servers.append(s)
            server_name = s.name
            server_resource_group = s.id.split('/')[4]
            databases.extend(sql_client.databases.list_by_server(
                resource_group_name=server_resource_group, server_name=server_name))

        #
        # Microsoft.ContainerService/managedClusters
        #
        container_service_client = ContainerServiceClient(
            self.azure_credentials, sub_id)
        managed_clusters = container_service_client.managed_clusters.list()

        #
        # Microsoft.Web/serverFarms
        #
        # TODO

        #
        # Microsoft.Web/sites
        #
        # TODO

        # For everything else, use the following API to fetch their resources.
        resource_client = ResourceManagementClient(
            self.azure_credentials, sub_id)
        # Construct the filter list to exclude the resource types already
        # processed above.
        exclude_resource_types = ["Microsoft.Sql/servers/databases", "Microsoft.Sql/servers", "Microsoft.Web/serverFarms",
                                  "Microsoft.Web/sites", "Microsoft.ContainerService/managedClusters", "Microsoft.Compute/virtualMachines"]
        list_filter = ' and '.join(
            ["resourceType ne '" + r + "'" for r in exclude_resource_types])

        # Reference for the LIST Resources api:
        # https://learn.microsoft.com/en-us/rest/api/resources/resources/list
        other_resources = resource_client.resources.list(
            expand=LIST_EXPAND, filter=list_filter)

        # Return the concatenated list.
        return [*vms, *servers, *databases, *managed_clusters, *other_resources]

    async def list_resources(self) -> None:
        """
        Get the list of subscription IDs for this tenant, and fetch resources
        information for each of the subscription.
        """
        self._reset_state()
        self.buf.write("[")
        for subscription in await self._list_subscriptions():
            sub_name = subscription["displayName"]
            sub_id = subscription["subscriptionId"]
            logging.info(
                f"[ResourcesHandler] Processing resources for subscription \"{sub_name}\" ({sub_id}).")

            resources_list = await self._get_resources_in_subscription(sub_id)
            for resource in resources_list:
                self.buf.write(json.dumps(resource.serialize(
                    keep_readonly=True), separators=(',', ':')))
                self.buf.write(",")
                self.num_obs += 1
                # Buffer size is above threshold.
                if self.buf.tell() >= self.max_req_size_byte:
                    await self._wrap_buffer_and_send_request()
                    self._reset_state()
                    self.buf.write("[")

            logging.info(
                f"[ResourcesHandler] Resources processed for subscription \"{sub_name}\" ({sub_id}).")

        if self.num_obs > 0:
            await self._wrap_buffer_and_send_request()


async def main(mytimer: func.TimerRequest) -> None:
    # Create a new resources handler, or load it from the cache.
    global RESOURCES_HANDLER
    if RESOURCES_HANDLER is None:
        RESOURCES_HANDLER = ResourcesHandler()

    try:
        await RESOURCES_HANDLER.list_resources()
    except Exception as e:
        logging.critical(f"[ResourcesHandler] {str(e)}")
        exit(-1)
    except:
        logging.critical(
            "[ResourcesHandler] Unknown error processing the resources")
        exit(-1)
