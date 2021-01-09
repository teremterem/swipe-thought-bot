# TODO oleksandr: move this module outside of common ?
#  give it a more descriptive name, too ?
#  and also rename swiper_telegram.py to something else ?
import json
import logging
from pprint import pformat

from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

from .constants import ConvState, DataKey, EsKey, AnswererMode
from .s3 import main_bucket
from .swiper_telegram import BaseSwiperConversation, StateAwareHandlers, BaseSwiperPresentation
from .thoughts import ThoughtContext, construct_thought_id, Answerer
from .utils import send_partitioned_text

logger = logging.getLogger(__name__)


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


def is_bot_silent(context):
    return context.chat_data.setdefault(DataKey.IS_BOT_SILENT, True)  # don't talk to strangers


class CommonStateHandlers(StateAwareHandlers):  # TODO oleksandr: get rid of this and parent class and use "UpdateScope"
    def configure_handlers(self):
        handlers = [
            CommandHandler('start', self.start),
            MessageHandler(Filters.text & ~Filters.command, self.user_thought),
            CallbackQueryHandler(self.like, pattern=r'like'),
            CallbackQueryHandler(self.dislike, pattern=r'dislike'),
        ]
        return handlers

    def start(self, update, context):
        if not is_bot_silent(context):
            self.swiper_presentation.say_hello(update, context, self.conv_state)

    def user_thought(self, update, context):
        bot_id = context.bot.id
        chat_id = update.effective_chat.id
        user_msg_id = update.effective_message.message_id

        text = update.effective_message.text
        thought_id = construct_thought_id(msg_id=user_msg_id, chat_id=chat_id, bot_id=bot_id)

        thought_ctx = ThoughtContext(context)

        answerer = Answerer()  # TODO oleksandr: introduce some sort of UpdateScope object and move answerer over there
        answerer.index_thought(answer_text=text, answer_thought_id=thought_id, thought_ctx=thought_ctx)

        who_replied = ConvState.USER_REPLIED
        thought_ctx.append_thought(
            text=text,
            thought_id=thought_id,
            msg_id=user_msg_id,
            conv_state=who_replied,
        )

        if is_bot_silent(context):
            answer_dict = None
        else:
            answerer_mode = context.chat_data.setdefault(DataKey.ANSWERER_MODE, AnswererMode.DEFAULT)
            answer_dict = answerer.answer(thought_ctx, answerer_mode)

        if answer_dict:
            answer_text = answer_dict[EsKey.ANSWER]
            answer_thought_id = answer_dict[EsKey.ANSWER_THOUGHT_ID]

            bot_msg = self.swiper_presentation.answer_thought(update, context, answer_text)

            who_replied = ConvState.BOT_REPLIED
            thought_ctx.append_thought(
                text=answer_text,
                thought_id=answer_thought_id,
                msg_id=bot_msg.message_id,
                conv_state=who_replied,
            )

            context.chat_data[DataKey.LATEST_ANSWER_MSG_ID] = bot_msg.message_id
            context.chat_data[DataKey.LATEST_MSG_ID] = bot_msg.message_id
        else:
            context.chat_data[DataKey.LATEST_MSG_ID] = user_msg_id

        thought_ctx.trim_context()

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
            thought_ctx = ThoughtContext(context)

            thought_ctx.reject_latest_thought(validate_msg_id=update.effective_message.message_id)

            previous_state = thought_ctx.get_latest_conv_state()
            if not previous_state:
                # empty previous_state is unlikely
                previous_state = ConversationHandler.END  # I assume this would clear conversation state

            self.swiper_presentation.reject(update, context)

            return previous_state
        else:
            self.swiper_presentation.dislike(update, context)


class SwiperPresentation(BaseSwiperPresentation):
    def say_hello(self, update, context, conv_state):
        thought_ctx_len = len(ThoughtContext(context).get_list())
        send_partitioned_text(
            update.effective_chat,
            f"{pformat(context.chat_data)}\n"
            f"\n"
            f"THOUGHT CTX LENGTH: {thought_ctx_len}\n"
            f"CONVERSATION STATE: {conv_state}"
        )

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
            Key=f"audit/{self.swiper_conversation.update_scope[DataKey.UPDATE_FILENAME]}.bot-answer.json",
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
