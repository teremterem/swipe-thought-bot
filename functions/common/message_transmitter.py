import os
import uuid

from boto3.dynamodb.conditions import Key, Attr
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.constants import CallbackData
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

msg_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)


def find_original_transmission(
        receiver_msg_id,
        receiver_chat_id,
        receiver_bot_id,
):
    receiver_msg_id = int(receiver_msg_id)
    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot_id)

    scan_result = msg_transmission_table.query(
        IndexName='byReceiverMsgId',
        KeyConditionExpression=
        Key(RECEIVER_MSG_ID_KEY).eq(receiver_msg_id) & Key(RECEIVER_CHAT_ID_KEY).eq(receiver_chat_id),
        FilterExpression=Attr(RECEIVER_BOT_ID_KEY).eq(receiver_bot_id),
    )
    if logger.isEnabledFor(logging.INFO):
        logger.info('FIND ORIGINAL TRANSMISSION (DDB QUERY RESPONSE):\n%s', scan_result)

    if not scan_result['Items']:
        logger.info(
            'FIND ORIGINAL TRANSMISSION: no DDB result was found for '
            'receiver_msg_id=%s ; receiver_chat_id=%s ; receiver_bot_id=%s',
            receiver_msg_id,
            receiver_chat_id,
            receiver_bot_id,
        )
        return None
    if len(scan_result['Items']) > 1:
        logger.warning(
            'FIND ORIGINAL TRANSMISSION: MORE THAN ONE DDB RESULT was found for '
            'receiver_msg_id=%s ; receiver_chat_id=%s ; receiver_bot_id=%s',
            receiver_msg_id,
            receiver_chat_id,
            receiver_bot_id,
        )
    return scan_result['Items'][0]


def transmit_message(
        swiper_update,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot,
        reply_to_msg_id=None,
):
    sender_msg_id = int(swiper_update.ptb_update.effective_message.message_id)
    sender_chat_id = int(swiper_update.ptb_update.effective_chat.id)
    sender_bot_id = int(sender_bot_id)

    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot.id)
    if reply_to_msg_id is not None:
        reply_to_msg_id = int(reply_to_msg_id)

    text = swiper_update.ptb_update.effective_message.text
    msg = receiver_bot.send_message(
        chat_id=receiver_chat_id,
        text=text,
        reply_to_message_id=reply_to_msg_id,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton('❤️', callback_data=CallbackData.LIKE),
            InlineKeyboardButton('❌', callback_data='dislike'),
        ]]),
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
        ddb_table=msg_transmission_table,
        item=msg_transmission,
    )
