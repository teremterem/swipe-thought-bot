import json
import logging
from pprint import pformat

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from functions.common.constants import ConvState, DataKey, EsKey
from functions.common.s3 import main_bucket
from functions.common.swiper_telegram import BaseSwiperConversation, StateAwareHandlers, BaseSwiperPresentation
from functions.common.utils import send_partitioned_text
from functions.swiper_experiments.swiper_one.thoughts import construct_thought_id
from functions.swiper_experiments.swiper_two.swiper_match import SwiperMatch

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

    def is_swiper_authorized(self):
        # single-threaded environment with non-async update processing
        return bool(self.swiper_update.swiper_chat_data.get(DataKey.IS_SWIPER_AUTHORIZED))

    def get_swiper_match(self):
        # single-threaded environment with non-async update processing
        swiper_match = self.swiper_update.volatile.get(DataKey.SWIPER_MATCH)
        if not swiper_match:
            swiper_match = SwiperMatch()
            self.swiper_update.volatile[DataKey.SWIPER_MATCH] = swiper_match
        return swiper_match


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
        if self.swiper_conversation.is_swiper_authorized():
            self.swiper_presentation.say_hello(update, context)

    def user_thought(self, update, context):
        user_msg_id = update.effective_message.message_id
        chat_id = update.effective_chat.id
        bot_id = context.bot.id

        thought = update.effective_message.text

        if self.swiper_conversation.is_swiper_authorized():
            if thought:
                swiper_match = self.swiper_conversation.get_swiper_match()

                thought_id = construct_thought_id(msg_id=user_msg_id, chat_id=chat_id, bot_id=bot_id)

                # TODO oleksandr: construct body inside SwiperMatch ?
                swiper_match.index_thought(thought, body={
                    EsKey.THOUGHT_ID: thought_id,
                    EsKey.THOUGHT: thought,
                    EsKey.MSG_ID: user_msg_id,
                    EsKey.CHAT_ID: chat_id,
                    EsKey.BOT_ID: bot_id,

                    # single-threaded environment with non-async update processing
                    EsKey.SWIPER_STATE_BEFORE: self.swiper_conversation.swiper_update.swiper_state,

                    EsKey.TELEGRAM_STATE_BEFORE: self.conv_state,
                })

                similar_thought = swiper_match.find_similar_thought(thought)
                send_partitioned_text(update.effective_chat, pformat(similar_thought))

            # bot_msg = self.swiper_presentation.send_thought(update, context, thought)
            #
            # context.chat_data[DataKey.LATEST_ANSWER_MSG_ID] = bot_msg.message_id
            # context.chat_data[DataKey.LATEST_MSG_ID] = bot_msg.message_id
            # return ConvState.BOT_REPLIED

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

    def send_thought(self, update, context, thought):
        answer_msg = update.effective_chat.send_message(
            text=thought,
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
