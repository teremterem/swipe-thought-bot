import logging
import os
from collections import defaultdict
from typing import Dict, Any, DefaultDict, Tuple, Optional

from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, ConversationHandler, BasePersistence
from telegram.utils.types import ConversationDict

from functions.common.swiper_chat_data import read_swiper_chat_data, write_swiper_chat_data

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']


class ConvState:
    # using plain str constants because json lib doesn't serialize Enum
    ENTRY_STATE = 'ENTRY_STATE'

    USER_REPLIED = 'USER_REPLIED'
    BOT_REPLIED = 'BOT_REPLIED'

    FALLBACK_STATE = 'FALLBACK_STATE'


class SwiperConversation:
    """
    SwiperConversation instances are designed to work only in single-threaded environments that process telegram updates
    sequentially (meaning, no asynchronous processing either). This is due to the way SwiperPersistence is implemented
    which SwiperConversation uses under the hood.
    """

    MAIN_CONV_NAME = 'swiper_main'

    def __init__(self, bot=None, swiper_presentation=None):
        if not bot:
            bot = Bot(TELEGRAM_TOKEN)
        self.bot = bot

        if not swiper_presentation:
            swiper_presentation = SwiperPresentation(swiper_conversation=self)
        self.swiper_presentation = swiper_presentation

        self.swiper_persistence = SwiperPersistence(self)
        self.dispatcher = self._configure_dispatcher()

    def process_update_json(self, update_json):
        update = Update.de_json(update_json, self.bot)

        swiper_chat_data = read_swiper_chat_data(chat_id=update.effective_chat.id, bot_id=self.bot.id)
        self.swiper_persistence.init_from_swiper_chat_data(swiper_chat_data)

        self.dispatcher.process_update(update)

        self.dispatcher.update_persistence()
        self.swiper_persistence.flush()  # this effectively does nothing
        write_swiper_chat_data(swiper_chat_data)

    def _configure_dispatcher(self):
        dispatcher = Dispatcher(
            self.bot,
            None,
            workers=0,
            persistence=self.swiper_persistence,
        )

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
            name=self.MAIN_CONV_NAME,
            persistent=True,
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


class SwiperPersistence(BasePersistence):
    def __init__(self, swiper_conversation):
        super().__init__(
            store_chat_data=True,
            store_user_data=False,
            store_bot_data=False,
        )
        self.swiper_conversation = swiper_conversation

        self.swiper_chat_data = None
        self.current_chat_id = None
        self.swiper_conv_dict = {}

    def init_from_swiper_chat_data(self, swiper_chat_data):
        """
        Here we assume single-threaded environment with sequential (non-async) update processing.
        """
        self.swiper_chat_data = swiper_chat_data
        self.current_chat_id = swiper_chat_data['chat_id']

        # TODO TODO TODO
        self.swiper_conv_dict.clear()
        # self.swiper_conv_dict[(self.current_chat_id,)] = \
        #     self.swiper_conv_state.setdefault('conversations', {}).setdefault(self.MAIN_CONV_NAME, {})

    def get_conversations(self, name: str) -> ConversationDict:
        # TODO TODO TODO
        return self.swiper_conv_dict

    def get_chat_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        """
        Python-telegram-bot framework thinks chat_data dict contains all chats of all users,
        but that's not the case in our environment. We are faking their protocol...
        """
        chat_data = defaultdict(None)  # WARNING! protocol violation

        if self.swiper_chat_data is None:
            current_chat_data = None  # WARNING! protocol violation
        else:
            current_chat_data = self.swiper_chat_data.setdefault('chat_data', {})

        chat_data[self.current_chat_id] = current_chat_data
        return chat_data

    def get_user_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        return None  # WARNING! protocol violation

    def get_bot_data(self) -> Dict[Any, Any]:
        return None  # WARNING! protocol violation

    def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        ...

    def update_chat_data(self, chat_id: int, data: Dict) -> None:
        ...

    def update_user_data(self, user_id: int, data: Dict) -> None:
        ...

    def update_bot_data(self, data: Dict) -> None:
        ...
