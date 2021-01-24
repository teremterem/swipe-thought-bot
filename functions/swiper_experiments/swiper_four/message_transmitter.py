from pprint import pformat

from functions.common import logging  # force log config of functions/common/__init__.py

logger = logging.getLogger(__name__)


def transmit_message(sender_chat_id, sender_bot_id, receiver_chat_id, receiver_bot_id, text):
    msg = context.bot.send_message(
        chat_id=swiper_chat_id,
        text=text,
    )
    log_bot_msg(msg)


def log_bot_msg(msg):
    if logger.isEnabledFor(logging.INFO):
        if msg:
            msg = msg.to_dict()
        logger.info('MESSAGE FROM BOT:\n%s', pformat(msg))
