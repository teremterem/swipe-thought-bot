import json
import os

import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.telegram_conv_state import init_telegram_conv_state, replace_telegram_conv_state
from functions.common.thoughts import index_thought, answer_thought

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
    """
    Configures the bot with a Telegram Token.

    Returns a bot instance.
    """

    telegram_token = os.environ.get('TELEGRAM_TOKEN')
    if not telegram_token:
        # TODO oleksandr: define generic SwipeThoughtError
        raise NotImplementedError('TELEGRAM_TOKEN env var is not set')

    return telegram.Bot(telegram_token)


def webhook(event, context):
    """
    Runs the Telegram webhook.
    """

    bot = configure_telegram()
    logger.info('Event: {}'.format(event))

    if event.get('httpMethod') == 'POST' and event.get('body'):
        logger.info('Message received')
        update = telegram.Update.de_json(json.loads(event.get('body')), bot)

        bot_id = bot.id
        chat_id = update.effective_chat.id
        msg_id = update.effective_message.message_id
        text = update.effective_message.text  # TODO oleksandr: this works weirdly when update is callback...

        if text == '/start':
            text = 'Hello, human! How does it feel to be made predominantly of meat and not think in ones and zeros?'
            bot.sendMessage(
                chat_id=chat_id,
                text=text,
            )
        elif update.callback_query:
            if update.callback_query.data == 'left_swipe':
                update.callback_query.message.delete()
            else:
                update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
            update.callback_query.answer()
        else:
            telegram_conf_state = init_telegram_conv_state(bot_id=bot_id, chat_id=chat_id)

            index_thought(bot_id=bot_id, chat_id=chat_id, msg_id=msg_id, text=text)

            replace_telegram_conv_state(telegram_conf_state)

            answer = answer_thought(text)

            bot.sendMessage(
                chat_id=chat_id,
                text=answer,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton('🖤', callback_data='right_swipe'),
                    InlineKeyboardButton('❌', callback_data='left_swipe'),
                ]]),
            )

        return OK_RESPONSE

    return ERROR_RESPONSE  # TODO oleksandr: do we really need to let Telegram know that something went wrong ?


def set_webhook(event, context):
    """
    Sets the Telegram bot webhook.
    """
    logger.info('Event: {}'.format(event))
    bot = configure_telegram()

    webhook_token = os.environ['TELEGRAM_TOKEN'].replace(':', '_')
    url = f"https://{event.get('headers').get('Host')}/{event.get('requestContext').get('stage')}/{webhook_token}"
    webhook_set = bot.set_webhook(url)

    if webhook_set:
        return OK_RESPONSE

    return ERROR_RESPONSE
