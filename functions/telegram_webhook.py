import os
from pprint import pformat

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.swiper_telegram import SwiperConversation
from functions.common.swiper_chat_data import read_swiper_chat_data, write_swiper_chat_data
from functions.common.thoughts import Thoughts
from functions.common.utils import log_event_and_response

logger = logging.getLogger()

# TODO oleksandr: do we need to load-test the lambda to make sure this singleton is ok ?
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
    msg_id = update.effective_message.message_id
    text = update.effective_message.text  # TODO oleksandr: this works weirdly when update is callback...

    telegram_conv_state = read_swiper_chat_data(chat_id=chat_id, bot_id=bot_id)

    latest_answer_msg_id_decimal = telegram_conv_state.get('latest_answer_msg_id')
    latest_answer_msg_id = None
    if latest_answer_msg_id_decimal is not None:
        latest_answer_msg_id = int(latest_answer_msg_id_decimal)

    # TODO oleksandr: latest_msg_id =

    if text == '/start':
        text = 'Hello, human! How does it feel to be made of meat and not think in ones and zeroes?'
        swiper_conversation.bot.sendMessage(
            chat_id=chat_id,
            text=text,
        )

    elif update.callback_query:
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

    else:
        thoughts = Thoughts()

        thoughts.index_thought(text=text, msg_id=msg_id, chat_id=chat_id, bot_id=bot_id)

        answer = thoughts.answer_thought(text)

        if answer:
            answer_msg = swiper_conversation.bot.send_message(
                chat_id=chat_id,
                text=answer,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[

                    # TODO oleksandr: red/black heart for girl/boy or human/bot ? I think, latter!
                    #  or maybe more like match / no match... (we don't want to disclose bot or human too early)
                    #  Yes! Match versus No match!
                    InlineKeyboardButton('🖤', callback_data='right_swipe'),

                    InlineKeyboardButton('❌', callback_data='left_swipe'),
                ]]),
            )

            telegram_conv_state['latest_answer_msg_id'] = answer_msg.message_id
            write_swiper_chat_data(telegram_conv_state)

            # if latest_answer_msg_id:
            #     try:
            #         bot.edit_message_reply_markup(
            #             message_id=latest_answer_msg_id,
            #             chat_id=chat_id,
            #             reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
            #         )
            #     except Exception:
            #         logger.info('INLINE KEYBOARD DID NOT SEEM TO NEED REMOVAL', exc_info=True)


@log_event_and_response
def set_webhook(event, context):
    webhook_token = os.environ['TELEGRAM_TOKEN'].replace(':', '_')
    url = f"https://{event.get('headers').get('Host')}/{event.get('requestContext').get('stage')}/{webhook_token}"

    # # Uncomment the following line at your own risk ? Better not to flash our secret url in logs ?
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
