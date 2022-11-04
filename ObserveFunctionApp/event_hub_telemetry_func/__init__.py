#! /usr/local/bin/python3

import azure.functions as func
import json
import logging

from observe.utils import BaseHandler

EVENTHUB_HANDLER = None


class EventHubHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "EventHub"
        self._reset_state()

    async def process_events(self, event_arr) -> None:
        """
        Parse and send all incoming events to Observe, in multiple requests
        if needed. Each HTTP request contains an array of JSON observations.
        """
        if len(event_arr) == 0:
            logging.error("[EventHubHandler] 0 event to process, skip")
            return

        # For cardinality=many scenarios, each event points to the common
        # metadata of all the events.
        if event_arr[0].metadata == {}:
            raise Exception(
                "Event metadata is missing from function invocation")

        self._reset_state()
        is_first_observation = True
        for e in event_arr:
            try:
                raw_data = json.loads(e.get_body().decode())
            except:
                raise Exception("Event data is not a valid JSON")
            # Data could be a list of records in the format of {"records": [...]}
            # In this case, we break it down into multiple observations.
            is_json_list = ("records" in raw_data and type(
                raw_data["records"]) is list)
            for r in raw_data["records"] if is_json_list else [raw_data]:
                if is_first_observation is False:
                    self.buf.write(",")
                else:
                    is_first_observation = False

                self.buf.write(json.dumps(r, separators=(',', ':')))
                self.num_obs += 1
                # Buffer size is above threshold.
                if self.buf.tell() >= self.max_req_size_byte:
                    self.event_metadata = event_arr[0].metadata
                    await self._wrap_buffer_and_send_request()
                    self._reset_state()
                    is_first_observation = True

        if self.num_obs > 0:
            self.event_metadata = event_arr[0].metadata
            await self._wrap_buffer_and_send_request()

        logging.info(f"[EventHubHandler] {len(event_arr)} events processed.")


async def main(event: func.EventHubEvent):
    # Create a new eventhub handler, or load it from the cache.
    global EVENTHUB_HANDLER
    if EVENTHUB_HANDLER is None:
        EVENTHUB_HANDLER = EventHubHandler()

    try:
        await EVENTHUB_HANDLER.process_events(event)
    except Exception as e:
        logging.critical(f"[EventHubHandler] {str(e)}")
        exit(-1)
    except:
        logging.critical(
            "[EventHubHandler] Unknown error processing the events")
        exit(-1)
