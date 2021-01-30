from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, CallbackQueryHandler

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.constants import DataKey, CallbackData
from functions.common.message_transmitter import transmit_message, find_original_transmission, SENDER_CHAT_ID_KEY, \
    SENDER_MSG_ID_KEY
from functions.common.swiper_matcher import find_match_for_swiper
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
        dispatcher.add_handler(MessageHandler(Filters.reply, self.transmit_reply))
        dispatcher.add_handler(MessageHandler(Filters.all, self.start_topic))
        dispatcher.add_handler(CallbackQueryHandler(self.force_reply, pattern=CallbackData.LIKE))

    def start(self, update, context):
        update.effective_chat.send_message(
            text='Привет, мир',
        )

    def start_topic(self, update, context):
        if update.effective_message.text:
            # for swiper_chat_id in get_all_swiper_chat_ids():
            #     if swiper_chat_id != str(update.effective_chat.id):
            matched_swiper_chat_id = find_match_for_swiper(update.effective_chat.id)
            transmit_message(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                sender_bot_id=context.bot.id,
                receiver_chat_id=matched_swiper_chat_id,
                receiver_bot=context.bot,
            )

    def force_reply(self, update, context):
        update.callback_query.answer(text='🖤 Liked')
        update.effective_message.reply_text('Liked')

    def transmit_reply(self, update, context):
        msg_transmission = find_original_transmission(
            receiver_msg_id=update.effective_message.reply_to_message.message_id,
            receiver_chat_id=update.effective_chat.id,
            receiver_bot_id=context.bot.id,
        )
        if msg_transmission:
            transmit_message(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                sender_bot_id=context.bot.id,
                receiver_chat_id=msg_transmission[SENDER_CHAT_ID_KEY],
                receiver_bot=context.bot,  # msg_transmission[SENDER_BOT_ID_KEY] is of no use here
                reply_to_msg_id=msg_transmission[SENDER_MSG_ID_KEY],
            )
