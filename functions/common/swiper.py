# TODO oleksandr: move this module outside of common ?
#  give it a more descriptive name, too ?
#  and also rename swiper_telegram.py to something else ?
import logging
from pprint import pformat

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from .swiper_telegram import BaseSwiperConversation, StateAwareHandlers, BaseSwiperPresentation
from .thoughts import Thoughts, EsKey
from .utils import timestamp_now_ms

logger = logging.getLogger(__name__)

thoughts = Thoughts()


class ConvState:
    # using plain str constants because json lib doesn't serialize Enum
    ENTRY_STATE = 'ENTRY_STATE'

    USER_REPLIED = 'USER_REPLIED'
    BOT_REPLIED = 'BOT_REPLIED'

    FALLBACK_STATE = 'FALLBACK_STATE'


class DataKey:
    LATEST_MSG_ID = 'latest_msg_id'  # this can be either a user thought or a bot answer to it
    LATEST_ANSWER_MSG_ID = 'latest_answer_msg_id'

    THOUGHT_CTX = 'thought_ctx'
    TEXT = 'text'
    THOUGHT_ID = 'thought_id'
    CONV_STATE = 'conv_state'
    TIMESTAMP_MS = 'timestamp_ms'


class SwiperConversation(BaseSwiperConversation):
    def init_swiper_presentation(self, swiper_presentation):
        if not swiper_presentation:
            swiper_presentation = SwiperPresentation(swiper_conversation=self)
        return swiper_presentation

    def configure_dispatcher(self, dispatcher):
        conv_state_dict = {}
        CommonStateHandlers(ConvState.USER_REPLIED, self).register_state_handlers(conv_state_dict)
        CommonStateHandlers(ConvState.BOT_REPLIED, self).register_state_handlers(conv_state_dict)

        conv_handler = ConversationHandler(
            per_chat=True,
            per_user=False,
            per_message=False,
            entry_points=CommonStateHandlers(ConvState.ENTRY_STATE, self).handlers,
            allow_reentry=False,
            states=conv_state_dict,
            fallbacks=CommonStateHandlers(ConvState.FALLBACK_STATE, self).handlers,
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
        self.swiper_presentation.say_hello(update, context, self.conv_state)

    def _append_to_thought_ctx(self, context, text, thought_id, conv_state):
        context.chat_data.setdefault(DataKey.THOUGHT_CTX, []).append({
            DataKey.TEXT: text,
            DataKey.THOUGHT_ID: thought_id,
            DataKey.CONV_STATE: conv_state,
            DataKey.TIMESTAMP_MS: timestamp_now_ms(),
        })

    def _trim_thought_ctx(self, context, max_thought_ctx_len=10):
        chat_data = context.chat_data
        chat_data[DataKey.THOUGHT_CTX] = chat_data.get(DataKey.THOUGHT_CTX, [])[-max_thought_ctx_len:]

    def user_thought(self, update, context):
        bot_id = context.bot.id
        chat_id = update.effective_chat.id
        user_msg_id = update.effective_message.message_id

        text = update.effective_message.text
        thought_id = thoughts.construct_thought_id(msg_id=user_msg_id, chat_id=chat_id, bot_id=bot_id)

        who_replied = ConvState.USER_REPLIED
        self._append_to_thought_ctx(
            context,
            text=text,
            thought_id=thought_id,
            conv_state=who_replied,
        )

        thoughts.index_thought(text=text, thought_id=thought_id)
        answer = thoughts.answer_thought(text)

        if answer:
            answer_text = answer[EsKey.ANSWER]
            answer_thought_id = answer[EsKey.ANSWER_THOUGHT_ID]

            who_replied = ConvState.BOT_REPLIED
            self._append_to_thought_ctx(
                context,
                text=answer_text,
                thought_id=answer_thought_id,
                conv_state=who_replied,
            )

            bot_msg = self.swiper_presentation.answer_thought(update, context, answer_text)

            context.chat_data[DataKey.LATEST_ANSWER_MSG_ID] = bot_msg.message_id
            context.chat_data[DataKey.LATEST_MSG_ID] = bot_msg.message_id
        else:
            context.chat_data[DataKey.LATEST_MSG_ID] = user_msg_id

        self._trim_thought_ctx(context)

        # # Move the following code to SwiperPresentation if you decide to uncomment it...
        # if previous_latest_answer_msg_id:
        #     try:
        #         bot.edit_message_reply_markup(
        #             message_id=latest_answer_msg_id,
        #             chat_id=chat_id,
        #             reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
        #         )
        #     except Exception:
        #         logger.info('INLINE KEYBOARD DID NOT SEEM TO NEED REMOVAL', exc_info=True)

        return who_replied

    def like(self, update, context):
        self.swiper_presentation.like(update, context)

    def dislike(self, update, context):
        if update.effective_message.message_id == context.chat_data.get(DataKey.LATEST_MSG_ID):
            self.swiper_presentation.reject(update, context)
        else:
            self.swiper_presentation.dislike(update, context)


class SwiperPresentation(BaseSwiperPresentation):
    def say_hello(self, update, context, conv_state):
        update.effective_chat.send_message(
            f"Hello, human!\n"
            f"\n"
            f"Current state is: {conv_state}\n"
            f"\n"
            f"{pformat(context.chat_data)}"
        )

    def answer_thought(self, update, context, answer):
        answer_msg = update.effective_chat.send_message(
            text=answer,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[

                # TODO oleksandr: red/black heart for girl/boy or human/bot ? I think, the latter!
                #  or maybe more like match / no match ? (we don't want to disclose bot or human too early, right?)
                #  Yes! Match versus No match!
                InlineKeyboardButton('🖤', callback_data='like'),

                InlineKeyboardButton('❌', callback_data='dislike'),
            ]]),
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
