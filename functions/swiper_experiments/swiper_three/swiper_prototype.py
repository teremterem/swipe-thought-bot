import logging
import os
import re

from telegram import ReplyKeyboardMarkup
from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, RegexHandler

from functions.common.constants import DataKey
from functions.common.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)

SWIPER1_CHAT_ID = os.environ['SWIPER1_CHAT_ID']
SWIPER2_CHAT_ID = os.environ['SWIPER2_CHAT_ID']
SWIPER3_CHAT_ID = os.environ['SWIPER3_CHAT_ID']


class Stories:
    SHARE_SEMI_ANONYMOUSLY = 'Меня что-то тревожит и я хочу поделиться этим [полу]анонимно - я [пока-что] не хочу ' \
                             'думать/знать, кому моя мысль будет отправлена.'


class SwiperPrototype(BaseSwiperConversation):
    def assert_swiper_authorized(self, update, context):
        # single-threaded environment with non-async update processing
        if not self.swiper_update.swiper_chat_data.get(DataKey.IS_SWIPER_AUTHORIZED):
            # https://github.com/python-telegram-bot/python-telegram-bot/issues/849#issuecomment-332682845
            raise DispatcherHandlerStop()

    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(MessageHandler(Filters.all, self.assert_swiper_authorized), -1)

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(RegexHandler(re.escape(Stories.SHARE_SEMI_ANONYMOUSLY), self.share_semi_anonymously))

    def share_semi_anonymously(self, update, context):
        context.bot.send_message(
            chat_id=SWIPER1_CHAT_ID,
            text='Ну так иди делись себе… От меня́ что надо?',
            # reply_markup=ReplyKeyboardMarkup([[
            #     SHARE_SEMI_ANONYMOUSLY,
            # ]]),
        )

    def start(self, update, context):
        context.bot.send_message(
            chat_id=SWIPER1_CHAT_ID,
            text='Привет, мир!',
            reply_markup=ReplyKeyboardMarkup([[
                Stories.SHARE_SEMI_ANONYMOUSLY,
            ]]),
        )
