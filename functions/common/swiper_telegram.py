import logging
import os

import telegram
from telegram.ext import Dispatcher, CommandHandler

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']


def configure_telegram_bot():
    return telegram.Bot(TELEGRAM_TOKEN)


class SwiperConversation:
    def __init__(self, bot=None, swiper_presentation=None):
        if not bot:
            bot = configure_telegram_bot()
        self.bot = bot

        self.dispatcher = self._configure_dispatcher()

        if not swiper_presentation:
            swiper_presentation = SwiperPresentation(swiper_conversation=self)
        self.presentation = swiper_presentation

    def process_update_json(self, update_json):
        update = telegram.Update.de_json(update_json, self.bot)
        self.dispatcher.process_update(update)

    def _configure_dispatcher(self):
        dispatcher = Dispatcher(self.bot, None, workers=0)

        dispatcher.add_handler(CommandHandler('start', self.start))

        return dispatcher

    def start(self, update, context):
        self.presentation.say_hello(update, context)


class SwiperPresentation:
    def __init__(self, swiper_conversation=None):
        self.conversation = swiper_conversation

    @property
    def bot(self):
        return self.conversation.bot

    def say_hello(self, update, context):
        update.effective_chat.send_message(
            'Hello, human!'  # How does it feel to be made of meat and not think in ones and zeroes?'
        )
