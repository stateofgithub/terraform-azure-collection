#! /usr/local/bin/python3

import asyncio
import azure.functions as func
import functools
import logging
import requests
import json
import os
import io

from datetime import datetime
from requests.adapters import HTTPAdapter

OBSERVE_CLIENT = None


class ObserveClient:
    def __init__(self):
        # Required environment variables.
        try:
            self.customer_id = os.environ["OBSERVE_CUSTOMER_ID"]
            self.observe_domain = os.environ["OBSERVE_DOMAIN"]
            self.datastream_token = os.environ["OBSERVE_DATASTREAM_TOKEN"]
        except:
            logging.critical(
                "[ObserveClient] Required ENV_VARS are not set properly")
            exit(-1)

        # Optional environment variables with default value.
        # Each request to Observe can batch multiple events from Event Hub,
        # and each event can contains multiple observation records.
        self.max_req_size_byte = int(
            os.getenv("OBSERVE_CLIENT_MAX_REQ_SIZE_BYTE") or 512*1024)
        self.max_events_per_req = int(
            os.getenv("OBSERVE_CLIENT_MAX_EVENTS_PER_REQ") or 256)
        self.max_retries = int(os.getenv("OBSERVE_CLIENT_MAX_RETRIES") or 5)
        self.max_timeout_sec = int(
            os.getenv("OBSERVE_CLIENT_MAX_TIMEOUT_SEC") or 10)

        logging.info(
            f"[ObserveClient] Initialized a new client: "
            f"customer_id = {self.customer_id}, "
            f"domain = {self.observe_domain}, "
            f"max_req_size_byte = {self.max_req_size_byte}, "
            f"max_events_per_req = {self.max_events_per_req}")

    async def reset_state(self):
        """
        Reset the state of the client.
        """
        self.num_obs_in_cur_req = 0
        self.num_events_in_cur_req = 0
        self.buf = io.StringIO()
        self.buf.write("[")

    async def process_events(self, event_arr: func.EventHubEvent):
        """
        Parse and send all incoming events to Observe, in multiple requests
        if needed. Each HTTP request contains an array of JSON observations.
        """
        if len(event_arr) == 0:
            logging.error("[ObserveClient] 0 event to process, skip")
            return

        # For cardinality=many scenarios, each event points to the common
        # metadata of all the events.
        if event_arr[0].metadata == {}:
            raise Exception(
                "Event metadata is missing for is function invocation")

        # Index of the starting event in the current request.
        event_index = 0
        await self.reset_state()

        for e in event_arr:
            # Here we assume the event body is always a valid JSON, as described
            # in the Azure documentation.
            try:
                raw_data = json.loads(e.get_body().decode())
            except:
                raise Exception("Event data is not a valid JSON")

            self.num_events_in_cur_req += 1

            # Data could be a list of records in the format of {"records": [...]}
            # In this case, we break it down into multiple observations.
            is_json_list = ("records" in raw_data and type(
                raw_data["records"]) is list)
            for r in raw_data["records"] if is_json_list else [raw_data]:
                self.buf.write(json.dumps(r, separators=(',', ':')))
                self.buf.write(",")
                self.num_obs_in_cur_req += 1

            # Check whether we need to flush the current buffer to Observe.
            if self.num_events_in_cur_req >= self.max_events_per_req or \
                    self.buf.tell() >= self.max_req_size_byte:
                self.buf.write(
                    await self._build_req_metadata_json(
                        event_arr[0].metadata, event_index))
                # Update the start index for the next request.
                event_index += self.num_events_in_cur_req
                self.buf.write("]")
                await self._send_request()
                await self.reset_state()

        # Flush remaining data from the buffer to Observe.
        if self.num_obs_in_cur_req > 0:
            self.buf.write(await self._build_req_metadata_json(
                event_arr[0].metadata, event_index))
            self.buf.write("]")
            await self._send_request()
            await self.reset_state()

        logging.info(f"[ObserveClient] {len(event_arr)} events processed.")

    async def _build_req_metadata_json(self, event_metadata, event_index) -> str:
        """
        Construct a metadata observation for the current Observe request,
        as the last record in the JSON array.
        """
        if self.buf.tell() <= 0:
            raise Exception("Buffer should contain data but is empty")
        elif self.num_obs_in_cur_req <= 0:
            raise Exception(
                "There should be at least 1 observation in current request")

        req_meta = {
            "ObserveNumEvents": self.num_events_in_cur_req,
            "ObserveNumObservations": self.num_obs_in_cur_req,
            "ObserveTotalSizeByte": self.buf.tell(),
            "ObserveSubmitTimeUtc": str(datetime.utcnow()).replace(' ', 'T'),
            "AzureEventHubPartitionContext": event_metadata.get("PartitionContext", {}),
        }

        if "SystemPropertiesArray" not in event_metadata:
            req_meta["AzureEventHubSystemPropertiesArray"] = {}
        else:
            # Get the sub array from the original metadata.
            req_meta["AzureEventHubSystemPropertiesArray"] = event_metadata[
                "SystemPropertiesArray"][event_index: event_index+self.num_obs_in_cur_req]

        return json.dumps(req_meta, separators=(',', ':'))

    async def _send_request(self):
        """
        Wrap up the request, and send the observations in the current buffer to
        Observe's collector endpoint.
        """
        if self.buf.tell() <= 0:
            raise Exception("Buffer should contain data but is empty")

        if os.getenv("DEBUG_OUTPUT") == 'true':
            # Instead of sending data to Observe, print it out to logging.
            logging.critical(f"[ObserveClient] {self.buf.getvalue()}")
            return

        # Send the request.
        req_url = f"https://{self.customer_id}.collect.{self.observe_domain}/v1/http/azure?source=EventHubTriggeredFunction"
        s = requests.Session()
        s.mount(req_url, HTTPAdapter(max_retries=self.max_retries))

        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            functools.partial(
                s.post,
                req_url,
                headers={
                    'Authorization': 'Bearer ' + self.datastream_token,
                    'Content-type': 'application/json'},
                data=bytes(self.buf.getvalue().encode('utf-8')),
                timeout=self.max_timeout_sec)
        )
        response = await future

        # Error handling.
        response.raise_for_status()

        logging.info(
            f"[ObserveClient] {self.num_obs_in_cur_req} observations sent, "
            f"response: {response.json()}")


async def main(event: func.EventHubEvent):
    # Create an HTTP client, or load it from the cache.
    global OBSERVE_CLIENT
    if OBSERVE_CLIENT is None:
        OBSERVE_CLIENT = ObserveClient()

    # Process the array of new events.
    try:
        await OBSERVE_CLIENT.process_events(event)
    except Exception as e:
        logging.critical(f"[ObserveClient] {str(e)}")
        exit(-1)
    except:
        logging.critical("[ObserveClient] Unknown error processing the events")
        exit(-1)
