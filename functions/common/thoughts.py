import logging

logger = logging.getLogger(__name__)


def construct_thought_id(msg_id, chat_id, bot_id):
    thought_id = f"m{msg_id}:c{chat_id}:b{bot_id}"
    logger.info('THOUGHT ID CONSTRUCTED: %s', thought_id)
    return thought_id


def index_thought(msg_id, chat_id, bot_id, text):
    pass


def answer_thought(text):
    return text
