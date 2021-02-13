from traceback import format_exception

from telegram import InlineKeyboardMarkup, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, CallbackQueryHandler

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.constants import CallbackData, Text
from functions.common.message_transmitter import transmit_message, find_original_transmission, SENDER_CHAT_ID_KEY, \
    SENDER_MSG_ID_KEY, reply_stop_kbd_markup, force_reply, find_transmissions_by_sender_msg, RECEIVER_CHAT_ID_KEY, \
    RECEIVER_MSG_ID_KEY, edit_transmission, RED_HEART_KEY
from functions.common.swiper_chat_data import IS_SWIPER_AUTHORIZED_KEY, find_all_active_swiper_chat_ids
from functions.common.swiper_telegram import BaseSwiperConversation
from functions.common.utils import send_partitioned_text

logger = logging.getLogger(__name__)


class SwiperTransparency(BaseSwiperConversation):
    def assert_swiper_authorized(self, update, context):
        # single-threaded environment with non-async update processing
        if not self.swiper_update.current_swiper.swiper_data.get(IS_SWIPER_AUTHORIZED_KEY):
            # https://github.com/python-telegram-bot/python-telegram-bot/issues/849#issuecomment-332682845
            raise DispatcherHandlerStop()

    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(MessageHandler(Filters.all, self.assert_swiper_authorized), -100500)
        # TODO oleksandr: guard CallbackQueryHandler as well ? any other types of handlers not covered ?

        dispatcher.add_handler(CommandHandler('start', self.start))
        dispatcher.add_handler(MessageHandler(
            Filters.update.edited_message | Filters.update.edited_channel_post, self.edit_message
        ))
        dispatcher.add_handler(MessageHandler(Filters.reply, self.transmit_reply))
        dispatcher.add_handler(MessageHandler(Filters.all, self.start_topic))
        dispatcher.add_handler(CallbackQueryHandler(self.force_reply, pattern=CallbackData.REPLY))
        dispatcher.add_handler(CallbackQueryHandler(self.stop, pattern=CallbackData.STOP))

        dispatcher.add_error_handler(self.handle_error)

    def start(self, update, context):
        update.effective_chat.send_message(
            text=Text.HELLO,  # TODO oleksandr: come up with a conversation starter ?
            reply_markup=reply_stop_kbd_markup(
                red_heart=False,
            ),
        )

    def start_topic(self, update, context):
        transmitted = False
        for swiper_chat_id in find_all_active_swiper_chat_ids(context.bot.id):
            # TODO oleksandr: use thread-workers to broadcast in parallel (remember about Telegram limits too);
            #  as a side effect it should also ensure that one failure doesn't stop the rest of broadcast
            #  (an exception may happen if, for ex., a receiver has blocked the bot)
            if str(swiper_chat_id) != str(update.effective_chat.id):
                transmitted = transmit_message(
                    swiper_update=self.swiper_update,  # non-async single-threaded environment
                    sender_bot_id=context.bot.id,
                    receiver_chat_id=swiper_chat_id,
                    receiver_bot=context.bot,
                    red_heart=False,
                ) or transmitted

        if transmitted:
            update.effective_chat.send_message(
                text=f"<i>{Text.NEW_TOPIC_STARTED}</i>",
                parse_mode=ParseMode.HTML,
                # reply_to_message_id=update.effective_message.message_id,
            )
        else:
            report_msg_not_transmitted(update)

    def edit_message(self, update, context):
        msg = update.effective_message
        transmissions_by_sender_msg = find_transmissions_by_sender_msg(
            sender_msg_id=msg.message_id,
            sender_chat_id=msg.chat.id,
            sender_bot_id=msg.bot.id,
        )

        if not transmissions_by_sender_msg:
            update.effective_chat.send_message(
                text=f"<i>{Text.TALK_NOT_FOUND}</i>",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=msg.message_id,
            )
            return

        red_heart_default = len(transmissions_by_sender_msg) < 2

        edited_at_receiver = True
        for msg_transmission in transmissions_by_sender_msg:
            # broadcast replies to own message

            # TODO oleksandr: use thread-workers to broadcast in parallel (remember about Telegram limits too);
            #  as a side effect it should also ensure that one failure doesn't stop the rest of broadcast
            #  (an exception may happen if, for ex., a receiver has blocked the bot)
            edited_at_receiver = edit_transmission(
                msg=msg,
                receiver_msg_id=msg_transmission[RECEIVER_MSG_ID_KEY],
                receiver_chat_id=msg_transmission[RECEIVER_CHAT_ID_KEY],
                receiver_bot=context.bot,  # msg_transmission[RECEIVER_BOT_ID_KEY] is of no use here
                red_heart=msg_transmission.get(RED_HEART_KEY, red_heart_default),
            ) and edited_at_receiver

        if not edited_at_receiver:
            update.effective_chat.send_message(
                text=f"<i>{Text.FAILED_TO_EDIT_AT_RECEIVER}</i>",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=msg.message_id,
            )

    def force_reply(self, update, context):
        msg_transmission = find_original_transmission_by_msg(update.effective_message)
        if not msg_transmission:
            # update.callback_query.answer()  # TODO oleksandr: make it failsafe
            # update.effective_chat.send_message(
            #     text=f"<i>{TRANSMISSION_NOT_FOUND_TEXT}</i>",
            #     parse_mode=ParseMode.HTML,
            #     reply_to_message_id=update.effective_message.message_id,
            # )
            update.callback_query.answer(text=Text.TALK_NOT_FOUND)
            update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
            return

        update.callback_query.answer()  # TODO oleksandr: make it failsafe
        force_reply(
            original_msg=update.effective_message,
            original_msg_transmission=msg_transmission,
        )
        update.effective_message.delete()

    def stop(self, update, context):
        # TODO oleksandr: delete correspondent transmission(s) as well

        update.effective_message.delete()
        update.callback_query.answer(text=Text.TALK_STOPPED)

        # update.callback_query.answer()  # TODO oleksandr: make it failsafe
        #
        # update.effective_chat.send_message(
        #     text=f"<i></i>",
        #     parse_mode=ParseMode.HTML,
        #     reply_to_message_id=update.effective_message.message_id,
        # )
        # update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))

    def transmit_reply(self, update, context):
        reply_to_msg = update.effective_message.reply_to_message
        try:
            reply_to_msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
        except BadRequest:
            logger.warning('Failed to hide inline keyboard', exc_info=True)

        msg_transmission = find_original_transmission_by_msg(reply_to_msg)
        if msg_transmission:
            if not transmit_message(
                    swiper_update=self.swiper_update,  # non-async single-threaded environment
                    sender_bot_id=context.bot.id,
                    receiver_chat_id=msg_transmission[SENDER_CHAT_ID_KEY],
                    receiver_bot=context.bot,  # msg_transmission[SENDER_BOT_ID_KEY] is of no use here
                    reply_to_msg_id=msg_transmission[SENDER_MSG_ID_KEY],
                    red_heart=True,
            ):
                report_msg_not_transmitted(update)
            return

        transmissions_by_sender_msg = find_transmissions_by_sender_msg(
            sender_msg_id=reply_to_msg.message_id,
            sender_chat_id=reply_to_msg.chat.id,
            sender_bot_id=reply_to_msg.bot.id,
        )

        if not transmissions_by_sender_msg:
            update.effective_chat.send_message(
                text=f"<i>{Text.TALK_NOT_FOUND}</i>",
                parse_mode=ParseMode.HTML,
                reply_to_message_id=update.effective_message.reply_to_message.message_id,
            )
            return

        red_heart = len(transmissions_by_sender_msg) < 2

        transmitted = False
        for msg_transmission in transmissions_by_sender_msg:
            # broadcast replies to own message

            # TODO oleksandr: use thread-workers to broadcast in parallel (remember about Telegram limits too);
            #  as a side effect it should also ensure that one failure doesn't stop the rest of broadcast
            #  (an exception may happen if, for ex., a receiver has blocked the bot)
            transmitted = transmit_message(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                sender_bot_id=context.bot.id,
                receiver_chat_id=msg_transmission[RECEIVER_CHAT_ID_KEY],
                receiver_bot=context.bot,  # msg_transmission[RECEIVER_BOT_ID_KEY] is of no use here
                reply_to_msg_id=msg_transmission[RECEIVER_MSG_ID_KEY],
                red_heart=red_heart,
            ) or transmitted  # TODO oleksandr: replace with "and" as in self.edit_message() handler ?

        if not transmitted:
            report_msg_not_transmitted(update)

    def handle_error(self, update, context):
        logger.error('ERROR IN A PTB HANDLER', exc_info=context.error)

        error_str = ''.join(format_exception(type(context.error), context.error, context.error.__traceback__))
        send_partitioned_text(update.effective_chat, error_str)


def report_msg_not_transmitted(update):
    report_msg = update.effective_chat.send_message(
        text=f"<i>{Text.MESSAGE_NOT_TRANSMITTED}</i>",
        parse_mode=ParseMode.HTML,
        reply_to_message_id=update.effective_message.message_id,
    )
    return report_msg


def find_original_transmission_by_msg(msg):
    msg_transmission = find_original_transmission(
        receiver_msg_id=msg.message_id,
        receiver_chat_id=msg.chat.id,
        receiver_bot_id=msg.bot.id,
    )
    return msg_transmission
