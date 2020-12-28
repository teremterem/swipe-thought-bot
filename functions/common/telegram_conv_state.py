import logging
import os
from pprint import pformat

from .dynamodb import dynamodb

logger = logging.getLogger(__name__)

TELEGRAM_CONV_STATE_DDB_TABLE_NAME = os.environ['TELEGRAM_CONV_STATE_DDB_TABLE_NAME']

telegram_conv_state_table = dynamodb.Table(TELEGRAM_CONV_STATE_DDB_TABLE_NAME)


def init_telegram_conv_state(bot_id, chat_id):
    empty_item = {
        'bot_id': bot_id,
        'chat_id': chat_id,
    }
    response = telegram_conv_state_table.get_item(Key=empty_item)
    if logger.isEnabledFor(logging.INFO):
        logger.info('TELEGRAM CONVERSATION STATE - GET_ITEM (DDB):\n%s', pformat(response))

    item = response.get('Item')
    if not item:
        # does not exist yet
        return empty_item

    return item


def replace_telegram_conv_state(telegram_conv_state):
    # https://stackoverflow.com/questions/43667229/difference-between-dynamodb-putitem-vs-updateitem
    response = telegram_conv_state_table.put_item(Item=telegram_conv_state)
    if logger.isEnabledFor(logging.INFO):
        logger.info('TELEGRAM CONVERSATION STATE - PUT_ITEM (DDB):\n%s', pformat(response))

    return response
