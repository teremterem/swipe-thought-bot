import logging
import os

import telegram

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']


def configure_telegram_bot():
    # TODO oleksandr: does anything else need to be configured ?
    return telegram.Bot(TELEGRAM_TOKEN)


# TODO oleksandr: is this a bad idea to configure global instance of bot ?
bot = configure_telegram_bot()
