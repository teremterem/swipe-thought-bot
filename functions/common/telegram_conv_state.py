import logging
import os

from .dynamodb import dynamodb

logger = logging.getLogger(__name__)

TELEGRAM_CONV_STATE_DDB_TABLE_NAME = os.environ['TELEGRAM_CONV_STATE_DDB_TABLE_NAME']

telegram_conv_state_table = dynamodb.Table(TELEGRAM_CONV_STATE_DDB_TABLE_NAME)


def get_telegram_conv_state(chat_id, bot_id):
    response = telegram_conv_state_table.get_item(
        Key={
            'chat_id': chat_id,
            'bot_id': bot_id,
        }
    )
    return response['Item']
