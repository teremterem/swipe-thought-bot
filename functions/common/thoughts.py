import logging
from pprint import pformat

from .constants import DataKey, EsKey, AnswererMode, ConvState
from .elasticsearch import create_es_client, THOUGHTS_ES_IDX
from .utils import timestamp_now_ms, SwiperError

logger = logging.getLogger(__name__)


def construct_thought_id(msg_id, chat_id, bot_id):
    thought_id = f"m{msg_id}:c{chat_id}:b{bot_id}"
    logger.info('THOUGHT ID CONSTRUCTED: %s', thought_id)
    return thought_id


class ThoughtContext:
    def __init__(self, ptb_context):
        self.ptb_ctx = ptb_context

    def get_list(self):
        return self.ptb_ctx.chat_data.setdefault(DataKey.THOUGHT_CTX, [])

    def append_thought(self, text, thought_id, msg_id, conv_state):
        self.get_list().append({
            DataKey.TEXT: text,
            DataKey.THOUGHT_ID: thought_id,
            DataKey.MSG_ID: msg_id,
            DataKey.CONV_STATE: conv_state,
            DataKey.TIMESTAMP_MS: timestamp_now_ms(),
        })

    def trim_context(self, max_thought_ctx_len=15):
        self.ptb_ctx.chat_data[DataKey.THOUGHT_CTX] = self.get_list()[-max_thought_ctx_len:]

    def reject_latest_thought(self, validate_msg_id):
        thoughts = self.get_list()
        if not thoughts:
            raise SwiperError('cannot reject latest thought from context - thought context is empty')

        latest_thought = thoughts[-1]
        latest_thought_msg_id = latest_thought[DataKey.MSG_ID]
        if latest_thought_msg_id != validate_msg_id:
            raise SwiperError(
                f"failed to reject latest thought from context - message id validation failed: "
                f"{validate_msg_id} expected to be latest thought msg id but actual latest was {latest_thought_msg_id}"
            )

        logger.info(
            'REJECTING THOUGHT FROM CONTEXT (msg_id=%s):\n%s', latest_thought_msg_id, latest_thought[DataKey.TEXT]
        )
        del thoughts[-1]

    def get_latest_conv_state(self):
        thoughts = self.get_list()
        if not thoughts:
            return None
        return thoughts[-1][DataKey.CONV_STATE]

    def get_latest_thoughts(self, context_size, user_only=False):
        thoughts = self.get_list()[-context_size:]
        if user_only:
            thoughts = [t for t in thoughts if t[DataKey.CONV_STATE] == ConvState.USER_REPLIED]
        return thoughts

    def concat_latest_thoughts(self, context_size, user_only=False):
        return '\n.\n'.join([t[DataKey.TEXT] for t in self.get_latest_thoughts(context_size, user_only=user_only)])

    def get_latest_thought_ids(self, context_size, user_only=False):
        return [t[DataKey.THOUGHT_ID] for t in self.get_latest_thoughts(context_size, user_only=user_only)]


class Answerer:
    def __init__(self):
        self.es = create_es_client()
        self.idx = THOUGHTS_ES_IDX
        # TODO oleksandr: create index if doesn't exist ?

    def index_thought(self, answer_text, answer_thought_id, thought_ctx):
        doc_body = {
            EsKey.ANSWER_THOUGHT_ID: answer_thought_id,
            EsKey.ANSWER: answer_text,

            # TODO oleksandr: should we index user thoughts only (skip bot replies) ?
            #  well, I think indexing both - user thoughts and bot replies - is fine...
            EsKey.CTX1: thought_ctx.concat_latest_thoughts(1),
            EsKey.CTX2: thought_ctx.concat_latest_thoughts(2),
            EsKey.CTX3: thought_ctx.concat_latest_thoughts(3),
            EsKey.CTX5: thought_ctx.concat_latest_thoughts(5),
            EsKey.CTX8: thought_ctx.concat_latest_thoughts(8),
            EsKey.CTX13: thought_ctx.concat_latest_thoughts(13),
        }
        if logger.isEnabledFor(logging.INFO):
            logger.info('INDEX THOUGHT IN ES:\n%s', pformat(doc_body))

        response = self.es.index(
            index=self.idx,
            id=answer_thought_id,
            body=doc_body,
        )

        if logger.isEnabledFor(logging.INFO):
            logger.info('THOUGHT INDEXING ES RESPONSE:\n%s', pformat(response))
        return response

    def answer(self, thought_ctx, answerer_mode):
        logger.info('ANSWERER MODE: %s', answerer_mode)

        if answerer_mode == AnswererMode.SIMPLEST_QUESTION_MATCH:
            # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query.html
            es_query = {
                'query': {
                    'match': {
                        EsKey.CTX1: {
                            # 1024 tokens limit can probably be ignored in case of one message -
                            # telegram limits messages to 4096 chars which isn't likely to contain 1024 separate tokens.
                            'query': thought_ctx.concat_latest_thoughts(1),
                            'fuzziness': 'AUTO',
                        },
                    },
                },
            }
        elif answerer_mode == AnswererMode.CTX8_CTX3_CTX1:
            es_query = {
                'query': {
                    'bool': {
                        # TODO oleksandr: handle hitting 1024 tokens limit gracefully ?
                        'should': [
                            {
                                'match': {
                                    EsKey.CTX1: {
                                        'query': thought_ctx.concat_latest_thoughts(1, user_only=True),
                                        'fuzziness': 'AUTO',
                                        'boost': 8,
                                    },
                                },
                            },
                            {
                                'match': {
                                    EsKey.CTX3: {
                                        'query': thought_ctx.concat_latest_thoughts(3, user_only=True),
                                        'fuzziness': 'AUTO',
                                        'boost': 3,
                                    },
                                },
                            },
                            {
                                'match': {
                                    EsKey.CTX8: {
                                        'query': thought_ctx.concat_latest_thoughts(8, user_only=True),
                                        'fuzziness': 'AUTO',
                                        'boost': 1,
                                    },
                                },
                            },
                        ],
                        'must_not': {
                            # https://stackoverflow.com/a/42646653/2040370
                            'terms': {
                                EsKey.ANSWER_THOUGHT_ID: thought_ctx.get_latest_thought_ids(7, user_only=True),
                            },
                        },
                    },
                },
            }
        else:
            raise SwiperError(f"unsupported answerer mode: {answerer_mode}")

        es_query['size'] = 1
        # es_query['explain'] = True

        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH QUERY:\n%s', pformat(es_query))

        response = self.es.search(
            index=self.idx,
            body=es_query,
            # request_timeout=15,  # or  # timeout=15,  # seconds
        )
        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH RESPONSE:\n%s', pformat(response, width=140))

        hits = response['hits']['hits']
        if hits:
            return hits[0]['_source']

        logger.info('ZERO ELASTICSEARCH HITS')
        return None
