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

# Constant URL parameters for the SDK request.
LIST_EXPAND = "createdTime,changedTime,provisioningState"
LIST_FILTER = "resourceType eq 'Microsoft.Compute/virtualMachines'"


class VmMetricsHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        self.source = "VmMetrics"
        self._reset_state()

    async def _list_vms(self) -> list:
        """
        Get the list of resource IDs for all the VMs in all subscriptions.
        The VM must already been provisioned successfully.
        """
        resource_id_arr = []
        for subscription in await self._list_subscriptions():
            sub_serialized = subscription.serialize(keep_readonly=True)
            sub_name = sub_serialized["displayName"]
            sub_id = sub_serialized["subscriptionId"]
            logging.info(
                f"[VmMetricsHandler] Listing VMs for subscription \"{sub_name}\" ({sub_id}).")

            client = ResourceManagementClient(self.azure_credentials, sub_id)

            # Reference: https://learn.microsoft.com/en-us/rest/api/resources/resources/list
            # Apply filter on Azure location.
            list_filter = LIST_FILTER + f" and location eq '{self.azure_client_location}'"

            for vm in client.resources.list(expand=LIST_EXPAND, filter=list_filter):
                meta = vm.serialize(keep_readonly=True)
                if meta["provisioningState"] == "Succeeded":
                    resource_id_arr.append(meta["id"])

        return resource_id_arr

    async def fetch_vm_metrics(self) -> None:
        """
        List all available metrics for each VM, and fetch time series data for
        all those metrics. The timespan depends on the schedule of the timer
        that triggers the function.
        """
        # Used by the request.
        timespan_str = await get_timespan()
        interval = "PT1M"

        self._reset_state()
        is_first_observation = True
        self.vm_metrics_metadata = []
        for vm_resource_id in await self._list_vms():
            # Metadata to append at the end of Observe request.
            apicall_metadata = {
                "ResourceId": vm_resource_id,
                "Cost": 0,
                "Timespan": timespan_str,
                "Interval": interval,
                "StartTimeUtc": datetime.utcnow().isoformat()
            }

            # Parse the subscription ID from the resource ID string.
            # Format: /subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.Compute/virtualMachines/{vm_name}
            subscription_id = vm_resource_id.split('/')[2]
            logging.info(
                f"[VmMetricsHandler] Listing metrics for VM: {vm_resource_id} ({subscription_id})")

            # Fetch the names of all available metrics for this VM resource.
            client = MonitorManagementClient(
                self.azure_credentials, subscription_id)
            metric_names = []
            # Reference: https://learn.microsoft.com/en-us/rest/api/monitor/metric-definitions/list
            for metric in client.metric_definitions.list(vm_resource_id):
                metric_names.append(metric.name.value)

            # Azure's List metrics API only allows up to 20 metrics per GET request.
            metric_batch_size = 20
            batched_metric_names = [metric_names[i:i + metric_batch_size]
                                    for i in range(0, len(metric_names), metric_batch_size)]

            for batch in batched_metric_names:
                # Reference: https://learn.microsoft.com/en-us/rest/api/monitor/metrics/list
                metrics_data = client.metrics.list(
                    vm_resource_id,
                    metricnames=','.join(batch),
                    aggregation='average',
                    interval=interval,
                    timespan=timespan_str,
                )
                # Break down each metrics to a single observation from the JSON.
                for value in metrics_data.value:
                    if is_first_observation is False:
                        self.buf.write(",")
                    else:
                        is_first_observation = False

                    self.buf.write(json.dumps(
                        value.serialize(keep_readonly=True), separators=(',', ':')))
                    self.num_obs += 1

                # Increment the cost for logging purpose.
                apicall_metadata["Cost"] = apicall_metadata["Cost"] + \
                    metrics_data.cost
                apicall_metadata["EndTimeUtc"] = datetime.utcnow().isoformat()

            apicall_metadata["TotalMetrics"] = len(metric_names)
            self.vm_metrics_metadata.append(apicall_metadata)

            # Buffer size is above threshold.
            if self.buf.tell() >= self.max_req_size_byte:
                await self._wrap_buffer_and_send_request()
                self._reset_state()
                is_first_observation = True
                self.vm_metrics_metadata = []

            logging.info(
                f"[VmMetricsHandler] {len(metric_names)} Metrics processed for VM: {vm_resource_id}")

        if self.num_obs > 0:
            await self._wrap_buffer_and_send_request()


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
    crontab_schedule = os.environ["timer_vm_metrics_func_schedule"]
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
