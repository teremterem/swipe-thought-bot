import logging
import os
from pprint import pformat

from .constants import DataKey, SwiperState
from .dynamodb import dynamodb

logger = logging.getLogger(__name__)

SWIPER_CHAT_DATA_DDB_TABLE_NAME = os.environ['SWIPER_CHAT_DATA_DDB_TABLE_NAME']

CHAT_ID_KEY = 'chat_id'
BOT_ID_KEY = 'bot_id'
PTB_CONVERSATIONS_KEY = 'ptb_conversations'
PTB_CHAT_DATA_KEY = 'ptb_chat_data'

swiper_chat_data_table = dynamodb.Table(SWIPER_CHAT_DATA_DDB_TABLE_NAME)


def read_swiper_chat_data(chat_id, bot_id):
    empty_item = {
        CHAT_ID_KEY: int(chat_id),
        BOT_ID_KEY: int(bot_id),
    }
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - GET_ITEM (DDB) KEY:\n%s', pformat(empty_item))
    response = swiper_chat_data_table.get_item(Key=empty_item)
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - GET_ITEM (DDB):\n%s', pformat(response))

    item = response.get('Item')
    if not item:
        # does not exist yet
        empty_item[DataKey.IS_SWIPER_AUTHORIZED] = False  # don't talk to strangers
        empty_item[DataKey.SWIPER_STATE] = SwiperState.IDLE
        return empty_item

    return item


def write_swiper_chat_data(swiper_chat_data):
    # https://stackoverflow.com/questions/43667229/difference-between-dynamodb-putitem-vs-updateitem
    # TODO oleksandr: implement optimistic locking using conditional DDB writing (and exception if condition not met)
    response = swiper_chat_data_table.put_item(Item=swiper_chat_data)
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - PUT_ITEM (DDB):\n%s', pformat(response))

    return response
