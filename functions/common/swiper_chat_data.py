# TODO oleksandr: rename to swiper_chat_data
import logging
import os
from pprint import pformat

from .dynamodb import dynamodb

logger = logging.getLogger(__name__)

SWIPER_CHAT_DATA_DDB_TABLE_NAME = os.environ['TELEGRAM_CONV_STATE_DDB_TABLE_NAME']

swiper_chat_data_table = dynamodb.Table(SWIPER_CHAT_DATA_DDB_TABLE_NAME)


def read_swiper_chat_data(chat_id, bot_id):
    empty_item = {
        'chat_id': chat_id,
        'bot_id': bot_id,
    }
    response = swiper_chat_data_table.get_item(Key=empty_item)
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - GET_ITEM (DDB):\n%s', pformat(response))

    item = response.get('Item')
    if not item:
        # does not exist yet
        return empty_item

    return item


def write_swiper_chat_data(swiper_chat_data):
    # https://stackoverflow.com/questions/43667229/difference-between-dynamodb-putitem-vs-updateitem
    response = swiper_chat_data_table.put_item(Item=swiper_chat_data)
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - PUT_ITEM (DDB):\n%s', pformat(response))

    return response
