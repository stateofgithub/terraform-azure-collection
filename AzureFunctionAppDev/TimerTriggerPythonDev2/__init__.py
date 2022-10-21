#! /usr/local/bin/python3

import azure.functions as func
import json
import logging
import os

from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from datetime import datetime, timedelta
from observe.utils import BaseHandler


VM_METRICS_HANDLER = None

# TODO: error handling
# TODO：add comments
# add some more metadata into observation table. How many VMs? metadata of each VM (num metrics, timespan config, etc)
# am I using async io correctly?
# TODO: how to configure the timespan?


class VmMetricsHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "VmMetrics"
        self._reset_state()

    async def _list_vms(self) -> list:
        """
        TODO
        """
        list_expand = "createdTime,changedTime,provisioningState"
        list_filter = "resourceType eq 'Microsoft.Compute/virtualMachines'"
        resource_id_arr = []
        for subscription in await self._list_subscriptions():
            sub_name = subscription["displayName"]
            sub_id = subscription["subscriptionId"]
            logging.info(
                f"[VmMetricsHandler] Listing VMs for subscription \"{sub_name}\" ({sub_id}).")

            client = ResourceManagementClient(self.azure_credentials, sub_id)
            for vm in client.resources.list(expand=list_expand, filter=list_filter):
                meta = vm.serialize(keep_readonly=True)
                if meta["provisioningState"] == "Succeeded":
                    resource_id_arr.append(meta["id"])

        return resource_id_arr

    async def fetch_vm_metrics(self) -> None:
        """
        TODO
        """

        # Generate the timespan config used for getting the configs.
        timespan_str = await get_timespan()

        self._reset_state()
        self.buf.write("[")
        for vm_resource_id in await self._list_vms():
            # Format: /subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}
            subscription_id = vm_resource_id.split('/')[2]
            logging.info(
                f"[VmMetricsHandler] Listing metrics for VM: {vm_resource_id}")

            # Fetch the names of all available metrics for this VM resource.
            client = MonitorManagementClient(
                self.azure_credentials, subscription_id)
            metric_names = []
            for metric in client.metric_definitions.list(vm_resource_id):
                metric_names.append(metric.name.value)

            # List metrics API only allows up to 20 metrics per call.
            metric_batch_size = 20
            batched_metric_names = [metric_names[i:i + metric_batch_size]
                                    for i in range(0, len(metric_names), metric_batch_size)]
            for batch in batched_metric_names:
                metrics_data = client.metrics.list(
                    vm_resource_id,
                    metricnames=','.join(batch),
                    aggregation='average',
                    interval='PT1M',
                    timespan=timespan_str,
                )
                print(metrics_data.serialize(keep_readonly=True)) # remove me
                for value in metrics_data.value:
                    self.buf.write(json.dumps(
                        value.serialize(keep_readonly=True), separators=(',', ':')))
                    self.buf.write(",")
                    self.num_obs += 1

            # Buffer size is above threshold.
            if self.buf.tell() >= self.max_req_size_byte:
                await self._wrap_buffer_and_send_request()
                self._reset_state()
                self.buf.write("[")

            logging.info(
                f"[VmMetricsHandler] {len(metric_names)} Metrics processed for VM: {vm_resource_id}")

        if self.num_obs > 0:
            await self._wrap_buffer_and_send_request()
            self._reset_state()


async def get_timespan() -> str:
    """
    Generates the timespan for the query. It is a string with the following
    format 'startDateTime_ISO/endDateTime_ISO'. For example:
    '2022-10-20T22:02:23Z/2022-10-20T23:02:23Z'
    """
    # Optional environment variable specifying how long we should back in time
    # so that the metrics are guaranteed to be available, default is 10 min.
    REWIND_MIN = int(os.getenv("OBSERVE_VM_METRICS_REWIND_MIN") or 10)
    timespan_end = datetime.utcnow() - timedelta(minutes=REWIND_MIN)

    # Delta is parsed from the crontab schedule, it is the number of minutes
    # between each run, minimum is 1.
    # Example: Run once every 5 minutes: '* */5 * * * *'
    crontab_schedule = os.environ["TimerTriggerPythonDev2_schedule"]
    min_schedule = crontab_schedule.split(' ')[1]
    delta = 1 if min_schedule == "*" else int(min_schedule.split('/')[1])
    timespan_begin = timespan_end - timedelta(minutes=delta)

    timespan_str = timespan_begin.strftime(
        "%Y-%m-%dT%H:%M:%SZ") + "/" + timespan_end.strftime("%Y-%m-%dT%H:%M:%SZ")
    return timespan_str

async def main(mytimer: func.TimerRequest) -> None:
    # Create a new VM metrics handler, or load it from the cache.
    global VM_METRICS_HANDLER
    if VM_METRICS_HANDLER is None:
        VM_METRICS_HANDLER = VmMetricsHandler()

    try:
        await VM_METRICS_HANDLER.fetch_vm_metrics()
    except Exception as e:
        logging.critical(f"[VmMetricsHandler] {str(e)}")
        exit(-1)
    except:
        logging.critical(
            "[VmMetricsHandler] Unknown error processing the VM metrics")
        exit(-1)
