import os
import uuid

from boto3.dynamodb.conditions import Key, Attr
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.constants import CallbackData
from functions.common.dynamodb import dynamodb, put_ddb_item
from functions.common.s3 import put_s3_object, main_bucket

logger = logging.getLogger(__name__)

MESSAGE_TRANSMISSION_DDB_TABLE_NAME = os.environ['MESSAGE_TRANSMISSION_DDB_TABLE_NAME']

MSG_TRANS_ID_KEY = 'id'
ORIGINAL_MSG_TRANS_ID_KEY = 'original_msg_trans_id'

SENDER_MSG_ID_KEY = 'sender_msg_id'
SENDER_CHAT_ID_KEY = 'sender_chat_id'
SENDER_BOT_ID_KEY = 'sender_bot_id'

RECEIVER_MSG_ID_KEY = 'receiver_msg_id'
RECEIVER_CHAT_ID_KEY = 'receiver_chat_id'
RECEIVER_BOT_ID_KEY = 'receiver_bot_id'

SENDER_UPDATE_S3_KEY_KEY = 'sender_update_s3_key'
RECEIVER_MSG_S3_KEY_KEY = 'receiver_msg_s3_key'

msg_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)


def reply_reject_kbd_markup(red_heart, reject_only=False):
    kbd_row = [InlineKeyboardButton('❌Отвергнуть', callback_data=CallbackData.REJECT)]
    if not reject_only:
        if red_heart:
            heart = '❤️'
        else:
            heart = '🖤'
        kbd_row.insert(0, InlineKeyboardButton(f"{heart}Ответить", callback_data=CallbackData.REPLY))

    kbd_markup = InlineKeyboardMarkup(inline_keyboard=[kbd_row])
    return kbd_markup


def find_original_transmission(
        receiver_msg_id,
        receiver_chat_id,
        receiver_bot_id,
):
    receiver_msg_id = int(receiver_msg_id)
    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot_id)

    # TODO oleksandr: paginate ?
    scan_result = msg_transmission_table.query(
        IndexName='byReceiverMsgId',
        KeyConditionExpression=(
                Key(RECEIVER_MSG_ID_KEY).eq(receiver_msg_id) & Key(RECEIVER_CHAT_ID_KEY).eq(receiver_chat_id)
        ),
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


def find_transmissions_by_sender_msg(
        sender_msg_id,
        sender_chat_id,
        sender_bot_id,
):
    sender_msg_id = int(sender_msg_id)
    sender_chat_id = int(sender_chat_id)
    sender_bot_id = int(sender_bot_id)

    scan_result = msg_transmission_table.query(
        IndexName='bySenderMsgId',
        KeyConditionExpression=(
                Key(SENDER_MSG_ID_KEY).eq(sender_msg_id) & Key(SENDER_CHAT_ID_KEY).eq(sender_chat_id)
        ),
        FilterExpression=Attr(SENDER_BOT_ID_KEY).eq(sender_bot_id),
    )
    if logger.isEnabledFor(logging.INFO):
        logger.info('FIND TRANSMISSION (DDB QUERY RESPONSE):\n%s', scan_result)

    items = scan_result['Items']
    if not items:
        logger.info(
            'FIND TRANSMISSIONS BY SENDER MSG: no DDB results were found for '
            'sender_msg_id=%s ; sender_chat_id=%s ; sender_bot_id=%s',
            sender_msg_id,
            sender_chat_id,
            sender_bot_id,
        )
    return items


def _ptb_transmit(update, receiver_chat_id, receiver_bot, red_heart, reply_to_msg_id):
    if not update.effective_message.text:
        return None

    msg = receiver_bot.send_message(
        chat_id=receiver_chat_id,
        text=update.effective_message.text,
        reply_to_message_id=reply_to_msg_id,
        reply_markup=reply_reject_kbd_markup(
            red_heart=red_heart,
        ),
    )
    return msg


def transmit_message(
        swiper_update,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot,
        red_heart,
        reply_to_msg_id=None,
):
    sender_msg_id = int(swiper_update.ptb_update.effective_message.message_id)
    sender_chat_id = int(swiper_update.ptb_update.effective_chat.id)
    sender_bot_id = int(sender_bot_id)

    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot.id)
    if reply_to_msg_id is not None:
        reply_to_msg_id = int(reply_to_msg_id)

    transmitted_msg = _ptb_transmit(
        update=swiper_update.ptb_update,
        receiver_chat_id=receiver_chat_id,
        receiver_bot=receiver_bot,
        red_heart=red_heart,
        reply_to_msg_id=reply_to_msg_id,
    )
    if not transmitted_msg:
        # message was not transmitted
        return False

    receiver_msg_id = int(transmitted_msg.message_id)

    msg_transmission_id = generate_msg_transmission_id()

    receiver_msg_s3_key = f"{swiper_update.update_s3_key_prefix}.transmission.{msg_transmission_id}.json"
    put_s3_object(
        s3_bucket=main_bucket,
        key=receiver_msg_s3_key,
        obj_dict=transmitted_msg.to_dict(),
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
    return True


def force_reply(original_msg, original_msg_transmission):
    kwargs = {
        'text': original_msg.text,
        'reply_markup': ForceReply(),
    }
    if original_msg.reply_to_message:
        kwargs['reply_to_message_id'] = original_msg.reply_to_message.message_id
    force_reply_msg = original_msg.chat.send_message(**kwargs)

    msg_trans_copy = original_msg_transmission.copy()
    msg_trans_copy[ORIGINAL_MSG_TRANS_ID_KEY] = msg_trans_copy[MSG_TRANS_ID_KEY]
    msg_trans_copy[MSG_TRANS_ID_KEY] = generate_msg_transmission_id()

    msg_trans_copy[RECEIVER_MSG_ID_KEY] = int(force_reply_msg.message_id)
    msg_trans_copy[RECEIVER_CHAT_ID_KEY] = int(force_reply_msg.chat.id)
    msg_trans_copy[RECEIVER_BOT_ID_KEY] = int(force_reply_msg.bot.id)

    put_ddb_item(
        ddb_table=msg_transmission_table,
        item=msg_trans_copy,
    )


def generate_msg_transmission_id():
    msg_transmission_id = str(uuid.uuid4())
    return msg_transmission_id
