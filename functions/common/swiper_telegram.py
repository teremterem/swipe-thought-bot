import logging
import os
from collections import defaultdict
from typing import Dict, Any, DefaultDict, Tuple, Optional

from telegram import Bot, Update
from telegram.ext import Dispatcher, BasePersistence
from telegram.utils.types import ConversationDict

from .swiper_chat_data import read_swiper_chat_data, write_swiper_chat_data, CHAT_ID_KEY, \
    PTB_CONVERSATIONS_KEY, PTB_CHAT_DATA_KEY

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']


class BaseSwiperConversation:
    """
    BaseSwiperConversation is designed to work only in single-threaded environments that process telegram updates
    sequentially (meaning, no asynchronous processing either). This is due to the way SwiperPersistence is implemented
    which SwiperConversation uses under the hood.
    """

    def __init__(self, bot=None, swiper_presentation=None):
        if not bot:
            bot = Bot(TELEGRAM_TOKEN)
        self.bot = bot
        self.swiper_presentation = self.init_swiper_presentation(swiper_presentation)

        self.swiper_persistence = SwiperPersistence()
        self.dispatcher = Dispatcher(
            self.bot,
            None,
            workers=0,
            persistence=self.swiper_persistence,
        )
        self.configure_dispatcher(self.dispatcher)

    def init_swiper_presentation(self, swiper_presentation):
        """To be overridden by child classes, if special swiper_presentation initialization is needed."""
        return swiper_presentation

    def configure_dispatcher(self, dispatcher):
        """To be overridden by child classes."""

    def process_update_json(self, update_json):
        # if logger.isEnabledFor(logging.INFO):
        #     logger.info('TELEGRAM UPDATE:\n%s', pformat(update_json))
        update = Update.de_json(update_json, self.bot)

        swiper_chat_data = read_swiper_chat_data(chat_id=update.effective_chat.id, bot_id=self.bot.id)
        self.swiper_persistence.init_from_swiper_chat_data(swiper_chat_data)

        self.dispatcher.process_update(update)

        self.dispatcher.update_persistence()
        self.swiper_persistence.flush()  # this effectively does nothing
        write_swiper_chat_data(swiper_chat_data)


class StateAwareHandlers:
    def __init__(self, conv_state, swiper_conversation):
        self.conv_state = conv_state
        self.swiper_conversation = swiper_conversation

        self.handlers = self.configure_handlers()

    def configure_handlers(self):
        """To be overridden by child classes."""
        return []

    def register_state_handlers(self, conv_state_dict):
        conv_state_dict[self.conv_state] = self.handlers

    @property
    def swiper_presentation(self):
        return self.swiper_conversation.swiper_presentation


class BaseSwiperPresentation:
    # TODO oleksandr: rename this class to SwiperBotAware ? or SwiperConversationAware ?
    #  or, maybe, get rid of it completely and rely on bot instance from ptb CallbackContext ?
    def __init__(self, swiper_conversation=None):
        self.swiper_conversation = swiper_conversation

    @property
    def bot(self):
        return self.swiper_conversation.bot


class SwiperPersistence(BasePersistence):
    def __init__(self):
        super().__init__(
            store_chat_data=True,
            store_user_data=False,
            store_bot_data=False,
        )
        self._swiper_chat_data = None
        self._ptb_conversations = {}
        self._ptb_chat_data = defaultdict(dict)

    def insert_bot(self, obj: object) -> object:
        # do not clone dictionaries - we rely on ability to modify dict content when processing telegram update
        return obj

    def replace_bot(cls, obj: object) -> object:
        # do not clone dictionaries - we rely on ability to modify dict content when processing telegram update
        return obj

    def init_from_swiper_chat_data(self, swiper_chat_data):
        """
        SwiperPersistence expects single-threaded environment with sequential (non-async) update processing.
        """
        self._swiper_chat_data = swiper_chat_data
        chat_id = swiper_chat_data[CHAT_ID_KEY]

        for ptb_conv_states in self._ptb_conversations.values():
            ptb_conv_states.clear()

        for conv_name, swiper_conv_states in swiper_chat_data.setdefault(PTB_CONVERSATIONS_KEY, {}).items():
            ptb_conv_states = self._ptb_conversations.setdefault(conv_name, {})

            for conv_state_key, swiper_conv_state in swiper_conv_states.items():
                conv_state_key = eval(conv_state_key)  # from str to tuple
                ptb_conv_states[conv_state_key] = swiper_conv_state

        self._ptb_chat_data.clear()
        self._ptb_chat_data[chat_id] = swiper_chat_data.setdefault(PTB_CHAT_DATA_KEY, {})

    def get_conversations(self, name: str) -> ConversationDict:
        return self._ptb_conversations.setdefault(name, {})

    def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        key = repr(key)  # from tuple to str
        if new_state is None:
            self._swiper_chat_data.get(PTB_CONVERSATIONS_KEY, {}).get(name, {}).pop(key, None)
        else:
            self._swiper_chat_data.setdefault(PTB_CONVERSATIONS_KEY, {}).setdefault(name, {})[key] = new_state

    def get_chat_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        return self._ptb_chat_data

    def update_chat_data(self, chat_id: int, data: Dict) -> None:
        # self.ptb_chat_data dict is part of swiper_chat_data and will be persisted automatically when
        # write_swiper_chat_data is called by SwiperConversation - no code is needed here
        ...

    def get_user_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        # TODO oleksandr: implement this ?
        return None  # we are violating ptb protocol to be alerted should ptb actually try to use this data

    def update_user_data(self, user_id: int, data: Dict) -> None:
        ...

    def get_bot_data(self) -> Dict[Any, Any]:
        return None  # we are violating ptb protocol to be alerted should ptb actually try to use this data

    def update_bot_data(self, data: Dict) -> None:
        ...
