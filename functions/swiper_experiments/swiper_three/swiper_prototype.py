import logging
import os

from telegram.ext import CommandHandler

from functions.common.constants import DataKey
from functions.common.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)

SWIPER1_CHAT_ID = os.environ['SWIPER1_CHAT_ID']
SWIPER2_CHAT_ID = os.environ['SWIPER2_CHAT_ID']
SWIPER3_CHAT_ID = os.environ['SWIPER3_CHAT_ID']


class SwiperPrototype(BaseSwiperConversation):
    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(CommandHandler('start', self.start))

    def is_swiper_authorized(self):
        # single-threaded environment with non-async update processing
        return bool(self.swiper_update.swiper_chat_data.get(DataKey.IS_SWIPER_AUTHORIZED))

    def start(self, update, context):
        if not self.is_swiper_authorized():
            return

        context.bot.send_message(
            chat_id=SWIPER1_CHAT_ID,
            text='Hello Swiper One',
        )
        context.bot.send_message(
            chat_id=SWIPER2_CHAT_ID,
            text='Hello Swiper Two',
        )
        context.bot.send_message(
            chat_id=SWIPER3_CHAT_ID,
            text='Hello Swiper Three',
        )
