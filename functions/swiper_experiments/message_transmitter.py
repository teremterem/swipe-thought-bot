import os
import uuid

from boto3.dynamodb.conditions import Key, Attr
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.error import BadRequest

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.dynamodb import dynamodb, put_ddb_item, delete_ddb_item
from functions.common.s3 import put_s3_object, main_bucket
from functions.common.utils import fail_safely
from functions.swiper_experiments.constants import CallbackData, Text

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

RED_HEART_KEY = 'red_heart'

SENDER_UPDATE_S3_KEY_KEY = 'sender_update_s3_key'
RECEIVER_MSG_S3_KEY_KEY = 'receiver_msg_s3_key'

msg_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)


def reply_stop_kbd_markup(red_heart, stop_only=False):
    # kbd_row = [InlineKeyboardButton(Text.STOP, callback_data=CallbackData.STOP)]
    kbd_row = []
    if not stop_only:
        if red_heart:
            heart = Text.READ_HEART
        else:
            heart = Text.BLACK_HEART
        kbd_row.insert(0, InlineKeyboardButton(f"{heart}{Text.REPLY}", callback_data=CallbackData.REPLY))

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


@fail_safely()
def transmit_message(
        swiper_update,
        msg,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot,
        red_heart,
        reply_to_msg_id=None,
):
    sender_msg_id = int(msg.message_id)
    sender_chat_id = int(msg.chat_id)
    sender_bot_id = int(sender_bot_id)

    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot.id)

    red_heart = bool(red_heart)
    if reply_to_msg_id is not None:
        reply_to_msg_id = int(reply_to_msg_id)

    transmitted_msg = _ptb_transmit(
        msg=msg,
        receiver_chat_id=receiver_chat_id,
        receiver_bot=receiver_bot,

        reply_to_message_id=reply_to_msg_id,
        # TODO oleksandr: allow_sending_without_reply=True, ?
        reply_markup=reply_stop_kbd_markup(
            red_heart=red_heart,
        ),
    )
    if not transmitted_msg:
        # message was not transmitted
        return False

    receiver_msg_id = int(transmitted_msg.message_id)

    msg_transmission_id = str(uuid.uuid4())

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

        RED_HEART_KEY: red_heart,

        SENDER_UPDATE_S3_KEY_KEY: swiper_update.telegram_update_s3_key,
        RECEIVER_MSG_S3_KEY_KEY: receiver_msg_s3_key,
    }
    put_ddb_item(
        ddb_table=msg_transmission_table,
        item=msg_transmission,
    )

    if reply_to_msg_id is not None:
        try:
            # TODO oleksandr: keep "stop" button at least ? no... I don't think so...
            receiver_bot.edit_message_reply_markup(
                chat_id=receiver_chat_id,
                message_id=reply_to_msg_id,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
            )
        except BadRequest:
            logger.warning('Failed to hide inline keyboard', exc_info=True)

    return True


def force_reply(original_msg, original_msg_transmission):
    if original_msg.reply_to_message:
        reply_to_msg_id = original_msg.reply_to_message.message_id
    else:
        reply_to_msg_id = None

    force_reply_msg = _ptb_transmit(
        msg=original_msg,
        receiver_chat_id=original_msg.chat.id,
        receiver_bot=original_msg.bot,

        reply_to_message_id=reply_to_msg_id,
        reply_markup=ForceReply(),
        allow_sending_without_reply=True,
    )

    msg_trans_copy = original_msg_transmission.copy()
    msg_trans_copy[ORIGINAL_MSG_TRANS_ID_KEY] = original_msg_transmission[MSG_TRANS_ID_KEY]
    msg_trans_copy[MSG_TRANS_ID_KEY] = str(uuid.uuid4())

    msg_trans_copy[RECEIVER_MSG_ID_KEY] = int(force_reply_msg.message_id)
    msg_trans_copy[RECEIVER_CHAT_ID_KEY] = int(force_reply_msg.chat.id)
    msg_trans_copy[RECEIVER_BOT_ID_KEY] = int(force_reply_msg.bot.id)

    put_ddb_item(
        ddb_table=msg_transmission_table,
        item=msg_trans_copy,
    )

    # TODO oleksandr: switch to soft deletes ?
    delete_ddb_item(
        ddb_table=msg_transmission_table,
        key={
            MSG_TRANS_ID_KEY: original_msg_transmission[MSG_TRANS_ID_KEY],
        },
    )


def prepare_msg_for_transmission(msg, sender_bot, **kwargs):
    if msg.poll:
        original_msg = msg
        msg = sender_bot.send_poll(
            chat_id=msg.chat_id,
            question=msg.poll.question,
            options=[po.text for po in msg.poll.options],
            is_anonymous=True,  # msg.poll.is_anonymous,
            type=msg.poll.type,
            allows_multiple_answers=msg.poll.allows_multiple_answers,
            correct_option_id=msg.poll.correct_option_id,
            is_closed=False,  # TODO oleksandr: support inline button that closes the poll ?
            disable_notification=True,
            reply_to_message_id=msg.reply_to_message.message_id if msg.reply_to_message else None,
            explanation=msg.poll.explanation,
            open_period=msg.poll.open_period,
            close_date=msg.poll.close_date,
            allow_sending_without_reply=True,
            explanation_entities=msg.poll.explanation_entities,
            **kwargs,
        )
        original_msg.delete()  # TODO oleksandr: make it failsafe ?

    return msg


def _ptb_transmit(msg, receiver_chat_id, receiver_bot, **kwargs):
    transmitted_msg = None

    if msg.text:
        transmitted_msg = receiver_bot.send_message(
            chat_id=receiver_chat_id,
            text=msg.text,
            entities=msg.entities,
            **kwargs,
        )

    elif msg.sticker:
        transmitted_msg = receiver_bot.send_sticker(
            chat_id=receiver_chat_id,
            sticker=msg.sticker,
            **kwargs,
        )

    elif msg.photo:
        biggest_photo = max(msg.photo, key=lambda p: p['file_size'])
        if logger.isEnabledFor(logging.INFO):
            logger.info('BIGGEST PHOTO SIZE:\n%s', biggest_photo.to_dict())
        transmitted_msg = receiver_bot.send_photo(
            chat_id=receiver_chat_id,
            photo=biggest_photo,
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            **kwargs,
        )

    elif msg.animation:
        transmitted_msg = receiver_bot.send_animation(
            chat_id=receiver_chat_id,
            animation=msg.animation,
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            **kwargs,
        )

    elif msg.video:
        transmitted_msg = receiver_bot.send_video(
            chat_id=receiver_chat_id,
            video=msg.video,
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            **kwargs,
        )

    elif msg.audio:
        transmitted_msg = receiver_bot.send_audio(
            chat_id=receiver_chat_id,
            audio=msg.audio,
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            **kwargs,
        )

    elif msg.video_note:
        transmitted_msg = receiver_bot.send_video_note(
            chat_id=receiver_chat_id,
            video_note=msg.video_note,
            **kwargs,
        )

    elif msg.voice:
        transmitted_msg = receiver_bot.send_voice(
            chat_id=receiver_chat_id,
            voice=msg.voice,
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            **kwargs,
        )

    elif msg.location:
        transmitted_msg = receiver_bot.send_location(
            chat_id=receiver_chat_id,
            location=msg.location,
            **kwargs,
        )

    elif msg.contact:
        transmitted_msg = receiver_bot.send_contact(
            chat_id=receiver_chat_id,
            contact=msg.contact,
            **kwargs,
        )

    elif msg.document:
        transmitted_msg = receiver_bot.send_document(
            chat_id=receiver_chat_id,
            document=msg.document,
            caption=msg.caption,
            caption_entities=msg.caption_entities,
            **kwargs,
        )

    elif msg.poll:
        transmitted_msg = receiver_bot.forward_message(
            chat_id=receiver_chat_id,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
        )

    return transmitted_msg


@fail_safely()
def edit_transmission(msg, receiver_msg_id, receiver_chat_id, receiver_bot, red_heart, **kwargs):
    receiver_msg_id = int(receiver_msg_id)
    receiver_chat_id = int(receiver_chat_id)

    edited_msg = None

    if msg.text:
        edited_msg = receiver_bot.edit_message_text(
            chat_id=receiver_chat_id,
            message_id=receiver_msg_id,
            text=msg.text,
            entities=msg.entities,
            reply_markup=reply_stop_kbd_markup(
                red_heart=red_heart,
            ),
            **kwargs,
        )

    # elif msg.caption:
    #     edited_msg = receiver_bot.edit_message_caption(
    #         chat_id=receiver_chat_id,
    #         message_id=receiver_msg_id,
    #         caption=msg.caption,
    #         caption_entities = msg.caption_entities,
    #         reply_markup=reply_stop_kbd_markup(
    #             red_heart=red_heart,
    #         ),
    #         **kwargs,
    #     )
    #     # TODO oleksandr: report to the user somehow that only caption was edited and not the media itself ?

    return edited_msg
