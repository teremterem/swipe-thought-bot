import json
import logging
from pprint import pformat

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from functions.common.constants import ConvState, DataKey
from functions.common.s3 import main_bucket
from functions.common.swiper_telegram import BaseSwiperConversation, StateAwareHandlers, BaseSwiperPresentation
from functions.common.utils import send_partitioned_text
from functions.swiper_experiments.swiper_one.swiper_one import is_bot_silent

logger = logging.getLogger(__name__)


class SwiperTwo(BaseSwiperConversation):
    def init_swiper_presentation(self, swiper_presentation):
        if not swiper_presentation:
            swiper_presentation = SwiperPresentationTwo(swiper_conversation=self)
        return swiper_presentation

    def configure_dispatcher(self, dispatcher):
        conv_state_dict = {}
        CommonStateHandlers(self, ConvState.USER_REPLIED).register_state_handlers(conv_state_dict)
        CommonStateHandlers(self, ConvState.BOT_REPLIED).register_state_handlers(conv_state_dict)

        conv_handler = ConversationHandler(
            per_chat=True,
            per_user=False,
            per_message=False,
            entry_points=CommonStateHandlers(self, ConvState.ENTRY_STATE).handlers,
            allow_reentry=False,
            states=conv_state_dict,
            fallbacks=CommonStateHandlers(self, ConvState.FALLBACK_STATE).handlers,
            name='swiper_main',
            persistent=True,
        )
        dispatcher.add_handler(conv_handler)


class CommonStateHandlers(StateAwareHandlers):
    def configure_handlers(self):
        handlers = [
            CommandHandler('start', self.start),
            MessageHandler(Filters.text & ~Filters.command, self.user_thought),
            CallbackQueryHandler(self.like, pattern=r'like'),
            CallbackQueryHandler(self.dislike, pattern=r'dislike'),
        ]
        return handlers

    def start(self, update, context):
        if not is_bot_silent(context):  # TODO oleksandr: change to is_swiper_authorized
            self.swiper_presentation.say_hello(update, context)

    def user_thought(self, update, context):
        user_msg_id = update.effective_message.message_id

        text = update.effective_message.text

        if not is_bot_silent(context):  # TODO oleksandr: change to is_swiper_authorized
            # TODO oleksandr: indexing goes inside this if statement

            bot_msg = self.swiper_presentation.answer_thought(update, context, text)

            context.chat_data[DataKey.LATEST_ANSWER_MSG_ID] = bot_msg.message_id
            context.chat_data[DataKey.LATEST_MSG_ID] = bot_msg.message_id
            return ConvState.BOT_REPLIED

        context.chat_data[DataKey.LATEST_MSG_ID] = user_msg_id
        return ConvState.USER_REPLIED

    def like(self, update, context):
        self.swiper_presentation.like(update, context)

    def dislike(self, update, context):
        if update.effective_message.message_id == context.chat_data.get(DataKey.LATEST_MSG_ID):

            self.swiper_presentation.reject(update, context)

            return ConvState.USER_REPLIED
        else:
            self.swiper_presentation.dislike(update, context)


class SwiperPresentationTwo(BaseSwiperPresentation):
    def say_hello(self, update, context):
        # single-threaded environment with non-async update processing
        swiper_update = self.swiper_conversation.swiper_update

        send_partitioned_text(update.effective_chat, pformat(swiper_update.swiper_chat_data))

    def answer_thought(self, update, context, answer):
        answer_msg = update.effective_chat.send_message(
            text=answer,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[

                # TODO oleksandr: black vs red hearts mean talking to bot vs to another human respectively !
                InlineKeyboardButton('🖤', callback_data='like'),

                InlineKeyboardButton('❌', callback_data='dislike'),
            ]]),
        )
        answer_msg_dict = answer_msg.to_dict()
        if logger.isEnabledFor(logging.INFO):
            logger.info('ANSWER FROM BOT:\n%s', pformat(answer_msg_dict))
        main_bucket.put_object(
            Key=f"audit/{self.swiper_conversation.swiper_update.update_s3_filename_prefix}.bot-answer.json",
            Body=json.dumps(answer_msg_dict).encode('utf8'),
        )
        return answer_msg

    def like(self, update, context):
        update.callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
        )
        update.callback_query.answer(text='🖤 Liked')

    def dislike(self, update, context):
        update.callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
        )
        update.callback_query.answer(text='❌ Disliked')

    def reject(self, update, context):
        update.effective_message.delete()
        update.callback_query.answer(text='❌ Rejected💔')
