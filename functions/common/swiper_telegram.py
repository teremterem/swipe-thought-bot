import logging
import os
from enum import Enum, auto

import telegram
from telegram.ext import Dispatcher, CommandHandler, ConversationHandler

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']


def configure_telegram_bot():
    return telegram.Bot(TELEGRAM_TOKEN)


class ConvState(Enum):
    ENTRY_STATE = auto()

    USER_REPLIED = auto()
    BOT_REPLIED = auto()

    FALLBACK_STATE = auto()


class SwiperConversation:
    def __init__(self, bot=None, swiper_presentation=None):
        if not bot:
            bot = configure_telegram_bot()
        self.bot = bot

        self.dispatcher = self._configure_dispatcher()

        if not swiper_presentation:
            swiper_presentation = SwiperPresentation(swiper_conversation=self)
        self.swiper_presentation = swiper_presentation

    def process_update_json(self, update_json):
        update = telegram.Update.de_json(update_json, self.bot)
        self.dispatcher.process_update(update)

    def start(self, update, context):
        self.swiper_presentation.say_hello(update, context)

    def _configure_dispatcher(self):
        dispatcher = Dispatcher(self.bot, None, workers=0)

        conv_state_dict = {}
        CommonStateHandlers(ConvState.USER_REPLIED, self).register_state_handlers(conv_state_dict)
        CommonStateHandlers(ConvState.BOT_REPLIED, self).register_state_handlers(conv_state_dict)

        conv_handler = ConversationHandler(
            per_chat=True,
            per_user=False,
            per_message=False,
            entry_points=CommonStateHandlers(ConvState.ENTRY_STATE, self).handlers,
            allow_reentry=False,
            states=conv_state_dict,
            fallbacks=CommonStateHandlers(ConvState.FALLBACK_STATE, self).handlers,
        )
        dispatcher.add_handler(conv_handler)

        return dispatcher


class CommonStateHandlers:
    # TODO oleksandr: split into more abstraction layers to support different kinds of sets of handlers ?
    def __init__(self, conv_state, swiper_conversation):
        self.conv_state = conv_state
        self.swiper_conversation = swiper_conversation

        self.handlers = [
            CommandHandler('start', self.start),
        ]

    def register_state_handlers(self, conv_state_dict):
        conv_state_dict[self.conv_state] = self.handlers

    @property
    def swiper_presentation(self):
        return self.swiper_conversation.swiper_presentation

    def start(self, update, context):
        self.swiper_presentation.say_hello(update, context, self.conv_state)
        return ConvState.BOT_REPLIED


class SwiperPresentation:
    def __init__(self, swiper_conversation=None):
        self.swiper_conversation = swiper_conversation

    @property
    def bot(self):
        return self.swiper_conversation.bot

    def say_hello(self, update, context, conv_state):
        update.effective_chat.send_message(
            f"Hello, human!\n"
            f"The last state of our conversation was: {conv_state}"
        )
