#! /usr/local/bin/python3

import logging
import azure.functions as func
import json
import os

from datetime import datetime
from azure.mgmt.resource import ResourceManagementClient
from azure.identity import ClientSecretCredential

from observe.utils import BaseHandler


RESOURCES_HANDLER = None

SUBSCRIPTION_ID = "2B514E36-3A9B-4C89-AD51-4BDCAB22E84F"

# TODO:
# make the function async io
# refactor the code to use handler - buffer - observe client
# get list of subscriptions, and list the resources in all of them.
# permissions: how to work around the AZURE_TENANT_ID, AZURE_CLIENT_ID, and APP stuff?
# "only collected resources that we are collecting data for": how do we apply filter, and keep the filter up to date?
# request id
# rename "EventHubTriggerPythonDev" and "TimerTriggerPythonDev"
# make sure my changes are compatible with the rest of the
# add comment to all function and classes.


class ResourcesHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "timer_triggered_func"
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
        client = ResourceManagementClient(credentials, SUBSCRIPTION_ID)

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

        logging.info(f"[ResourcesHandler] Resources processed.")


async def main(mytimer: func.TimerRequest) -> None:
    # Create a new resources handler, or load it from the cache.
    global RESOURCES_HANDLER
    if RESOURCES_HANDLER is None:
        RESOURCES_HANDLER = ResourcesHandler()

    if mytimer.past_due:
        logging.info('The timer is past due!')

    try:
        await RESOURCES_HANDLER.list_resources()
    except Exception as e:
        logging.critical(f"[ResourcesHandler] {str(e)}")
        exit(-1)
    except:
        logging.critical(
            "[ResourcesHandler] Unknown error processing the resources")
        exit(-1)
