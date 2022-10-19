#! /usr/local/bin/python3

import logging
import azure.functions as func
import json
import os

from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.identity import ClientSecretCredential

from observe.utils import BaseHandler


RESOURCES_HANDLER = None

# TODO:
# permissions: how to work around the AZURE_TENANT_ID, AZURE_CLIENT_ID, and APP stuff?
# request id
# rename "EventHubTriggerPythonDev" and "TimerTriggerPythonDev"
# make sure my changes are compatible with the rest of the
# add comment to all function and classes.
# Add more logging


class ResourcesHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "ResourceManagement"
        self._reset_state()

        # Required environment variables.
        try:
            self.azure_tenant_id = os.environ["AZURE_TENANT_ID"]
            self.azure_client_id = os.environ["AZURE_CLIENT_ID"]
            self.azure_client_secret = os.environ["AZURE_CLIENT_SECRET"]
        except:
            logging.critical(
                "[ResourcesHandler] Required ENV_VARS are not set properly")
            exit(-1)

    async def list_resources(self) -> None:
        # Construct Azure credentials.
        credentials = ClientSecretCredential(
            tenant_id=self.azure_tenant_id,
            client_id=self.azure_client_id,
            client_secret=self.azure_client_secret)

        # Get the list of subscription IDs for this tenant, and fetch resources
        # information for each of them.
        subscription_client = SubscriptionClient(credentials)
        for sub in subscription_client.subscriptions.list():
            sub_name = sub.serialize(keep_readonly=True)["displayName"]
            sub_id = sub.serialize(keep_readonly=True)[
                "subscriptionId"]
            logging.info(
                f"[ResourcesHandler] Processing resources for subscription \"{sub_name}\" ({sub_id}).")
            resource_client = ResourceManagementClient(credentials, sub_id)

            self._reset_state()
            self.buf.write("[")
            for resource in resource_client.resources.list(expand='createdTime,changedTime,provisioningState'):
                self.buf.write(json.dumps(resource.serialize(
                    keep_readonly=True), separators=(',', ':')))
                self.buf.write(",")
                self.num_obs += 1
                # Buffer size is above threshold.
                if self.buf.tell() >= self.max_req_size_byte:
                    await self._wrap_buffer_and_send_request()
                    self._reset_state()
                    self.buf.write("[")

            if self.num_obs > 0:
                await self._wrap_buffer_and_send_request()
                self._reset_state()

            logging.info(
                f"[ResourcesHandler] Resources processed for subscription \"{sub_name}\" ({sub_id}).")


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
