import json
import logging
import os

import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)
logging.basicConfig(level=logging.INFO)

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
        chat_id = update.message.chat.id
        text = update.message.text

        kbd = [[
            InlineKeyboardButton('🖤', callback_data='right_swipe'),
            InlineKeyboardButton('❌', callback_data='left_swipe'),
        ]]
        if text == '/start':
            text = 'Hello, human! How does it feel to be made primarily of meat and not think in ones and zeros?'
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

    webhook_token = os.environ['TELEGRAM'].replace(':', '_')
    url = f"https://{event.get('headers').get('Host')}/{event.get('requestContext').get('stage')}/{webhook_token}"
    webhook_set = bot.set_webhook(url)

    if webhook_set:
        return OK_RESPONSE

    return ERROR_RESPONSE
