import logging
from pprint import pformat

from .constants import DataKey, EsKey, AnswererMode
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

    def append_thought(self, text, thought_id, conv_state):
        self.get_list().append({
            DataKey.TEXT: text,
            DataKey.THOUGHT_ID: thought_id,
            DataKey.CONV_STATE: conv_state,
            DataKey.TIMESTAMP_MS: timestamp_now_ms(),
        })

    def trim_context(self, max_thought_ctx_len=10):
        self.ptb_ctx.chat_data[DataKey.THOUGHT_CTX] = self.get_list()[-max_thought_ctx_len:]

    def _latest_thoughts(self, num_of_thoughts):
        return self.get_list()[-num_of_thoughts:]

    def latest_thoughts_for_idx(self, num_of_thoughts):
        return '\n.\n'.join([t[DataKey.TEXT] for t in self._latest_thoughts(num_of_thoughts)])

    def latest_thought_ids(self, num_of_thoughts):
        return [t[DataKey.THOUGHT_ID] for t in self._latest_thoughts(num_of_thoughts)]


class Answerer:
    def __init__(self):
        self.es = create_es_client()
        self.idx = THOUGHTS_ES_IDX
        # TODO oleksandr: create index if doesn't exist ?

    def index_thought(self, answer, answer_thought_id, thought_ctx):
        doc_body = {
            EsKey.ANSWER: answer,
            EsKey.ANSWER_THOUGHT_ID: answer_thought_id,
            EsKey.CTX1: thought_ctx.latest_thoughts_for_idx(1),
            EsKey.CTX3: thought_ctx.latest_thoughts_for_idx(3),
            EsKey.CTX8: thought_ctx.latest_thoughts_for_idx(8),
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
        if answerer_mode != AnswererMode.SIMPLEST_QUESTION_MATCH:
            raise SwiperError(f"unsupported answerer mode: {answerer_mode}")

        # TODO oleksandr: are you sure this shouldn't be maintained outside of Answerer
        thought_ctx.ptb_ctx.chat_data[DataKey.ANSWERER_MODE] = answerer_mode
        logger.info('ANSWERER MODE: %s', answerer_mode)

        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query.html
        es_query = {
            # 'explain': ES_EXPLAIN_MATCHING,
            'size': 1,
            'query': {
                'match': {
                    EsKey.CTX1: {
                        # 1024 tokens limit can probably be ignored in case of one message -
                        # telegram limits messages to 4096 chars which isn't likely to contain 1024 separate tokens.
                        'query': thought_ctx.latest_thoughts_for_idx(1),
                        'fuzziness': 'AUTO',
                    },
                },
            },
        }
        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH QUERY:\n%s', pformat(es_query))

        response = self.es.search(
            index=self.idx,
            body=es_query,
            # request_timeout=25,  # seconds
        )
        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH RESPONSE:\n%s', pformat(response, width=140))

        hits = response['hits']['hits']
        if hits:
            return hits[0]['_source']

        logger.info('ZERO ELASTICSEARCH HITS')
        return None
