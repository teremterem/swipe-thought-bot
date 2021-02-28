import logging
import os
from pprint import pformat

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ['REGION']

SWIPER_CHAT_DATA_DDB_TABLE_NAME = os.environ['SWIPER_CHAT_DATA_DDB_TABLE_NAME']
MESSAGE_TRANSMISSION_DDB_TABLE_NAME = os.environ['MESSAGE_TRANSMISSION_DDB_TABLE_NAME']
TOPIC_DDB_TABLE_NAME = os.environ['TOPIC_DDB_TABLE_NAME']
ALLOGROOMING_DDB_TABLE_NAME = os.environ['ALLOGROOMING_DDB_TABLE_NAME']

dynamodb = boto3.resource('dynamodb', region_name=REGION)

swiper_chat_data_table = dynamodb.Table(SWIPER_CHAT_DATA_DDB_TABLE_NAME)
msg_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)
topic_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)
allogrooming_table = dynamodb.Table(ALLOGROOMING_DDB_TABLE_NAME)


# TODO oleksandr: get rid of put_ddb_item and delete_ddb_item functions - I don't think you need them


def put_ddb_item(ddb_table, item):
    if logger.isEnabledFor(logging.INFO):
        logger.info('DDB PUT_ITEM (table: %s):\n%s', ddb_table.name, pformat(item))
    response = ddb_table.put_item(Item=item)
    if logger.isEnabledFor(logging.INFO):
        logger.info('DDB PUT_ITEM RESPONSE:\n%s', pformat(response))
    return response


def delete_ddb_item(ddb_table, key):
    if logger.isEnabledFor(logging.INFO):
        logger.info('DDB DELETE_ITEM (table: %s):\n%s', ddb_table.name, pformat(key))
    response = ddb_table.delete_item(Key=key)
    if logger.isEnabledFor(logging.INFO):
        logger.info('DDB DELETE_ITEM RESPONSE:\n%s', pformat(response))
    return response
