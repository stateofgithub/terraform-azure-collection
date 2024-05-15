import os

AZURE_COLLECTION_FUNCTION = os.environ.get("AZURE_COLLECTION_FUNCTION")
OBSERVE_TOKEN_ID = os.environ.get("OBSERVE_TOKEN_ID")

# OPAL PIPELINEs to execute on Dataset

eventhub_pipeline = \
    "make_col _ob_datastream_token_id:coalesce(DATASTREAM_TOKEN_ID, string(EXTRA.datastream_token_id))| " \
    "filter _ob_datastream_token_id = '{}'|" \
    "filter (string(EXTRA.collection_version) = '{}')|" \
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
    "statsby msg_count: count_distinct(message), earliest_ts: first_not_null(timestamp), group_by(source)" \
    "".format(OBSERVE_TOKEN_ID, AZURE_COLLECTION_FUNCTION)

resource_management_pipeline = \
    "make_col _ob_datastream_token_id:coalesce(DATASTREAM_TOKEN_ID, string(EXTRA.datastream_token_id))| " \
    "filter _ob_datastream_token_id = '{}'|" \
    "filter (string(EXTRA.collection_version) = '{}')|" \
    "filter (string(EXTRA.source) = 'ResourceManagement')|" \
    "make_col source: string(EXTRA.source)|" \
    "make_col type:string(FIELDS.type)|" \
    "statsby msg_count: count_distinct(type), earliest_ts: first_not_null(BUNDLE_TIMESTAMP), group_by(source)" \
    "".format(OBSERVE_TOKEN_ID, AZURE_COLLECTION_FUNCTION)

vm_metrics_pipeline = \
    "make_col _ob_datastream_token_id:coalesce(DATASTREAM_TOKEN_ID, string(EXTRA.datastream_token_id))| " \
    "filter _ob_datastream_token_id = '{}'|" \
    "filter (string(EXTRA.collection_version) = '{}')|" \
    "filter (string(EXTRA.source) = 'VmMetrics')| " \
    "make_col time_string: string(FIELDS.timeseries[0].data[0].timeStamp)|" \
    "make_col timestamp:parse_isotime(string(FIELDS.timeseries[0].data[0].timeStamp))| " \
    "make_col metric_name:string(FIELDS.name.value)|" \
    "make_col FIELDS:parse_json(string(FIELDS))|" \
    "make_col source: string(EXTRA.source)|" \
    "statsby msg_count: count_distinct(metric_name), earliest_ts: first_not_null(BUNDLE_TIMESTAMP), group_by(source)" \
    "".format(OBSERVE_TOKEN_ID, AZURE_COLLECTION_FUNCTION)
