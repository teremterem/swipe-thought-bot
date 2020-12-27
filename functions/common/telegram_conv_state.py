import logging
import os
from pprint import pformat

from .dynamodb import dynamodb

logger = logging.getLogger(__name__)

TELEGRAM_CONV_STATE_DDB_TABLE_NAME = os.environ['TELEGRAM_CONV_STATE_DDB_TABLE_NAME']

telegram_conv_state_table = dynamodb.Table(TELEGRAM_CONV_STATE_DDB_TABLE_NAME)


def init_telegram_conv_state(chat_id, bot_id):
    empty_item = {
        'chat_id': chat_id,
        'bot_id': bot_id,
    }
    response = telegram_conv_state_table.get_item(Key=empty_item)

    if logger.isEnabledFor(logging.INFO):
        logger.info('TELEGRAM CONVERSATION STATE (DDB get_item response):\n%s', pformat(response))

    item = response.get('Item')
    if not item:
        # does not exist yet
        return empty_item

    return item
