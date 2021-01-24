import os
import uuid
from pprint import pformat

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.dynamodb import dynamodb, put_ddb_item

logger = logging.getLogger(__name__)

MESSAGE_TRANSMISSION_DDB_TABLE_NAME = os.environ['MESSAGE_TRANSMISSION_DDB_TABLE_NAME']

MSG_TRANS_ID_KEY = 'id'

SENDER_MSG_ID_KEY = 'sender_msg_id'
SENDER_CHAT_ID_KEY = 'sender_chat_id'
SENDER_BOT_ID_KEY = 'sender_bot_id'

RECEIVER_MSG_ID_KEY = 'receiver_msg_id'
RECEIVER_CHAT_ID_KEY = 'receiver_chat_id'
RECEIVER_BOT_ID_KEY = 'receiver_bot_id'

SENDER_UPDATE_S3_KEY_KEY = 'sender_update_s3_key'
RECEIVER_MSG_S3_KEY_KEY = 'receiver_msg_s3_key'  # TODO oleksandr

message_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)


def transmit_message(
        sender_update_s3_key,
        sender_bot_id,
        sender_chat_id,
        sender_msg_id,
        receiver_bot,
        receiver_chat_id,
        text,
):
    sender_bot_id = int(sender_bot_id)
    sender_chat_id = int(sender_chat_id)
    sender_msg_id = int(sender_msg_id)

    receiver_bot_id = int(receiver_bot.id)
    receiver_chat_id = int(receiver_chat_id)

    msg = receiver_bot.send_message(
        chat_id=receiver_chat_id,
        text=text,
    )
    log_bot_msg(msg)

    receiver_msg_id = int(msg.message_id)

    msg_transmission_id = str(uuid.uuid4())
    msg_transmission = {
        MSG_TRANS_ID_KEY: msg_transmission_id,
        SENDER_UPDATE_S3_KEY_KEY: sender_update_s3_key,
        SENDER_MSG_ID_KEY: sender_msg_id,
        SENDER_CHAT_ID_KEY: sender_chat_id,
        SENDER_BOT_ID_KEY: sender_bot_id,
        RECEIVER_MSG_ID_KEY: receiver_msg_id,
        RECEIVER_CHAT_ID_KEY: receiver_chat_id,
        RECEIVER_BOT_ID_KEY: receiver_bot_id,
    }
    put_ddb_item(
        ddb_table=message_transmission_table,
        item=msg_transmission,
    )


def log_bot_msg(msg):
    if logger.isEnabledFor(logging.INFO):
        if msg:
            msg = msg.to_dict()
        logger.info('MESSAGE FROM BOT:\n%s', pformat(msg))
