import logging

from telegram.ext import CommandHandler

from functions.common.constants import DataKey
from functions.common.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)


class SwiperPrototype(BaseSwiperConversation):
    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(CommandHandler('start', self.start))

    def is_swiper_authorized(self):
        # single-threaded environment with non-async update processing
        return bool(self.swiper_update.swiper_chat_data.get(DataKey.IS_SWIPER_AUTHORIZED))

    def start(self, update, context):
        if not self.is_swiper_authorized():
            return

        update.effective_chat.send_message('hello')
