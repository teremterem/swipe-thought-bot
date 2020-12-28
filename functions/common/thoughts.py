import logging
from pprint import pformat

from functions.common.elasticsearch import create_es_client, THOUGHTS_ES_IDX

logger = logging.getLogger(__name__)


def construct_thought_id(msg_id, chat_id, bot_id):
    thought_id = f"m{msg_id}:c{chat_id}:b{bot_id}"
    logger.info('THOUGHT ID CONSTRUCTED: %s', thought_id)
    return thought_id


def index_thought(text, msg_id, chat_id, bot_id):
    es = create_es_client()
    # TODO oleksandr: create index if doesn't exist ?

    thought_id = construct_thought_id(msg_id=msg_id, chat_id=chat_id, bot_id=bot_id)
    response = es.index(
        index=THOUGHTS_ES_IDX,
        id=thought_id,
        body={
            'answer_thought_id': thought_id,
            'answer': text,
        }
    )

    if logger.isEnabledFor(logging.INFO):
        logger.info('INDEX THOUGHT ES RESPONSE:\n%s', pformat(response))
    return response


def answer_thought(text):
    return text
