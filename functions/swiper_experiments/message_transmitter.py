from pprint import pformat

from boto3.dynamodb.conditions import Key, Attr
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from telegram.error import BadRequest

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.dynamodb import msg_transmission_table, DdbFields, topic_table, subtopic_table, \
    allogrooming_table
from functions.common.s3 import put_s3_object, main_bucket
from functions.common.utils import fail_safely, generate_uuid
from functions.swiper_experiments.constants import CallbackData, Texts, BLACK_HEARTS_ARE_SILENT
from functions.swiper_experiments.swiper_usernames import append_swiper_username

logger = logging.getLogger(__name__)


def transmission_kbd_markup(red_heart, show_share):
    if red_heart:
        heart = Texts.READ_HEART
    else:
        heart = Texts.BLACK_HEART

    kbd_row = [InlineKeyboardButton(f"{heart}{Texts.REPLY}", callback_data=CallbackData.REPLY)]
    if show_share:
        kbd_row.append(InlineKeyboardButton(Texts.SHARE, callback_data=CallbackData.SHARE))
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
                Key(DdbFields.RECEIVER_MSG_ID).eq(receiver_msg_id) &
                Key(DdbFields.RECEIVER_CHAT_ID).eq(receiver_chat_id)
        ),
        FilterExpression=Attr(DdbFields.RECEIVER_BOT_ID).eq(receiver_bot_id),
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
                Key(DdbFields.SENDER_MSG_ID).eq(sender_msg_id) &
                Key(DdbFields.SENDER_CHAT_ID).eq(sender_chat_id)
        ),
        FilterExpression=Attr(DdbFields.SENDER_BOT_ID).eq(sender_bot_id),
    )
    if logger.isEnabledFor(logging.INFO):  # TODO oleksandr: this logging is redundant - get rid of it
        logger.info('FIND TRANSMISSION (DDB QUERY RESPONSE):\n%s', pformat(scan_result))

    items = scan_result['Items']
    if not items:
        logger.info(  # TODO oleksandr: this logging is redundant - get rid of it
            'FIND TRANSMISSIONS BY SENDER MSG: no DDB results were found for '
            'sender_msg_id=%s ; sender_chat_id=%s ; sender_bot_id=%s',
            sender_msg_id,
            sender_chat_id,
            sender_bot_id,
        )
    return items


def create_topic(
        swiper_update,
        msg,
        sender_bot_id,
):
    sender_msg_id = int(msg.message_id)
    sender_chat_id = int(msg.chat_id)
    sender_bot_id = int(sender_bot_id)

    topic_id = generate_uuid()
    topic = {
        DdbFields.ID: topic_id,

        DdbFields.SENDER_MSG_ID: sender_msg_id,
        DdbFields.SENDER_CHAT_ID: sender_chat_id,
        DdbFields.SENDER_BOT_ID: sender_bot_id,

        DdbFields.SENDER_UPDATE_S3_KEY: swiper_update.telegram_update_s3_key,
    }
    topic_table.put_item(
        Item=topic,
    )
    return topic_id


def create_subtopic(
        swiper_update,
        msg,
        sender_bot_id,
        topic_id,
):
    sender_msg_id = int(msg.message_id)
    sender_chat_id = int(msg.chat_id)
    sender_bot_id = int(sender_bot_id)

    subtopic_id = generate_uuid()
    subtopic = {
        DdbFields.ID: subtopic_id,

        DdbFields.SENDER_MSG_ID: sender_msg_id,
        DdbFields.SENDER_CHAT_ID: sender_chat_id,
        DdbFields.SENDER_BOT_ID: sender_bot_id,

        DdbFields.SENDER_UPDATE_S3_KEY: swiper_update.telegram_update_s3_key,

        DdbFields.TOPIC_ID: topic_id,
    }
    subtopic_table.put_item(
        Item=subtopic,
    )
    return subtopic_id


def find_allogrooming(
        sender_chat_id,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot_id,
        topic_id,
):
    sender_chat_id = int(sender_chat_id)
    sender_bot_id = int(sender_bot_id)

    scan_result = allogrooming_table.query(
        IndexName='byTopicAndSender',
        KeyConditionExpression=(
                Key(DdbFields.TOPIC_ID).eq(topic_id) &
                Key(DdbFields.SENDER_CHAT_ID).eq(sender_chat_id)
        ),
        FilterExpression=(
                Attr(DdbFields.SENDER_BOT_ID).eq(sender_bot_id) &
                Attr(DdbFields.RECEIVER_CHAT_ID).eq(receiver_chat_id) &
                Attr(DdbFields.RECEIVER_BOT_ID).eq(receiver_bot_id)
        ),
    )
    if logger.isEnabledFor(logging.INFO):  # TODO oleksandr: this logging is redundant - get rid of it
        logger.info('FIND ALLOGROOMING (DDB QUERY RESPONSE):\n%s', scan_result)

    items = scan_result['Items']
    if items:
        if len(items) > 1:
            logger.warning(
                'FOUND MORE THAN ONE ALLOGROOMING BY TOPIC AND SENDER: '
                'topic_id=%s ; sender_chat_id=%s ; sender_bot_id=%s ; receiver_chat_id=%s ; receiver_bot_id=%s',
                topic_id,
                sender_chat_id,
                sender_bot_id,
                receiver_chat_id,
                receiver_bot_id,
            )
        return items[0]
    return None


def create_allogrooming(
        swiper_update,
        msg,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot_id,
        topic_id,
):
    sender_msg_id = int(msg.message_id)
    sender_chat_id = int(msg.chat_id)
    sender_bot_id = int(sender_bot_id)

    receiver_chat_id = int(receiver_chat_id)
    receiver_bot_id = int(receiver_bot_id)

    allogrooming_id = generate_uuid()
    allogrooming = {
        DdbFields.ID: allogrooming_id,
        DdbFields.TOPIC_ID: topic_id,

        DdbFields.SENDER_MSG_ID: sender_msg_id,
        DdbFields.SENDER_CHAT_ID: sender_chat_id,
        DdbFields.SENDER_BOT_ID: sender_bot_id,

        DdbFields.RECEIVER_CHAT_ID: receiver_chat_id,
        DdbFields.RECEIVER_BOT_ID: receiver_bot_id,

        DdbFields.SENDER_UPDATE_S3_KEY: swiper_update.telegram_update_s3_key,
    }
    allogrooming_table.put_item(
        Item=allogrooming,
    )
    return allogrooming_id


@fail_safely()
def transmit_message(
        swiper_update,
        msg,
        sender_bot_id,
        receiver_chat_id,
        receiver_bot,
        red_heart,
        topic_id,
        disable_notification,
        subtopic_id=None,
        allogrooming_id=None,
        reply_to_msg_id=None,
        reply_to_transmission_id=None,
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
        username_to_append=swiper_update.current_swiper.swiper_username,

        reply_to_message_id=reply_to_msg_id,
        # TODO oleksandr: allow_sending_without_reply=True, ?
        reply_markup=transmission_kbd_markup(
            red_heart=red_heart,
            show_share=red_heart,  # TODO oleksandr: make sure that the message is actually shareable
        ),
        disable_notification=disable_notification,
    )
    if not transmitted_msg:
        # message was not transmitted
        return False

    receiver_msg_id = int(transmitted_msg.message_id)

    msg_transmission_id = generate_uuid()

    receiver_msg_s3_key = f"{swiper_update.update_s3_key_prefix}.transmission.{msg_transmission_id}.json"
    put_s3_object(
        s3_bucket=main_bucket,
        key=receiver_msg_s3_key,
        obj_dict=transmitted_msg.to_dict(),
    )

    msg_transmission = {
        DdbFields.ID: msg_transmission_id,
        DdbFields.TOPIC_ID: topic_id,
        DdbFields.SUBTOPIC_ID: subtopic_id,
        DdbFields.ALLOGROOMING_ID: allogrooming_id,

        DdbFields.SENDER_MSG_ID: sender_msg_id,
        DdbFields.SENDER_CHAT_ID: sender_chat_id,
        DdbFields.SENDER_BOT_ID: sender_bot_id,

        DdbFields.RECEIVER_MSG_ID: receiver_msg_id,
        DdbFields.RECEIVER_CHAT_ID: receiver_chat_id,
        DdbFields.RECEIVER_BOT_ID: receiver_bot_id,

        DdbFields.REPLY_TO_MSG_ID: reply_to_msg_id,
        DdbFields.REPLY_TO_TRANSMISSION_ID: reply_to_transmission_id,

        DdbFields.RED_HEART: red_heart,

        DdbFields.SENDER_UPDATE_S3_KEY: swiper_update.telegram_update_s3_key,
        DdbFields.RECEIVER_MSG_S3_KEY: receiver_msg_s3_key,
    }
    msg_transmission_table.put_item(
        Item=msg_transmission,
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
        username_to_append=None,

        reply_to_message_id=reply_to_msg_id,
        reply_markup=ForceReply(),
        allow_sending_without_reply=True,
        disable_notification=True,
    )

    msg_trans_copy = original_msg_transmission.copy()
    msg_trans_copy[DdbFields.ORIGINAL_MSG_TRANS_ID] = original_msg_transmission[DdbFields.ID]
    msg_trans_copy[DdbFields.ID] = generate_uuid()

    msg_trans_copy[DdbFields.RECEIVER_MSG_ID] = int(force_reply_msg.message_id)
    msg_trans_copy[DdbFields.RECEIVER_CHAT_ID] = int(force_reply_msg.chat.id)
    msg_trans_copy[DdbFields.RECEIVER_BOT_ID] = int(force_reply_msg.bot.id)

    msg_transmission_table.put_item(
        Item=msg_trans_copy,
    )

    # TODO oleksandr: switch to soft deletes ?
    msg_transmission_table.delete_item(
        Key={
            DdbFields.ID: original_msg_transmission[DdbFields.ID],
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


def _ptb_transmit(msg, receiver_chat_id, receiver_bot, username_to_append, **kwargs):
    transmitted_msg = None

    def _append_username_or_dont(_text, _entities):
        if username_to_append:
            return append_swiper_username(_text, _entities, username_to_append)
        return _text, _entities

    if msg.text:
        text, entities = _append_username_or_dont(msg.text, msg.entities)
        transmitted_msg = receiver_bot.send_message(
            chat_id=receiver_chat_id,
            text=text,
            entities=entities,
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

        text, entities = _append_username_or_dont(msg.caption, msg.caption_entities)
        transmitted_msg = receiver_bot.send_photo(
            chat_id=receiver_chat_id,
            photo=biggest_photo,
            caption=text,
            caption_entities=entities,
            **kwargs,
        )

    elif msg.animation:
        text, entities = _append_username_or_dont(msg.caption, msg.caption_entities)
        transmitted_msg = receiver_bot.send_animation(
            chat_id=receiver_chat_id,
            animation=msg.animation,
            caption=text,
            caption_entities=entities,
            **kwargs,
        )

    elif msg.video:
        text, entities = _append_username_or_dont(msg.caption, msg.caption_entities)
        transmitted_msg = receiver_bot.send_video(
            chat_id=receiver_chat_id,
            video=msg.video,
            caption=text,
            caption_entities=entities,
            **kwargs,
        )

    elif msg.audio:
        text, entities = _append_username_or_dont(msg.caption, msg.caption_entities)
        transmitted_msg = receiver_bot.send_audio(
            chat_id=receiver_chat_id,
            audio=msg.audio,
            caption=text,
            caption_entities=entities,
            **kwargs,
        )

    elif msg.video_note:
        transmitted_msg = receiver_bot.send_video_note(
            chat_id=receiver_chat_id,
            video_note=msg.video_note,
            **kwargs,
        )

    elif msg.voice:
        text, entities = _append_username_or_dont(msg.caption, msg.caption_entities)
        transmitted_msg = receiver_bot.send_voice(
            chat_id=receiver_chat_id,
            voice=msg.voice,
            caption=text,
            caption_entities=entities,
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
        text, entities = _append_username_or_dont(msg.caption, msg.caption_entities)
        transmitted_msg = receiver_bot.send_document(
            chat_id=receiver_chat_id,
            document=msg.document,
            caption=text,
            caption_entities=entities,
            **kwargs,
        )

    elif msg.poll:
        transmitted_msg = receiver_bot.forward_message(
            chat_id=receiver_chat_id,
            from_chat_id=msg.chat_id,
            message_id=msg.message_id,
            disable_notification=BLACK_HEARTS_ARE_SILENT,  # poll with a read heart does not make much sense
        )

    return transmitted_msg


@fail_safely()
def edit_transmission(swiper_update, msg, receiver_msg_id, receiver_chat_id, receiver_bot, red_heart, **kwargs):
    receiver_msg_id = int(receiver_msg_id)
    receiver_chat_id = int(receiver_chat_id)

    swiper_username = swiper_update.current_swiper.swiper_username
    edited_msg = None

    if msg.text:
        text, entities = append_swiper_username(msg.text, msg.entities, swiper_username)
        edited_msg = receiver_bot.edit_message_text(
            chat_id=receiver_chat_id,
            message_id=receiver_msg_id,
            text=text,
            entities=entities,
            reply_markup=transmission_kbd_markup(
                red_heart=red_heart,
                show_share=red_heart,  # TODO oleksandr: make sure that the message is actually shareable
            ),
            **kwargs,
        )

    elif msg.caption:
        text, entities = append_swiper_username(msg.caption, msg.caption_entities, swiper_username)
        edited_msg = receiver_bot.edit_message_caption(
            chat_id=receiver_chat_id,
            message_id=receiver_msg_id,
            caption=text,
            caption_entities=entities,
            reply_markup=transmission_kbd_markup(
                red_heart=red_heart,
                show_share=red_heart,  # TODO oleksandr: make sure that the message is actually shareable
            ),
            **kwargs,
        )
        # TODO oleksandr: report to the user somehow that only caption was edited and not the media itself

    return edited_msg
