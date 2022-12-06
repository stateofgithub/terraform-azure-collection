#! /usr/local/bin/python3

import azure.functions as func
import json
import logging

from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.mgmt.web import WebSiteManagementClient
from observe.utils import BaseHandler


RESOURCES_HANDLER = None

# Constant URL parameters for the SDK request.
LIST_EXPAND = "createdTime,changedTime,provisioningState"


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

        # Microsoft.Compute/virtualMachines
        # Reference: https://learn.microsoft.com/en-us/rest/api/compute/virtual-machines/list-by-location
        # Microsoft.Compute/disks
        # Reference: https://learn.microsoft.com/en-us/rest/api/compute/disks/list
        compute_client = ComputeManagementClient(
            self.azure_credentials, sub_id)
        vms = compute_client.virtual_machines.list_by_location(location=self.azure_client_location)

        disks = compute_client.disks.list()

        # Microsoft.Sql/servers
        # Reference: https://learn.microsoft.com/en-us/rest/api/sql/2021-11-01/servers/list
        # Microsoft.Sql/servers/databases
        # Reference: https://learn.microsoft.com/en-us/rest/api/sql/2022-05-01-preview/databases/list-by-server
        sql_client = SqlManagementClient(self.azure_credentials, sub_id)
        servers_itr = sql_client.servers.list()
        servers = []
        databases = []
        for s in servers_itr:
            servers.append(s)
            server_name = s.name
            server_resource_group = s.id.split('/')[4]
            databases.extend(sql_client.databases.list_by_server(
                resource_group_name=server_resource_group, server_name=server_name))

        # Microsoft.ContainerService/managedClusters
        # Reference: https://learn.microsoft.com/en-us/rest/api/aks/managed-clusters/list
        container_service_client = ContainerServiceClient(
            self.azure_credentials, sub_id)
        managed_clusters = container_service_client.managed_clusters.list()

        # Microsoft.Web/serverFarms (externally called App Service Plans)
        # Reference: https://learn.microsoft.com/en-us/rest/api/appservice/app-service-plans/list
        web_client = WebSiteManagementClient(self.azure_credentials, sub_id)
        server_farms = web_client.app_service_plans.list(detailed=True)

        # Microsoft.Web/sites (externally called Web Apps / Function Apps)
        # Reference: https://learn.microsoft.com/en-us/rest/api/appservice/web-apps/list
        # Microsoft.Web/sites/functions
        # Reference: https://learn.microsoft.com/en-us/rest/api/appservice/web-apps/list-functions
        web_sites_itr = web_client.web_apps.list()
        web_sites = []
        web_functions = []
        for w in web_sites_itr:
            web_sites.append(w)
            site_name = w.name
            site_resource_group = w.resource_group
            web_functions.extend(web_client.web_apps.list_functions(
                resource_group_name=site_resource_group, name=site_name))

        # Microsoft.Network/networkInterfaces
        # Reference: https://learn.microsoft.com/en-us/rest/api/virtualnetwork/network-interfaces/list-all
        # Microsoft.Network/publicIPAddresses
        # Reference: https://learn.microsoft.com/en-us/rest/api/virtualnetwork/public-ip-addresses/list-all
        network_client = NetworkManagementClient(
            self.azure_credentials, sub_id)
        network_interfaces = network_client.network_interfaces.list_all()
        public_ip_addresses = network_client.public_ip_addresses.list_all()

        # # For everything else, use the following API to fetch their resources.
        resource_client = ResourceManagementClient(
            self.azure_credentials, sub_id)

        # Currently our exclude list is empty and we allow duplicated info
        # for some of the services. This is because we need information from
        # both list APIs.
        exclude_resource_types = [
            #     "Microsoft.Compute/virtualMachines",
            #     "Microsoft.Compute/disks"
            #     "Microsoft.Sql/servers",
            #     "Microsoft.Sql/servers/databases",
            #     "Microsoft.ContainerService/managedClusters",
            #     "Microsoft.Web/serverFarms",
            #     "Microsoft.Web/sites",
            #     "Microsoft.Web/sites/functions"
            #     "Microsoft.Network/networkInterfaces"
            #     "Microsoft.Network/publicIPAddresses"
        ]
        list_filter = ' and '.join(
            ["resourceType ne '" + r + "'" for r in exclude_resource_types])
        # Apply filter on Azure location.
        if len(list_filter) > 0:
            list_filter += " and "
        list_filter += f"location eq '{self.azure_client_location}'"

        # Reference: https://learn.microsoft.com/en-us/rest/api/resources/resources/list
        other_resources = resource_client.resources.list(
            expand=LIST_EXPAND, filter=list_filter)

        return [*vms, *disks, *servers, *databases, *managed_clusters, *server_farms, *web_sites, *web_functions, *network_interfaces, *public_ip_addresses, *other_resources]

    async def list_resources(self) -> None:
        """
        Get the list of subscription IDs for this tenant, and fetch resources
        information for each of the subscription.
        """
        self._reset_state()
        is_first_observation = True
        for subscription in await self._list_subscriptions():
            sub_serialized = subscription.serialize(keep_readonly=True)
            sub_name = sub_serialized["displayName"]
            sub_id = sub_serialized["subscriptionId"]
            logging.info(
                f"[ResourcesHandler] Processing resources for subscription \"{sub_name}\" ({sub_id}).")

            resources_list = await self._get_resources_in_subscription(sub_id)
            # append the subscription itself.
            resources_list.append(subscription)

            for resource in resources_list:
                serialized = resource.serialize(keep_readonly=True)
                if 'location' in serialized and serialized['location'] != self.azure_client_location:
                    # Skip the resource if it is in a different Azure location.
                    continue

                if is_first_observation is False:
                    self.buf.write(",")
                else:
                    is_first_observation = False

                self.buf.write(json.dumps(serialized, separators=(',', ':')))
                self.num_obs += 1
                # Buffer size is above threshold.
                if self.buf.tell() >= self.max_req_size_byte:
                    await self._wrap_buffer_and_send_request()
                    self._reset_state()
                    is_first_observation = True

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
