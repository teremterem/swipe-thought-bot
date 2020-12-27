import json
import os
from pprint import pformat

import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.telegram_conv_state import get_telegram_conv_state

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

        chat_id = update.effective_chat.id
        text = update.effective_message.text  # TODO oleksandr: this works weirdly when update is callback...

        telegram_conf_state = get_telegram_conv_state(chat_id, bot.id)

        # text += f"\n\n{pformat(update.effective_chat.to_dict())}\n\n{pformat(update.effective_user.to_dict())}"
        text += f"\n\n{pformat(telegram_conf_state)}"

        kbd = [[
            InlineKeyboardButton('🖤', callback_data='right_swipe'),
            InlineKeyboardButton('❌', callback_data='left_swipe'),
        ]]
        if text == '/start':
            text = 'Hello, human! How does it feel to be made predominantly of meat and not think in ones and zeros?'
            kbd[0] = []

        bot.sendMessage(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=kbd,
            ),
        )
        logger.info('Message sent')

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
