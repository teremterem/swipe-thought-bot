from traceback import format_exception

from telegram import InlineKeyboardMarkup, ParseMode
from telegram.error import BadRequest
from telegram.ext import CommandHandler, DispatcherHandlerStop, Filters, MessageHandler, CallbackQueryHandler

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.dynamodb import DdbFields
from functions.common.swiper_chat_data import find_all_active_swiper_chat_ids
from functions.common.utils import send_partitioned_text
from functions.swiper_experiments.constants import CallbackData, Texts, Commands, BLACK_HEARTS_ARE_SILENT, \
    TransmissionModes
from functions.swiper_experiments.message_transmitter import transmit_message, find_original_transmission, \
    force_reply, find_transmissions_by_sender_msg, edit_transmission, prepare_msg_for_transmission, \
    create_allogrooming, find_allogrooming, create_topic, create_subtopic, \
    find_subtopic_by_sender_msg, extract_transmission_mode
from functions.swiper_experiments.swiper_telegram import BaseSwiperConversation

logger = logging.getLogger(__name__)


class SwiperTransparency(BaseSwiperConversation):
    def assert_swiper_authorized(self, update, context):
        # single-threaded environment with non-async update processing
        if not self.swiper_update.current_swiper.is_swiper_authorized():
            # https://github.com/python-telegram-bot/python-telegram-bot/issues/849#issuecomment-332682845
            raise DispatcherHandlerStop()

    def configure_dispatcher(self, dispatcher):
        dispatcher.add_handler(MessageHandler(Filters.all, self.assert_swiper_authorized), -100500)
        # TODO oleksandr: guard CallbackQueryHandler as well ? any other types of handlers not covered ?

        dispatcher.add_handler(CommandHandler(Commands.START, self.help))
        dispatcher.add_handler(CommandHandler(Commands.HELP, self.help))
        dispatcher.add_handler(CommandHandler(Commands.ABOUT, self.about))
        dispatcher.add_handler(MessageHandler(
            Filters.update.edited_message | Filters.update.edited_channel_post, self.edit_message
        ))
        dispatcher.add_handler(MessageHandler(Filters.reply, self.transmit_reply))
        dispatcher.add_handler(MessageHandler(Filters.all, self.start_topic))
        dispatcher.add_handler(CallbackQueryHandler(self.force_reply, pattern=f"^{CallbackData.REPLY}$"))
        dispatcher.add_handler(CallbackQueryHandler(self.share, pattern=f"^{CallbackData.SHARE}$"))

        dispatcher.add_error_handler(self.handle_error)

    def help(self, update, context):
        swiper_username = self.swiper_update.current_swiper.swiper_username  # non-async single-threaded environment
        update.effective_chat.send_message(
            text=Texts.get_help_msg(swiper_username),
            parse_mode=ParseMode.HTML,
            disable_notification=True,
        )

    def about(self, update, context):
        update.effective_chat.send_message(
            text=Texts.READ_MORE,
            parse_mode=ParseMode.HTML,
            disable_notification=True,
        )

    def start_topic(self, update, context):
        msg = prepare_msg_for_transmission(update.effective_message, context.bot)

        topic_id = create_topic(
            swiper_update=self.swiper_update,  # non-async single-threaded environment
            msg=msg,
            sender_bot_id=context.bot.id,
        )
        subtopic_id = create_subtopic(
            swiper_update=self.swiper_update,  # non-async single-threaded environment
            msg=msg,
            sender_bot_id=context.bot.id,
            topic_id=topic_id,
            autoshare=True,
        )

        transmitted = False
        for swiper_chat_id in find_all_active_swiper_chat_ids(context.bot.id):
            # TODO oleksandr: use thread-workers to broadcast in parallel ? (remember about Telegram limits too)
            if str(swiper_chat_id) != str(update.effective_chat.id):
                transmitted = transmit_message(
                    swiper_update=self.swiper_update,  # non-async single-threaded environment
                    msg=msg,
                    sender_bot_id=context.bot.id,
                    receiver_chat_id=swiper_chat_id,
                    receiver_bot=context.bot,
                    trans_mode=TransmissionModes.BLACK,
                    shareable=False,
                    topic_id=topic_id,
                    subtopic_id=subtopic_id,
                    disable_notification=BLACK_HEARTS_ARE_SILENT,
                ) or transmitted

        if transmitted:
            swiper_username = self.swiper_update.current_swiper.swiper_username  # non-async single-threaded environment
            update.effective_chat.send_message(
                text=Texts.get_new_topic_started_msg(swiper_username),
                parse_mode=ParseMode.HTML,
                # reply_to_message_id=msg.message_id,  # TODO oleksandr: are you 100% sure we don't need it ?
                disable_notification=True,
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
                text=Texts.TALK_NOT_FOUND,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=msg.message_id,
                # disable_notification=True,
            )
            return

        red_heart_default = len(transmissions_by_sender_msg) < 2
        if red_heart_default:
            default_trans_mode = TransmissionModes.RED
        else:
            default_trans_mode = TransmissionModes.BLACK

        edited_at_receiver = True
        for msg_transmission in transmissions_by_sender_msg:
            # broadcast replies to own message

            # TODO oleksandr: use thread-workers to broadcast in parallel ? (remember about Telegram limits too)
            edited_at_receiver = edit_transmission(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                msg=msg,
                receiver_msg_id=msg_transmission[DdbFields.RECEIVER_MSG_ID],
                receiver_chat_id=msg_transmission[DdbFields.RECEIVER_CHAT_ID],
                receiver_bot=context.bot,  # msg_transmission[DdbFields.RECEIVER_BOT_ID] is of no use here
                trans_mode=extract_transmission_mode(
                    msg_transmission=msg_transmission,
                    default_trans_mode=default_trans_mode,
                ),
                shareable=msg_transmission.get(DdbFields.SHAREABLE, False),
            ) and edited_at_receiver

        if not edited_at_receiver:
            update.effective_chat.send_message(
                text=Texts.FAILED_TO_EDIT_AT_RECEIVER,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=msg.message_id,
                # disable_notification=True,
            )

    def force_reply(self, update, context):
        update.callback_query.answer()  # TODO oleksandr: make it failsafe

        msg_transmission = find_original_transmission_by_msg(update.effective_message)
        if not msg_transmission:
            update.effective_chat.send_message(
                text=Texts.TALK_NOT_FOUND,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=update.effective_message.message_id,
                # disable_notification=True,
            )
            update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
            return

        force_reply(
            original_msg=update.effective_message,
            original_msg_transmission=msg_transmission,
        )
        update.effective_message.delete()  # TODO oleksandr: make it failsafe ?

    def share(self, update, context):
        update.callback_query.answer()  # TODO oleksandr: make it failsafe

        transmitted = False  # TODO oleksandr: use it to report about the result

        reply_to_msg = update.effective_message.reply_to_message
        shareable_transmission = find_original_transmission_by_msg(update.effective_message)

        # case #1: it is a reply to current user's message that is being shared
        reply_to_transmissions_by_sender_msg = find_transmissions_by_sender_msg(
            sender_msg_id=reply_to_msg.message_id,
            sender_chat_id=reply_to_msg.chat.id,
            sender_bot_id=reply_to_msg.bot.id,
        )
        for reply_to_transmission in reply_to_transmissions_by_sender_msg:
            if str(reply_to_transmission[DdbFields.RECEIVER_CHAT_ID]) == \
                    str(shareable_transmission[DdbFields.SENDER_CHAT_ID]):
                continue

            # TODO oleksandr: create subtopic

            # TODO oleksandr: use thread-workers to broadcast in parallel ? (remember about Telegram limits too)
            transmitted = transmit_message(
                swiper_update=self.swiper_update,  # non-async single-threaded environment

                # TODO TODO TODO TODO TODO oleksandr: pass the real sender chat and message ids
                msg=update.effective_message,

                sender_bot_id=context.bot.id,
                receiver_chat_id=reply_to_transmission[DdbFields.RECEIVER_CHAT_ID],
                receiver_bot=context.bot,
                trans_mode=TransmissionModes.YELLOW,
                shareable=False,
                topic_id=reply_to_transmission.get(DdbFields.TOPIC_ID),
                subtopic_id=None,  # TODO TODO TODO TODO TODO oleksandr
                disable_notification=BLACK_HEARTS_ARE_SILENT,
                append_username=False,
                reply_to_msg_id=reply_to_transmission[DdbFields.RECEIVER_MSG_ID],

                # TODO TODO TODO TODO TODO oleksandr: is this correct ?
                reply_to_transmission_id=reply_to_transmission[DdbFields.ID],

            ) or transmitted

        # TODO oleksandr
        # # case #2: ... (what kind of case is this ?)
        # reply_to_transmission = find_original_transmission_by_msg(reply_to_msg)

        # TODO TODO TODO
        # TODO oleksandr: implement it properly
        return

        if transmitted:
            swiper_username = self.swiper_update.current_swiper.swiper_username  # non-async single-threaded environment
            update.effective_chat.send_message(
                text=Texts.get_new_topic_started_msg(swiper_username),
                parse_mode=ParseMode.HTML,
                # reply_to_message_id=msg.message_id,  # TODO oleksandr: are you 100% sure we don't need it ?
                disable_notification=True,
            )
        else:
            report_msg_not_transmitted(update)

    def transmit_reply(self, update, context):
        reply_to_msg = update.effective_message.reply_to_message
        try:
            reply_to_msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))
        except BadRequest:
            logger.warning('Failed to hide inline keyboard', exc_info=True)

        msg = prepare_msg_for_transmission(update.effective_message, context.bot)

        msg_transmission = find_original_transmission_by_msg(reply_to_msg)
        if msg_transmission:
            disable_notification = True
            allogrooming_id = None
            topic_id = msg_transmission.get(DdbFields.TOPIC_ID)
            if topic_id:
                allogrooming = find_allogrooming(
                    sender_chat_id=msg.chat_id,
                    sender_bot_id=context.bot.id,
                    receiver_chat_id=msg_transmission[DdbFields.SENDER_CHAT_ID],
                    receiver_bot_id=msg_transmission[DdbFields.SENDER_BOT_ID],
                    topic_id=topic_id,
                )
                if allogrooming:
                    allogrooming_id = allogrooming[DdbFields.ID]
                else:
                    allogrooming_id = create_allogrooming(
                        swiper_update=self.swiper_update,  # non-async single-threaded environment
                        msg=msg,
                        sender_bot_id=context.bot.id,
                        receiver_chat_id=msg_transmission[DdbFields.SENDER_CHAT_ID],
                        receiver_bot_id=msg_transmission[DdbFields.SENDER_BOT_ID],
                        topic_id=topic_id,
                    )
                    disable_notification = False

            transmitted = transmit_message(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                msg=msg,
                sender_bot_id=context.bot.id,
                receiver_chat_id=msg_transmission[DdbFields.SENDER_CHAT_ID],
                receiver_bot=context.bot,  # msg_transmission[DdbFields.SENDER_BOT_ID] is of no use here
                trans_mode=TransmissionModes.RED,
                shareable=bool(msg_transmission.get(DdbFields.SUBTOPIC_ID)),
                topic_id=topic_id,
                disable_notification=disable_notification,
                allogrooming_id=allogrooming_id,
                reply_to_msg_id=msg_transmission[DdbFields.SENDER_MSG_ID],
                reply_to_transmission_id=msg_transmission[DdbFields.ID],
            )
            if not transmitted:
                report_msg_not_transmitted(update)
                # TODO oleksandr: what to do with new allogrooming if message was not transmitted ?
            return

        transmissions_by_sender_msg = find_transmissions_by_sender_msg(
            sender_msg_id=reply_to_msg.message_id,
            sender_chat_id=reply_to_msg.chat.id,
            sender_bot_id=reply_to_msg.bot.id,
        )

        if not transmissions_by_sender_msg:
            update.effective_chat.send_message(
                text=Texts.TALK_NOT_FOUND,
                parse_mode=ParseMode.HTML,
                reply_to_message_id=update.effective_message.reply_to_message.message_id,
                # disable_notification=True,
            )
            return

        subtopic_by_sender_msg = find_subtopic_by_sender_msg(
            sender_msg_id=reply_to_msg.message_id,
            sender_chat_id=reply_to_msg.chat.id,
            sender_bot_id=reply_to_msg.bot.id,
        )
        subtopic_autoshare = bool(subtopic_by_sender_msg and subtopic_by_sender_msg[DdbFields.AUTOSHARE])
        if subtopic_autoshare:
            trans_mode = TransmissionModes.BLACK
            # TODO oleksandr: what about yellow ?
        else:
            trans_mode = TransmissionModes.RED

        if subtopic_autoshare:
            parent_subtopic_id = (subtopic_by_sender_msg or {}).get(DdbFields.ID)
            child_subtopic_id = create_subtopic(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                msg=msg,
                sender_bot_id=context.bot.id,
                topic_id=subtopic_by_sender_msg[DdbFields.TOPIC_ID],
                parent_subtopic_id=parent_subtopic_id,
                autoshare=True,
            )
        else:
            child_subtopic_id = None

        transmitted = False
        for msg_transmission in transmissions_by_sender_msg:
            # broadcast replies to own message

            # TODO oleksandr: use thread-workers to broadcast in parallel (remember about Telegram limits too);
            #  as a side effect it should also ensure that one failure doesn't stop the rest of broadcast
            #  (an exception may happen if, for ex., a receiver has blocked the bot)
            transmitted = transmit_message(
                swiper_update=self.swiper_update,  # non-async single-threaded environment
                msg=msg,
                sender_bot_id=context.bot.id,
                receiver_chat_id=msg_transmission[DdbFields.RECEIVER_CHAT_ID],
                receiver_bot=context.bot,  # msg_transmission[DdbFields.RECEIVER_BOT_ID] is of no use here
                trans_mode=trans_mode,
                shareable=bool(not child_subtopic_id and msg_transmission.get(DdbFields.SUBTOPIC_ID)),
                topic_id=msg_transmission.get(DdbFields.TOPIC_ID),
                subtopic_id=child_subtopic_id,
                disable_notification=True,
                allogrooming_id=msg_transmission.get(DdbFields.ALLOGROOMING_ID),
                reply_to_msg_id=msg_transmission[DdbFields.RECEIVER_MSG_ID],
                reply_to_transmission_id=msg_transmission[DdbFields.ID],
            ) or transmitted  # TODO oleksandr: replace with "and" as in self.edit_message() handler ?

        if not transmitted:
            report_msg_not_transmitted(update)

    def handle_error(self, update, context):
        logger.error('ERROR IN A PTB HANDLER', exc_info=context.error)

        error_str = ''.join(format_exception(type(context.error), context.error, context.error.__traceback__))
        send_partitioned_text(update.effective_chat, error_str)


def report_msg_not_transmitted(update):
    report_msg = update.effective_chat.send_message(
        text=Texts.MESSAGE_NOT_TRANSMITTED,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=update.effective_message.message_id,
        # disable_notification=True,
    )
    return report_msg


def find_original_transmission_by_msg(msg):
    msg_transmission = find_original_transmission(
        receiver_msg_id=msg.message_id,
        receiver_chat_id=msg.chat.id,
        receiver_bot_id=msg.bot.id,
    )
    return msg_transmission
