import logging
import re

from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ParseMode
from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, RegexHandler, \
    CallbackQueryHandler

from functions.common.constants import DataKey
from functions.common.swiper_matcher import get_all_swiper_chat_ids, find_match_for_swiper
from functions.common.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)


class Story:
    SHARE_SEMI_ANONYMOUSLY = 'Меня что-то тревожит и я хочу поделиться этим [полу]анонимно - я [пока-что] не хочу ' \
                             'думать/знать, кому моя мысль будет отправлена.'


class Reaction:
    LIKE_STRANGER_THOUGHT = 'like_stranger_thought'
    REJECT_STRANGER_THOUGHT = 'reject_stranger_thought'
    RESPOND_TO_STRANGER = 'respond_to_stranger'

    LIKE_BOT_THOUGHT = 'like_bot_thought'
    REJECT_BOT_THOUGHT = 'reject_bot_thought'
    RESPOND_TO_BOT = 'respond_to_bot'


class ProtoKey:
    SWIPER3_INDEXED_MSG_ID = 'swiper3_indexed_msg_id'


class SwiperPrototype(BaseSwiperConversation):
    def assert_swiper_authorized(self, update, context):
        # single-threaded environment with non-async update processing
        if not self.swiper_update.current_swiper.swiper_data.get(DataKey.IS_SWIPER_AUTHORIZED):
            # https://github.com/python-telegram-bot/python-telegram-bot/issues/849#issuecomment-332682845
            raise DispatcherHandlerStop()

    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(MessageHandler(Filters.all, self.assert_swiper_authorized), -100500)
        # TODO oleksandr: guard CallbackQueryHandler as well ? any other types of handlers not covered ?

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(RegexHandler(re.escape(Story.SHARE_SEMI_ANONYMOUSLY), self.share_semi_anonymously))
        dispatcher.add_handler(CallbackQueryHandler(self.reject_stranger_thought,
                                                    pattern=re.escape(Reaction.REJECT_STRANGER_THOUGHT)))
        dispatcher.add_handler(CallbackQueryHandler(self.respond_to_bot,
                                                    pattern=re.escape(Reaction.RESPOND_TO_BOT)))

        dispatcher.add_handler(MessageHandler(Filters.all, self.todo))
        dispatcher.add_handler(CallbackQueryHandler(self.todo))

    def _seed_chat_history(self, context, chat_id):
        indexed_msg = context.bot.send_message(
            chat_id=chat_id,
            text='<i>Здесь должна быть какая-то переписка между пользователем и ботом, либо пользователем и другими '
                 'пользователями.</i>',
            parse_mode=ParseMode.HTML,
        )
        swiper = self.swiper_update.get_swiper(chat_id)  # single-threaded environment with non-async update processing
        swiper.swiper_data[ProtoKey.SWIPER3_INDEXED_MSG_ID] = indexed_msg.message_id

    def start(self, update, context):
        for swiper_chat_id in get_all_swiper_chat_ids():
            self._seed_chat_history(context, swiper_chat_id)

        update.effective_chat.send_message(
            text='Привет, мир!',
            reply_markup=ReplyKeyboardMarkup(
                [[
                    Story.SHARE_SEMI_ANONYMOUSLY,
                ]],
                one_time_keyboard=True,
            ),
        )

    def share_semi_anonymously(self, update, context):
        matched_swiper_chat_id = find_match_for_swiper(update.effective_chat.id)

        context.bot.send_message(
            chat_id=matched_swiper_chat_id,
            text='Вам кто-то написал. Этот кто-то не знает, что написал именно вам, а вы не знаете, кто этот кто-то. '
                 'Система в произвольном порядке выбрала, как получателя, именно вас.\n'
                 '\n'
                 'Вам знакомы переживания, излитые в сообщении? У вас есть, что ответить (посоветовать)? Или может '
                 'сообщение, которое пришло, вас раздражает (момент неподходящий, либо сообщение просто глупое)?',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton('❤️', callback_data=Reaction.LIKE_STRANGER_THOUGHT),
                    InlineKeyboardButton('❌', callback_data=Reaction.REJECT_STRANGER_THOUGHT),
                ],
                [
                    InlineKeyboardButton('У меня есть, что ответить…', callback_data=Reaction.RESPOND_TO_STRANGER),
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
            text='Вам пришел ответ. Правда, не от человека. Человек его когда-то написал, но не человек его вам сейчас '
                 'отправил.\n'
                 '\n'
                 'Вам есть, что ответить, или подобранный ответ не имеет в этом контексте никакого смысла?',
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton('🖤', callback_data=Reaction.LIKE_BOT_THOUGHT),
                    InlineKeyboardButton('❌', callback_data=Reaction.REJECT_BOT_THOUGHT),
                ],
                [
                    InlineKeyboardButton('У меня есть, что ответить…', callback_data=Reaction.RESPOND_TO_BOT),
                ]
            ]),
        )

    def respond_to_bot(self, update, context):
        reply_to_msg_id = self.swiper_update.get_swiper(SWIPER3_CHAT_ID).swiper_data[ProtoKey.SWIPER3_INDEXED_MSG_ID]

        context.bot.send_message(
            chat_id=SWIPER1_CHAT_ID,
            text='<i>Вы ответили</i>',
            parse_mode=ParseMode.HTML,
        )
        context.bot.send_message(
            chat_id=SWIPER3_CHAT_ID,
            text='Кто-то ответил на вашу старую мысль. Этот кто-то не знает, что написал именно вам, а вы не знаете, '
                 'кто этот кто-то.\n'
                 '\n'
                 'Причина: бот подбросил эту вашу мысль ему как автоматический ответ на что-то, и человек ответил на '
                 'неё.',

            # TODO oleksandr: handle telegram.error.BadRequest: Reply message not found
            reply_to_message_id=str(reply_to_msg_id),

            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton('❤️', callback_data=Reaction.LIKE_STRANGER_THOUGHT),
                    InlineKeyboardButton('❌', callback_data=Reaction.REJECT_STRANGER_THOUGHT),
                ],
                [
                    InlineKeyboardButton('У меня есть, что ответить…', callback_data='stub'),
                ]
            ]),
        )

    def todo(self, update, context):
        update.effective_chat.send_message('TODO')
