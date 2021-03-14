import copy
import json
import logging
import os

from telegram import Bot, Update
from telegram.ext import Dispatcher

from functions.common.dynamodb import DdbFields
from functions.common.s3 import main_bucket
from functions.common.swiper_chat_data import read_swiper_chat_data, write_swiper_chat_data
from functions.common.utils import generate_uuid

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']


class Swiper:
    def __init__(self, chat_id, bot_id):
        self.chat_id = chat_id
        self.bot_id = bot_id

        self._swiper_data = None
        self._swiper_data_original = None

    @property
    def swiper_data(self):
        if self._swiper_data is None:
            self._swiper_data = read_swiper_chat_data(chat_id=self.chat_id, bot_id=self.bot_id)
            self._swiper_data_original = copy.deepcopy(self._swiper_data)

        return self._swiper_data

    def is_initialized(self):
        return self._swiper_data is not None

    def is_swiper_authorized(self):
        return bool(self.swiper_data.get(DdbFields.IS_SWIPER_AUTHORIZED))

    def persist(self):
        if self.is_initialized() and self._swiper_data != self._swiper_data_original:
            # TODO oleksandr: versioning and optimistic locking ? what for ? chance of conflict is almost non-existent
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
            self.current_swiper.swiper_data[DdbFields.CHAT] = self.ptb_update.effective_chat.to_dict()

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
    sequentially (meaning, no asynchronous processing either).
    """

    def __init__(self, bot=None):
        if not bot:
            bot = Bot(TELEGRAM_TOKEN)
        # self.bot = bot

        self.dispatcher = Dispatcher(
            bot,
            None,
            workers=0,
        )
        self.configure_dispatcher(self.dispatcher)

        self.swiper_update = None

    def configure_dispatcher(self, dispatcher):
        """To be overridden by child classes."""

    def process_update_json(self, update_json):
        # if logger.isEnabledFor(logging.INFO):
        #     logger.info('TELEGRAM UPDATE:\n%s', pformat(update_json))
        with SwiperUpdate(self, update_json) as swiper_update:
            self.dispatcher.process_update(swiper_update.ptb_update)
