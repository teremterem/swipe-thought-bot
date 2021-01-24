import os
import uuid

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.dynamodb import dynamodb, put_ddb_item
from functions.common.s3 import put_s3_object, main_bucket

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
RECEIVER_MSG_S3_KEY_KEY = 'receiver_msg_s3_key'

message_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)


def transmit_message(
        swiper_update,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot,
):
    sender_msg_id = int(swiper_update.ptb_update.effective_message.message_id)
    sender_chat_id = int(swiper_update.ptb_update.effective_chat.id)
    sender_bot_id = int(sender_bot_id)

    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot.id)

    text = swiper_update.ptb_update.effective_message.text
    msg = receiver_bot.send_message(
        chat_id=receiver_chat_id,
        text=text,
    )
    receiver_msg_id = int(msg.message_id)

    msg_transmission_id = str(uuid.uuid4())

    receiver_msg_s3_key = f"{swiper_update.update_s3_key_prefix}.transmission.{msg_transmission_id}.json"
    put_s3_object(
        s3_bucket=main_bucket,
        key=receiver_msg_s3_key,
        obj_dict=msg.to_dict(),
    )

    msg_transmission = {
        MSG_TRANS_ID_KEY: msg_transmission_id,

        SENDER_MSG_ID_KEY: sender_msg_id,
        SENDER_CHAT_ID_KEY: sender_chat_id,
        SENDER_BOT_ID_KEY: sender_bot_id,

        RECEIVER_MSG_ID_KEY: receiver_msg_id,
        RECEIVER_CHAT_ID_KEY: receiver_chat_id,
        RECEIVER_BOT_ID_KEY: receiver_bot_id,

        SENDER_UPDATE_S3_KEY_KEY: swiper_update.telegram_update_s3_key,
        RECEIVER_MSG_S3_KEY_KEY: receiver_msg_s3_key,
    }
    put_ddb_item(
        ddb_table=message_transmission_table,
        item=msg_transmission,
    )
