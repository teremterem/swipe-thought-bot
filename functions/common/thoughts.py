import logging
from pprint import pformat

from functions.common.elasticsearch import create_es_client, THOUGHTS_ES_IDX

logger = logging.getLogger(__name__)


class Thoughts:
    def __init__(self):
        self.es = create_es_client()
        self.idx = THOUGHTS_ES_IDX
        # TODO oleksandr: create index if doesn't exist ?

    def index_thought(self, text, msg_id, chat_id, bot_id):
        thought_id = self.construct_thought_id(msg_id=msg_id, chat_id=chat_id, bot_id=bot_id)
        response = self.es.index(
            index=self.idx,
            id=thought_id,
            body={
                'answer_thought_id': thought_id,
                'answer': text,
            }
        )

        if logger.isEnabledFor(logging.INFO):
            logger.info('INDEX THOUGHT ES RESPONSE:\n%s', pformat(response))
        return response

    def answer_thought(self, text):
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query.html
        es_query = {
            # 'explain': ES_EXPLAIN_MATCHING,
            'size': 1,
            'query': {
                'match': {
                    'answer': {
                        # 1024 tokens limit can probably be ignored in case of one message -
                        # telegram limits messages to 4096 chars which isn't likely to contain 1024 separate tokens.
                        'query': text,
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
            return hits[0]['_source']['answer']

        logger.info('ZERO ELASTICSEARCH HITS')
        return None

    @staticmethod
    def construct_thought_id(msg_id, chat_id, bot_id):
        thought_id = f"m{msg_id}:c{chat_id}:b{bot_id}"
        logger.info('THOUGHT ID CONSTRUCTED: %s', thought_id)
        return thought_id
