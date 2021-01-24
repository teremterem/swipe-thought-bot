import logging
import os
from pprint import pformat

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ['REGION']

dynamodb = boto3.resource('dynamodb', region_name=REGION)


def put_ddb_item(ddb_table, item):
    if logger.isEnabledFor(logging.INFO):
        logger.info('DDB PUT_ITEM (table: %s):\n%s', ddb_table.name, pformat(item))
    response = ddb_table.put_item(Item=item)
    if logger.isEnabledFor(logging.INFO):
        logger.info('DDB PUT_ITEM RESPONSE:\n%s', pformat(response))
