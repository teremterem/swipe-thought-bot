import os
from pprint import pformat

from telegram import Update, InlineKeyboardMarkup

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.swiper import SwiperConversation
from functions.common.swiper_chat_data import read_swiper_chat_data
from functions.common.utils import log_event_and_response

logger = logging.getLogger()

swiper_conversation = SwiperConversation()


@log_event_and_response
def webhook(event, context):
    update_json = event['body']
    swiper_conversation.process_update_json(update_json)
    # return

    if logger.isEnabledFor(logging.INFO):
        logger.info('TELEGRAM UPDATE:\n%s', pformat(update_json))
    update = Update.de_json(update_json, swiper_conversation.bot)

    bot_id = swiper_conversation.bot.id
    chat_id = update.effective_chat.id

    telegram_conv_state = read_swiper_chat_data(chat_id=chat_id, bot_id=bot_id)

    latest_answer_msg_id_decimal = telegram_conv_state.get('latest_answer_msg_id')
    latest_answer_msg_id = None
    if latest_answer_msg_id_decimal is not None:
        latest_answer_msg_id = int(latest_answer_msg_id_decimal)

    # TODO oleksandr: latest_msg_id =

    if update.callback_query:
        if update.callback_query.data == 'left_swipe':
            if update.effective_message.message_id == latest_answer_msg_id:
                # TODO oleksandr: it should be latest_msg_id instead
                update.effective_message.delete()
                update.callback_query.answer(text='❌ Rejected💔')
            else:
                update.callback_query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
                )
                update.callback_query.answer(text='❌ Disliked')
        else:
            update.callback_query.edit_message_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
            )
            update.callback_query.answer(text='🖤 Liked')


@log_event_and_response
def set_webhook(event, context):
    webhook_token = os.environ['TELEGRAM_TOKEN'].replace(':', '_')
    url = f"https://{event.get('headers').get('Host')}/{event.get('requestContext').get('stage')}/{webhook_token}"

    # # Uncomment the following line at your own risk... Better not to flash our secret url in logs, right?
    # logger.info('SETTING WEBHOOK IN TELEGRAM: %s', url)

    webhook_set = swiper_conversation.bot.set_webhook(url)

    if webhook_set:
        return {
            'statusCode': 200,
            'body': 'Telegram webhook set successfully!',
        }

    return {
        'statusCode': 400,
        'body': 'FAILED to set telegram webhook!',
    }
