import json
import logging
import os
from collections import defaultdict
from typing import Dict, Any, DefaultDict, Tuple, Optional

from telegram import Bot, Update
from telegram.ext import Dispatcher, BasePersistence
from telegram.utils.types import ConversationDict

from functions.common.dynamodb import SwiperChatDataFields
from functions.common.s3 import main_bucket
from functions.common.swiper_chat_data import read_swiper_chat_data, write_swiper_chat_data
from functions.common.utils import generate_uuid

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']

SWIPER_STATE_KEY = 'swiper_state'
CHAT_KEY = 'chat'


class Swiper:
    def __init__(self, chat_id, bot_id):
        self.chat_id = chat_id
        self.bot_id = bot_id

        self._swiper_data = None

    @property
    def swiper_data(self):
        if self._swiper_data is None:
            self._swiper_data = read_swiper_chat_data(chat_id=self.chat_id, bot_id=self.bot_id)

        return self._swiper_data

    @property
    def swiper_state(self):
        return self._swiper_data.get(SWIPER_STATE_KEY)

    @swiper_state.setter
    def swiper_state(self, swiper_state):
        self._swiper_data[SWIPER_STATE_KEY] = swiper_state

    def is_initialized(self):
        return self._swiper_data is not None

    def persist(self):
        if self.is_initialized():
            # TODO oleksandr: track changes somehow and persist only if data changed ?
            # TODO oleksandr: versioning and optimistic locking ?
            write_swiper_chat_data(self._swiper_data)


class SwiperUpdate:
    def __init__(self, swiper_conversation, update_json):
        self.swiper_conversation = swiper_conversation

        self.ptb_update = Update.de_json(update_json, self.swiper_conversation.dispatcher.bot)
        self.update_s3_key_prefix = f"audit/upd{self.ptb_update.update_id}_{generate_uuid()}"
        self.telegram_update_s3_key = f"{self.update_s3_key_prefix}.update.json"

        main_bucket.put_object(
            Key=self.telegram_update_s3_key,
            Body=json.dumps(update_json).encode('utf8'),
        )

        self._swipers = {}
        self.current_swiper = self.get_swiper(self.ptb_update.effective_chat.id)

        self.volatile = {}  # to store reusable objects that are scoped to update and aren't to be persisted

    def get_swiper(self, chat_id):
        chat_id_str = str(chat_id)  # let's be sure that chat id is always of the same type when used as a dict key

        swiper = self._swipers.get(chat_id_str)
        if not swiper:
            swiper = Swiper(chat_id=chat_id, bot_id=self.swiper_conversation.dispatcher.bot.id)
            self._swipers[chat_id_str] = swiper

        return swiper

    def persist_swipers(self):
        if self.current_swiper.is_initialized() and self.ptb_update.effective_chat:
            self.current_swiper.swiper_data[CHAT_KEY] = self.ptb_update.effective_chat.to_dict()

        for swiper in self._swipers.values():
            swiper.persist()

    def __enter__(self):
        # single-threaded environment with non-async update processing
        self.swiper_conversation.swiper_update = self

        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.swiper_conversation.swiper_update = None
        self.persist_swipers()


class BaseSwiperConversation:
    """
    BaseSwiperConversation is designed to work only in single-threaded environments that process telegram updates
    sequentially (meaning, no asynchronous processing either). This is due to the way SwiperPersistence (as well as
    SwiperUpdateScope) is implemented which BaseSwiperConversation uses under the hood.
    """

    def __init__(self, bot=None, swiper_presentation=None):
        if not bot:
            bot = Bot(TELEGRAM_TOKEN)
        # self.bot = bot
        self.swiper_presentation = self.init_swiper_presentation(swiper_presentation)

        self.swiper_persistence = SwiperPersistence()
        self.dispatcher = Dispatcher(
            bot,
            None,
            workers=0,
            persistence=self.swiper_persistence,
        )
        self.configure_dispatcher(self.dispatcher)

        self.swiper_update = None

    def init_swiper_presentation(self, swiper_presentation):
        """To be overridden by child classes, if special swiper_presentation initialization is needed."""
        return swiper_presentation

    def configure_dispatcher(self, dispatcher):
        """To be overridden by child classes."""

    def process_update_json(self, update_json):
        # if logger.isEnabledFor(logging.INFO):
        #     logger.info('TELEGRAM UPDATE:\n%s', pformat(update_json))

        with SwiperUpdate(self, update_json) as swiper_update:
            # TODO oleksandr: we don't need this if we are getting rid of ConversationHandler
            #  (why read from DDB for no reason ?)
            #  although, we do read swiper data on every update during assert_swiper_authorized anyway...
            self.swiper_persistence.init_from_swiper_data(swiper_update.current_swiper.swiper_data)

            self.dispatcher.process_update(swiper_update.ptb_update)

            self.dispatcher.update_persistence()
            self.swiper_persistence.flush()  # this effectively does nothing


class StateAwareHandlers:
    def __init__(self, swiper_conversation, conv_state):
        self.swiper_conversation = swiper_conversation
        self.conv_state = conv_state

        self.handlers = self.configure_handlers()

    def configure_handlers(self):
        """To be overridden by child classes."""
        return []

    def register_state_handlers(self, conv_state_dict):
        conv_state_dict[self.conv_state] = self.handlers

    @property
    def swiper_presentation(self):
        return self.swiper_conversation.swiper_presentation


class BaseSwiperPresentation:  # TODO oleksandr: rename this class to SwiperConversationAware ? no, get rid of it
    def __init__(self, swiper_conversation=None):
        self.swiper_conversation = swiper_conversation

    # @property
    # def bot(self):
    #     return self.swiper_conversation.bot


class SwiperPersistence(BasePersistence):
    def __init__(self):
        super().__init__(
            store_chat_data=True,
            store_user_data=False,
            store_bot_data=False,
        )
        self._swiper_data = None
        self._ptb_conversations = {}
        self._ptb_chat_data = defaultdict(dict)

    def insert_bot(self, obj: object) -> object:
        # do not clone dictionaries - we rely on ability to modify dict content when processing telegram update
        return obj

    def replace_bot(cls, obj: object) -> object:
        # do not clone dictionaries - we rely on ability to modify dict content when processing telegram update
        return obj

    def init_from_swiper_data(self, swiper_data):
        """
        SwiperPersistence expects single-threaded environment with sequential (non-async) update processing.
        """
        self._swiper_data = swiper_data
        chat_id = swiper_data[SwiperChatDataFields.CHAT_ID]

        for ptb_conv_states in self._ptb_conversations.values():
            ptb_conv_states.clear()

        for conv_name, swiper_conv_states in swiper_data.setdefault(SwiperChatDataFields.PTB_CONVERSATIONS, {}).items():
            ptb_conv_states = self._ptb_conversations.setdefault(conv_name, {})

            for conv_state_key, swiper_conv_state in swiper_conv_states.items():
                conv_state_key = eval(conv_state_key)  # from str to tuple
                ptb_conv_states[conv_state_key] = swiper_conv_state

        self._ptb_chat_data.clear()
        self._ptb_chat_data[chat_id] = swiper_data.setdefault(SwiperChatDataFields.PTB_CHAT_DATA, {})

    def get_conversations(self, name: str) -> ConversationDict:
        return self._ptb_conversations.setdefault(name, {})

    def update_conversation(self, name: str, key: Tuple[int, ...], new_state: Optional[object]) -> None:
        key = repr(key)  # from tuple to str
        if new_state is None:
            self._swiper_data.get(SwiperChatDataFields.PTB_CONVERSATIONS, {}).get(name, {}).pop(key, None)
        else:
            self._swiper_data.setdefault(SwiperChatDataFields.PTB_CONVERSATIONS, {}).setdefault(name, {})[key] = \
                new_state

    def get_chat_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        return self._ptb_chat_data

    def update_chat_data(self, chat_id: int, data: Dict) -> None:
        # self.ptb_chat_data dict is part of swiper_data and will be persisted automatically when
        # write_swiper_chat_data is called by BaseSwiperConversation - no code is needed here
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
