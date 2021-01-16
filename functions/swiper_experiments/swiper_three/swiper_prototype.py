import logging
import os
import re

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, RegexHandler, \
    CallbackQueryHandler

from functions.common.constants import DataKey
from functions.common.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)

SWIPER1_CHAT_ID = os.environ['SWIPER1_CHAT_ID']
SWIPER2_CHAT_ID = os.environ['SWIPER2_CHAT_ID']
SWIPER3_CHAT_ID = os.environ['SWIPER3_CHAT_ID']


class Stories:
    SHARE_SEMI_ANONYMOUSLY = 'Меня что-то тревожит и я хочу поделиться этим [полу]анонимно - я [пока-что] не хочу ' \
                             'думать/знать, кому моя мысль будет отправлена.'


class Reactions:
    LIKE_STRANGER_THOUGHT = 'like_stranger_thought'
    REJECT_STRANGER_THOUGHT = 'reject_stranger_thought'
    LIKE_BOT_THOUGHT = 'like_stranger_thought'
    REJECT_BOT_THOUGHT = 'reject_stranger_thought'


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
        dispatcher.add_handler(CallbackQueryHandler(self.reject_stranger_thought,
                                                    pattern=re.escape(Reactions.REJECT_STRANGER_THOUGHT)))

    def share_semi_anonymously(self, update, context):
        context.bot.send_message(
            chat_id=SWIPER2_CHAT_ID,
            text='Вам кто-то написал. Этот кто-то не знает, что написал именно вам, а вы не знаете, кто этот кто-то. '
                 'Система в произвольном порядке выбрала, как получателя, именно вас…\n\n'
                 'Вам знакомы переживания, излитые в сообщении? У вас есть, что ответить (посоветовать)? Или может '
                 'сообщение, которое пришло, вас раздражает (момент неподходящий, либо сообщение просто глупое)?',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton('❤️', callback_data=Reactions.LIKE_STRANGER_THOUGHT),
                    InlineKeyboardButton('❌', callback_data=Reactions.REJECT_STRANGER_THOUGHT),
                ],
                [
                    InlineKeyboardButton('У меня есть, что ответить…', callback_data='like_stranger_thought'),
                ]
            ]),
        )

    def reject_stranger_thought(self, update, context):
        update.effective_message.delete()
        update.callback_query.answer(text='❌ Отвергнуто💔')
        context.bot.send_message(
            chat_id=SWIPER2_CHAT_ID,
            text='<i>Вы больше не получите сообщений от этого человека [как минимум, некоторое время]</i>',
            parse_mode=ParseMode.HTML,
        )
        context.bot.send_message(
            chat_id=SWIPER1_CHAT_ID,
            text='Вам пришел ответ, правда, не от человека (человек его когда-то написал, но не человек его вам сейчас '
                 'отправил). Вам есть, что ответить, или подобранный ответ - глупый?',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton('🖤', callback_data=Reactions.LIKE_STRANGER_THOUGHT),
                    InlineKeyboardButton('❌', callback_data=Reactions.REJECT_STRANGER_THOUGHT),
                ],
                [
                    InlineKeyboardButton('У меня есть, что ответить…', callback_data='like_stranger_thought'),
                ]
            ]),
        )

    def start(self, update, context):
        context.bot.send_message(
            chat_id=SWIPER1_CHAT_ID,
            text='Привет, мир!',
            reply_markup=ReplyKeyboardMarkup([[
                Stories.SHARE_SEMI_ANONYMOUSLY,
            ]]),
        )
