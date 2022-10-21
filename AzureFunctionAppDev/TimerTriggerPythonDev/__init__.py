#! /usr/local/bin/python3

import azure.functions as func
import json
import logging
import os

from azure.mgmt.resource import ResourceManagementClient
from observe.utils import BaseHandler


RESOURCES_HANDLER = None


class ResourcesHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "ResourceManagement"
        self._reset_state()

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
            client = ResourceManagementClient(self.azure_credentials, sub_id)

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
