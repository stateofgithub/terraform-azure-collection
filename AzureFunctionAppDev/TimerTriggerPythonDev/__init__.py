#! /usr/local/bin/python3

import azure.functions as func
import json
import logging
import os

from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.identity import ClientSecretCredential
from observe.utils import BaseHandler


RESOURCES_HANDLER = None


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

        # Construct Azure credentials.
        self.credentials = ClientSecretCredential(
            tenant_id=self.azure_tenant_id,
            client_id=self.azure_client_id,
            client_secret=self.azure_client_secret)

    async def _list_subscriptions(self) -> dict:
        client = SubscriptionClient(self.credentials)
        subscriptions = []
        for sub in client.subscriptions.list():
            subscriptions.append(sub.serialize(keep_readonly=True))
        return subscriptions

    async def list_resources(self) -> None:
        """
        Get the list of subscription IDs for this tenant, and fetch resources
        information for each of the subscription.
        """
        for subscription in await self._list_subscriptions():
            sub_name = subscription["displayName"]
            sub_id = subscription["subscriptionId"]
            logging.info(
                f"[ResourcesHandler] Processing resources for subscription \"{sub_name}\" ({sub_id}).")
            client = ResourceManagementClient(self.credentials, sub_id)
            self._reset_state()
            self.buf.write("[")
            for resource in client.resources.list(expand='createdTime,changedTime,provisioningState'):
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
