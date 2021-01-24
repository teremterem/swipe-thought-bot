from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.constants import DataKey
from functions.common.swiper_matcher import get_all_swiper_chat_ids
from functions.common.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)


class SwiperTransparency(BaseSwiperConversation):
    def assert_swiper_authorized(self, update, context):
        # single-threaded environment with non-async update processing
        if not self.swiper_update.current_swiper.swiper_data.get(DataKey.IS_SWIPER_AUTHORIZED):
            # https://github.com/python-telegram-bot/python-telegram-bot/issues/849#issuecomment-332682845
            raise DispatcherHandlerStop()

    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(MessageHandler(Filters.all, self.assert_swiper_authorized), -100500)
        # TODO oleksandr: guard CallbackQueryHandler as well ? any other types of handlers not covered ?

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(MessageHandler(Filters.all, self.todo))

    def start(self, update, context):
        update.effective_chat.send_message(
            text='Привет, мир',
        )

    def todo(self, update, context):
        text = update.effective_message.text
        if text:
            for swiper_chat_id in get_all_swiper_chat_ids():
                if swiper_chat_id != str(update.effective_chat.id):
                    msg = context.bot.send_message(
                        chat_id=swiper_chat_id,
                        text=text,
                    )
                    log_bot_msg(msg)
