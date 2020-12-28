import logging

logger = logging.getLogger(__name__)


def construct_thought_id(msg_id, chat_id, bot_id):
    thought_id = f"m{msg_id}:c{chat_id}:b{bot_id}"
    logger.info('THOUGHT ID CONSTRUCTED: %s', thought_id)
    return thought_id


_last_thought_id = None  # TODO oleksandr: get rid of this


def index_thought(msg_id, chat_id, bot_id, text):
    global _last_thought_id
    _last_thought_id = construct_thought_id(msg_id=msg_id, chat_id=chat_id, bot_id=bot_id)


def answer_thought(text):
    return f"yadayadayada\n{_last_thought_id}"
