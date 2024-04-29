import configparser
import json
import re
import logging
import requests
import os, sys
import datetime
from datetime import timezone


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


def query_dataset(bearer_token: str, dataset_id: str, pipeline: str = "", interval: str = "30m") -> list:
    """

    Queries the last 30 minutes (default) of a dataset returning result of query. Uses Observe OpenAPI

    @param bearer_token: bearer token for authorization
    @param dataset_id: dataset_id to query using openAPI query
    @param pipeline: OPAL Pipeline
    @param interval: interval to query dataset, eg:"30m"

    @return: dataset: queried dataset  in json separated by timestamps

    See  https://developer.observeinc.com/#/paths/~1v1~1meta~1export~1query/post
    """

    logger.info("Querying Dataset for Dataset ID: {} for interval {}".format(dataset_id, interval))
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
    params = {
        "interval": interval
    }
    dataset = send_query(bearer_token, query, params, url_extension='/export/query', type='openapi')
    return dataset


def validate_azure_data(source: str, stale_checks_mins: int = 30, query_interval: str = "30m") -> bool:
    """

    :param source: can be 'EventHub`, `ResourceManagement`, `VMMetrics`
    :param stale_checks_mins: how long should difference be between received data and current timestamp
    :param query_interval: default interval to valid from (last 30m default)
    :return: if source is validated from current time (true, false)
    """

    AZURE_DATASET_ID = os.environ.get("AZURE_DATASET_ID")
    OBSERVE_TOKEN_ID = os.environ.get("OBSERVE_TOKEN_ID")
    bearer_token = get_bearer_token()

    current_ts = datetime.datetime.now().timestamp()
    current_ts_ns = int(current_ts * 1e9)
    current_ts_string = datetime.datetime.fromtimestamp(current_ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
 
    logger.info("{}: stale_check_mins is: {} mins".format(source, stale_checks_mins))
    logger.info("{}: query interval is: {}".format(source, query_interval))
    logger.info("{}: Current time is: {}".format(source, current_ts_string))

    pipeline = ''
    if source == "EventHub":
        # OPAL PIPELINE to execute on Dataset
        pipeline = "make_col _ob_datastream_token_id:coalesce(DATASTREAM_TOKEN_ID, string(EXTRA.datastream_token_id))| " \
                   "filter _ob_datastream_token_id = '{}'|" \
                   "filter (string(EXTRA.source) = 'EventHub')| " \
                   "make_col timestamp:parse_timestamp(string(FIELDS.time), 'MM/DD/YYYY HH24:MI:SS')| " \
                   "make_col timestamp:if_null(timestamp,parse_isotime(string(FIELDS.time)))| " \
                   "set_valid_from options(max_time_diff:30m), timestamp|" \
                   "make_col FIELDS:parse_json(string(FIELDS))|" \
                   "make_col source: string(EXTRA.source)|" \
                   "make_col category:string(FIELDS.category)|" \
                   "make_col appName:string(FIELDS.properties.appName)|" \
                   "make_col message:string(FIELDS.properties.message)|" \
                   "make_col time_string:string(FIELDS.time)|" \
                   "pick_col timestamp, time_string, source, category, appName, message|" \
                   "statsby msg_count: count_distinct(message), latest_ts: last_not_null(timestamp), group_by(source)" \
                   "". \
            format(OBSERVE_TOKEN_ID)
    elif source == "ResourceManagement":
        pipeline = "make_col _ob_datastream_token_id:coalesce(DATASTREAM_TOKEN_ID, string(EXTRA.datastream_token_id))| " \
                   "filter _ob_datastream_token_id = '{}'|" \
                   "filter (string(EXTRA.source) = 'ResourceManagement')|" \
                   "make_col source: string(EXTRA.source)|" \
                   "make_col type:string(FIELDS.type)|" \
                   "statsby msg_count: count_distinct(type), latest_ts: last_not_null(BUNDLE_TIMESTAMP), group_by(source)" \
                   "". \
            format(OBSERVE_TOKEN_ID)
    elif source == "VmMetrics":
        pipeline = "make_col _ob_datastream_token_id:coalesce(DATASTREAM_TOKEN_ID, string(EXTRA.datastream_token_id))| " \
                   "filter _ob_datastream_token_id = '{}'|" \
                   "filter (string(EXTRA.source) = 'VmMetrics')| " \
                   "make_col time_string: string(FIELDS.timeseries[0].data[0].timeStamp)|" \
                   "make_col timestamp:parse_isotime(string(FIELDS.timeseries[0].data[0].timeStamp))| " \
                   "set_valid_from options(max_time_diff:30m), timestamp|" \
                   "make_col metric_name:string(FIELDS.name.value)|" \
                   "make_col FIELDS:parse_json(string(FIELDS))|" \
                   "make_col source: string(EXTRA.source)|" \
                   "pick_col timestamp, time_string, source, metric_name|" \
                   "statsby msg_count: count_distinct(metric_name), latest_ts: last_not_null(timestamp), group_by(source)" \
                   "". \
            format(OBSERVE_TOKEN_ID)

    # Query Dataset with pipeline and write results to JSON
    ds = query_dataset(bearer_token=bearer_token, dataset_id=AZURE_DATASET_ID, pipeline=pipeline,
                       interval=query_interval)
    ds_file = "{}.json".format(source)
    with open(ds_file, "w") as json_file:
        json.dump(ds, json_file, indent=4)
    logger.info("{}: JSON data has been saved to {}.json".format(source, source))
    logger.info("{}: {}".format(source, ds))

    # Iterate through ds and determine if pass ofr fail for data staleness check or no data
    for item in ds:
        # Check if entries exist in query windows (pipeline)
        msg_count = int(item["msg_count"])
        if msg_count < 1:
            logger.error("{}: No msg_count entries returned within query window".format(source))
            return False
        else:
            logger.info("{}: > 0 msg_count entries returned within query window".format(source))

        # If entries exist, then check if timestamps are not stale
        latest_ts_data_ns = int(item["latest_ts"])
        latest_ts_data_ns_string = datetime.datetime.fromtimestamp(latest_ts_data_ns / 1E9, timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ')
        
        
        logger.info("{}: Latest time from data is: {}".format(source, latest_ts_data_ns_string))
        difference_minutes = (latest_ts_data_ns - current_ts_ns) * 1E-9 * (1 / 60)

        # Check if the difference is less than or equal to 30 minutes (in nanoseconds)
        if difference_minutes > -stale_checks_mins:
            logger.info("{}: latest_ts_data is less than {} minutes stale".format(source, stale_checks_mins))
            logger.info("{}: Difference in minutes is: {}".format(source, difference_minutes))
            return True

        else:
            logger.error("{}: latest_ts_data is more than {} minutes stale".format(source, stale_checks_mins))
            logger.info("{}: Difference in minutes is: {}".format(source, difference_minutes))
            return False
    # Return False if no entries found
    logger.error("{}: Dataset is empty and has no entries within query window".format(source))
    return False


if __name__ == '__main__':

    
    logger = logging.getLogger(__name__)
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    log_level = logging.INFO

    setup_logger(log_level, log_format)

    eh = validate_azure_data(source='EventHub', stale_checks_mins=30, query_interval="30m")
    rm = validate_azure_data(source='ResourceManagement', stale_checks_mins=30, query_interval="30m")
    vm_metrics = validate_azure_data(source='VmMetrics', stale_checks_mins=30, query_interval="30m")

    if eh is False or rm is False or vm_metrics is False:
        logger.error("One or more sources are not valid")
        logger.error("EventHub: {}".format(eh))
        logger.error("ResourceManagement: {}".format(rm))
        logger.error("VmMetrics: {}".format(vm_metrics))
        sys.exit(1)
    
    logger.info("All sources are valid")
    logger.info("Data Validation Passed for all sources! ")
