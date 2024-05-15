import configparser
import json
import re
import logging
import requests # type: ignore
import os, sys, json
import datetime
from datetime import timezone
import pipeline_config # type: ignore


# Create a logger instance
def setup_logger(log_level, log_format):
    """
    Setup logger with specified log level and format.

    @param log_level: Logging level (default is DEBUG)
    @param log_format: Logging format (default is '%(asctime)s - %(levelname)s - %(message)s')
    """
    logger.setLevel(log_level)
    formatter = logging.Formatter(log_format)

    # Create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ch.setFormatter(formatter)

    # Add console handler to logger
    logger.addHandler(ch)


def get_bearer_token() -> str:
    """Logins into account and gets bearer token
    @return: bearer_token
    """

    customer_id = os.environ.get("OBSERVE_CUSTOMER")
    domain = os.environ.get("OBSERVE_DOMAIN")
    user_email = os.environ.get("OBSERVE_USER_EMAIL")
    user_password = os.environ.get("OBSERVE_USER_PASSWORD")

    url = f"https://{customer_id}.{domain}/v1/login"

    message = '{"user_email":"$user_email$","user_password":"$user_password$", "tokenName":"terraform-azure-collection"}'
    tokens_to_replace = {
        "$user_email$": user_email,
        "$user_password$": user_password,
    }
    for key, value in tokens_to_replace.items():
        message = message.replace(key, value)

    header = {
        "Content-Type": "application/json",
    }

    response = json.loads(
        requests.post(url, data=message, headers=header, timeout=10).text
    )
    bearer_token = response['access_key']
    return bearer_token


def send_query(bearer_token: str, query: str, params: dict = None, url_extension: str = '',
               type='gql') -> list or object:
    """
    @param bearer_token: generated from credentials
    @param query: graphQL query
    @param params: params for executing a query (startTime, EndTime, interval, paginate)
    @return: response of graphQL query
    """

    customer_id = os.environ.get("OBSERVE_CUSTOMER")
    domain = os.environ.get("OBSERVE_DOMAIN")

    # Set the GraphQL API endpoint URL
    url = f"https://{customer_id}.{domain}/v1/meta{url_extension}"

    # Set the headers (including authentication)
    headers = {
        "Authorization": f"""Bearer {customer_id} {bearer_token}""",
        'Content-Type': 'application/json',
        'Accept': 'application/x-ndjson'
    }

    # Create the request payload for GQL/OpenAPI
    if type == 'gql':
        data = {
            'query': query
        }
    elif type == 'openapi':
        data = json.loads(query)
    else:
        data = {None}
    # Send the POST request
    try:
        response = requests.post(url, json=data, params=params, headers=headers)
        response.raise_for_status()
        # result = response.json()
        if type == 'gql':
            result = response.json()
            logger.debug("Request for query {} successful with status code {}:".format(query, response.status_code))
            logger.debug("Response:{}".format(result))
            return result
        else:
            result = response.text
            json_objects = result.strip().split('\n')
            json_list = []
            if json_objects and result != "":
                for obj in json_objects:
                    json_list.append(json.loads(obj))
            logger.debug("Request for query {} successful with status code {}:".format(query, response.status_code))
            logger.debug("Response:{}".format(json_list))
            return json_list
    except requests.exceptions.HTTPError as err:
        logging.debug(err.request.url)
        logging.debug(err)
        logging.debug(err.response.text)
        return None


def query_dataset(bearer_token: str, dataset_id: str, pipeline: str = "", interval: str = None, startTime: str = None,
                  endTime: str = None) -> list:
    """

    Queries the last 30 minutes (default) of a dataset returning result of query. Uses Observe OpenAPI

    @param bearer_token: bearer token for authorization
    @param dataset_id: dataset_id to query using openAPI query
    @param pipeline: OPAL Pipeline
    @param interval: Length of time window (if start or end is missing). Defaults to 15m (from observe API)
    @param startTime: Beginning of time window as ISO time.
    @param endTime: End of time window as ISO time. Defaults to now.

    @return: dataset: queried dataset  in json separated by timestamps

    See  https://developer.observeinc.com/#/paths/~1v1~1meta~1export~1query/post
    """
    params = {}
    query = """
       {
          "query": {
              "stages":[
                {
                   "input":[
                       {
                       "inputName": "default",
                       "datasetId": "%s"
                      }
                  ],
                  "stageID":"main",
                  "pipeline": "%s"
              }
          ]
        }
      }
      """ % (dataset_id, pipeline)
    if startTime is not None and endTime is not None:
        logger.info("Querying Dataset for Dataset ID: {} for startTime {} and endTime {}".format(dataset_id, startTime,
                                                                                                 endTime))
        params = {
            "startTime": startTime,
            "endTime": endTime
        }
    elif startTime is not None and interval is not None and endTime is None:
        logger.info(
            "Querying Dataset for Dataset ID: {} for startTime {} and interval".format(dataset_id, startTime, interval))
        params = {
            "startTime": startTime,
            "interval": interval
        }
    elif endTime is not None and interval is not None and startTime is None:
        logger.info(
            "Querying Dataset for Dataset ID: {} for interval {} and endTime".format(dataset_id, interval, endTime))
        params = {
            "endTime": startTime,
            "interval": interval
        }
    elif interval is not None and startTime is None and endTime is None:
        logger.info("Querying Dataset for Dataset ID: {} for interval {}".format(dataset_id, interval))
        params = {
            "interval": interval
        }
    else:
        raise ValueError("Invalid interval, startTime or endTime arguments")

    dataset = send_query(bearer_token, query, params, url_extension='/export/query', type='openapi')
    return dataset


def validate_azure_data(source: str, stale_checks_mins: int) -> bool:
    """

    :param source: can be 'EventHub`, `ResourceManagement`, `VMMetrics`
    :param stale_checks_mins: how long should difference be between received data and current query_start_time
    :return: if source is validated from current time (true, false)
    """

    AZURE_DATASET_ID = os.environ.get("AZURE_DATASET_ID")    
    CURRENT_TIME_ISO = os.environ.get("CURRENT_TIME_ISO")

    # Query Start Time: Uses Terraform script finish time as query Start Time
    timestamp_dt = datetime.datetime.strptime(CURRENT_TIME_ISO, '%Y-%m-%dT%H:%M:%S.%fZ')
    unix_timestamp = timestamp_dt.replace(tzinfo=timezone.utc)
    query_start_time_ns = int(unix_timestamp.timestamp() * 1e9)

    # Query End Time: Current Time
    current_ts = datetime.datetime.now().timestamp()
    query_end_time = datetime.datetime.fromtimestamp(current_ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    logger.info("{}: stale_check_mins is: {} mins".format(source, stale_checks_mins))
    logger.info("{}: query_start_time is: {}".format(source, CURRENT_TIME_ISO))
    logger.info("{}: query_end_time is: {}".format(source, query_end_time))

    pipeline = ''
    if source == "EventHub":
        pipeline = pipeline_config.eventhub_pipeline
    elif source == "ResourceManagement":
        pipeline = pipeline_config.resource_management_pipeline
    elif source == "VmMetrics":
        pipeline = pipeline_config.vm_metrics_pipeline

    # Query Dataset with pipeline and write results to JSON
    bearer_token = get_bearer_token()
    ds = query_dataset(bearer_token=bearer_token, dataset_id=AZURE_DATASET_ID, pipeline=pipeline,
                       startTime=CURRENT_TIME_ISO, endTime=query_end_time)
    ds_file = "{}.json".format(source)
    with open(ds_file, "w") as json_file:
        json.dump(ds, json_file, indent=4)
    logger.info("{}: JSON data has been saved to {}.json".format(source, source))
    logger.info("{}: {}".format(source, ds))

    # Iterate through ds and determine if pass or fail for data staleness check or no data
    for item in ds:
        # Check if entries exist in query windows (pipeline)
        msg_count = int(item["msg_count"])
        if msg_count < 1:
            logger.error("{}: No msg_count entries returned within query window".format(source))
            return False
        else:
            logger.info("{}: > 0 msg_count entries returned within query window".format(source))

        # If entries exist, then check if timestamps are not stale
        earliest_ts_data_ns = int(item["earliest_ts"])
        earliest_ts_data_ns_string = datetime.datetime.fromtimestamp(earliest_ts_data_ns / 1E9, timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ')

        logger.info("{}: Earliest time from data is: {}".format(source, earliest_ts_data_ns_string))
        difference_minutes = (earliest_ts_data_ns - query_start_time_ns) * 1E-9 * (1 / 60)

        # Check if the difference is less than to 30 minutes (in nanoseconds)
        # There can be cases where data is few minutes earlier than query window because of valid from timesamp
        # In that case, just check that its 10 mins. Eg: Query Start Time is 4:15pm but earliest timestamp can 4:10pm
        # ^ This just means BUNDLE_TIMESTAMP was 4:15pm but we started getting data already
        if difference_minutes > -10 and difference_minutes < stale_checks_mins:
            logger.info("{}: earliest_ts_data is less than {} minutes stale".format(source, stale_checks_mins))
            logger.info(
                "{}: Difference in minutes (earliest ts - query_start_time) is: {}".format(source, difference_minutes))
            return True

        else:
            logger.error("{}: earliest_ts_data is more than {} minutes stale".format(source, stale_checks_mins))
            logger.info(
                "{}: Difference in minutes (earliest ts - query_start_time) is: {}".format(source, difference_minutes))
            return False
    # Return False if no entries found
    logger.error("{}: Dataset is empty and has no entries within query window".format(source))
    return False


if __name__ == '__main__':

    logger = logging.getLogger(__name__)
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.INFO

    setup_logger(log_level, log_format)


    logger.info("Validating Azure Data")
    logger.info("------------------------------------")
    logger.info("Customer ID: {}".format(os.environ.get("OBSERVE_CUSTOMER")))
    logger.info("Domain: {}".format(os.environ.get("OBSERVE_DOMAIN")))
    logger.info("Dataset ID: {}".format(os.environ.get("AZURE_DATASET_ID")))
    logger.info("Observe Token ID: {}".format(os.environ.get("OBSERVE_TOKEN_ID")))
    logger.info("Azure Collection Function: {}".format(os.environ.get("AZURE_COLLECTION_FUNCTION")))
    logger.info("Terraform Script End Time: {}".format(os.environ.get("CURRENT_TIME_ISO")))
    logger.info("------------------------------------\n")

    eh = validate_azure_data(source='EventHub', stale_checks_mins=30)
    rm = validate_azure_data(source='ResourceManagement', stale_checks_mins=30)
    vm_metrics = validate_azure_data(source='VmMetrics', stale_checks_mins=30)

    if eh is False or rm is False or vm_metrics is False:
        logger.error("One or more sources are not valid")
        logger.error("EventHub: {}".format(eh))
        logger.error("ResourceManagement: {}".format(rm))
        logger.error("VmMetrics: {}".format(vm_metrics))
        sys.exit(1)

    logger.info("All sources are valid")
    logger.info("Data Validation Passed for all sources! ")
