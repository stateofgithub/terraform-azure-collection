#! /usr/local/bin/python3

import logging
import azure.functions as func
import logging
import requests
import logging
import json
import io
import os

from azure.mgmt.resource import ResourceManagementClient
from requests.adapters import HTTPAdapter
from azure.identity import DefaultAzureCredential, ClientSecretCredential\

import azure.functions as func

SUBSCRIPTION_ID = "2B514E36-3A9B-4C89-AD51-4BDCAB22E84F"


def list_all_resources() -> io.StringIO:
    # Required environment variables.
    try:
        azure_tenant_id = os.environ["AZURE_TENANT_ID"]
        azure_client_id = os.environ["AZURE_CLIENT_ID"]
        azure_client_secret = os.environ["AZURE_CLIENT_SECRET"]
    except:
        logging.critical(
            "[ObserveClient] Required ENV_VARS are not set properly")
        exit(-1)

    credentials = ClientSecretCredential(
        tenant_id=azure_tenant_id, client_id=azure_client_id,
        client_secret=azure_client_secret)
    client = ResourceManagementClient(credentials, SUBSCRIPTION_ID)

    buf = io.StringIO()
    buf.write("[")
    for idx, item in enumerate(client.resources.list(expand='createdTime,changedTime,provisioningState')):
        if idx != 0:
            buf.write(",")
        buf.write(json.dumps(item.serialize(
            keep_readonly=True), separators=(',', ':')))
    buf.write("]")
    return buf


async def main(mytimer: func.TimerRequest) -> None:
    # Create an HTTP client, or load it from the cache.
    global OBSERVE_CLIENT
    if OBSERVE_CLIENT is None:
        OBSERVE_CLIENT = ObserveClient()

    # if mytimer.past_due:
        # logging.info('The timer is past due!')

    try:
        OBSERVE_CLIENT._send_request(list_all_resources())

    except Exception as e:
        logging.critical(f"[ObserveClient] {str(e)}")
        exit(-1)
    except:
        logging.critical("[ObserveClient] Unknown error processing the events")
        exit(-1)


# remove duplicated code

OBSERVE_CLIENT = None


class ObserveClient:
    def __init__(self):
        # Required environment variables.
        try:
            self.observe_customer = os.environ["OBSERVE_CUSTOMER"]
            self.observe_token = os.environ["OBSERVE_TOKEN"]
            self.observe_domain = os.environ["OBSERVE_DOMAIN"]
        except:
            logging.critical(
                "[ObserveClient] Required ENV_VARS are not set properly")
            exit(-1)

        # Optional environment variables with default value.
        self.max_req_size_byte = int(
            os.getenv("OBSERVE_CLIENT_MAX_REQ_SIZE_BYTE") or 512*1024)
        # Each request to Observe can batch multiple events from Event Hub,
        # and each event can contains multiple observation records.
        self.max_events_per_req = int(
            os.getenv("OBSERVE_CLIENT_MAX_EVENTS_PER_REQ") or 256)
        self.max_retries = int(os.getenv("OBSERVE_CLIENT_MAX_RETRIES") or 5)
        self.max_timeout_sec = int(
            os.getenv("OBSERVE_CLIENT_MAX_TIMEOUT_SEC") or 10)

        logging.info(
            f"[ObserveClient] Initialized a new client: "
            f"observe_customer = {self.observe_customer}, "
            f"domain = {self.observe_domain}, "
            f"max_req_size_byte = {self.max_req_size_byte}, "
            f"max_events_per_req = {self.max_events_per_req}")

    def _send_request(self, input_buffer) -> None:
        """
        Wrap up the request, and send the observations in the current buffer to
        Observe's collector endpoint.
        """
        if input_buffer.tell() <= 0:
            raise Exception("Buffer should contain data but is empty")

        if os.getenv("DEBUG_OUTPUT") == 'true':
            # Instead of sending data to Observe endpoint, print it out for debugging.
            logging.critical(f"[ObserveClient] {input_buffer.getvalue()}")
            return

        # Send the request.
        req_url = f"https://{self.observe_customer}.collect.{self.observe_domain}/v1/http/azure?source=EventHubTriggeredFunction"
        s = requests.Session()
        s.mount(req_url, HTTPAdapter(max_retries=self.max_retries))

        response = s.post(
            req_url,
            headers={
                'Authorization': 'Bearer ' + self.observe_token,
                'Content-type': 'application/json'},
            data=bytes(input_buffer.getvalue().encode('utf-8')),
            timeout=self.max_timeout_sec)

        # Error handling.
        response.raise_for_status()
