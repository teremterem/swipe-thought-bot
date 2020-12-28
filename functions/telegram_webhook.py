import json
import os
from pprint import pformat

import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.telegram_conv_state import init_telegram_conv_state, replace_telegram_conv_state
from functions.common.thoughts import index_thought, answer_thought
from functions.common.utils import log_event_and_response, fail_safely

logger = logging.getLogger()

OK_RESPONSE = {
    'statusCode': 200,
    'headers': {'Content-Type': 'application/json'},
    'body': json.dumps('ok')
}
ERROR_RESPONSE = {
    'statusCode': 400,
    'body': json.dumps('Oops, something went wrong!')
}


def configure_telegram():
    telegram_token = os.environ.get('TELEGRAM_TOKEN')
    if not telegram_token:
        # TODO oleksandr: define generic SwipeThoughtError
        raise NotImplementedError('TELEGRAM_TOKEN env var is not set')

    return telegram.Bot(telegram_token)


@log_event_and_response
@fail_safely(static_response=OK_RESPONSE)
def webhook(event, context):
    bot = configure_telegram()

    if event.get('httpMethod') == 'POST' and event.get('body'):
        update_json = json.loads(event.get('body'))
        if logger.isEnabledFor(logging.INFO):
            logger.info('TELEGRAM UPDATE:\n%s', pformat(update_json))
        update = telegram.Update.de_json(update_json, bot)

        bot_id = bot.id
        chat_id = update.effective_chat.id
        msg_id = update.effective_message.message_id
        text = update.effective_message.text  # TODO oleksandr: this works weirdly when update is callback...

        telegram_conv_state = init_telegram_conv_state(chat_id=chat_id, bot_id=bot_id)
        latest_answer_msg_id = int(telegram_conv_state.get('latest_answer_msg_id'))

        if text == '/start':
            text = 'Hello, human! How does it feel to be made of meat and not think in ones and zeroes?'
            bot.sendMessage(
                chat_id=chat_id,
                text=text,
            )

        elif update.callback_query:
            if update.callback_query.data == 'left_swipe':
                if update.effective_message.message_id == latest_answer_msg_id:
                    update.effective_message.delete()
                    update.callback_query.answer(text='💔 Disliked and ❌ rejected')
                else:
                    update.callback_query.edit_message_reply_markup(
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
                    )
                    update.callback_query.answer(text='💔 Disliked')
            else:
                update.callback_query.edit_message_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
                )
                update.callback_query.answer(text='🖤 Liked')

        else:
            index_thought(text=text, msg_id=msg_id, chat_id=chat_id, bot_id=bot_id)

            answer = answer_thought(text)

            answer_msg = bot.send_message(
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
            replace_telegram_conv_state(telegram_conv_state)

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
    bot = configure_telegram()

    webhook_token = os.environ['TELEGRAM_TOKEN'].replace(':', '_')
    url = f"https://{event.get('headers').get('Host')}/{event.get('requestContext').get('stage')}/{webhook_token}"

    # TODO oleksandr: are you sure it is ok to "flash" this url in logs ?
    #  it is ok if INFO level is not displayed in production...
    logger.info('SETTING WEBHOOK IN TELEGRAM: %s', url)

    webhook_set = bot.set_webhook(url)

    if webhook_set:
        return OK_RESPONSE

    return ERROR_RESPONSE
