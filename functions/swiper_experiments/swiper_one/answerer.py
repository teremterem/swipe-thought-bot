import json
import logging
from pprint import pformat

from functions.common.constants import EsKey, AnswererMode
from functions.common.elasticsearch import create_es_client, THOUGHTS_ES_IDX, ES_EXPLAIN
from functions.common.s3 import main_bucket
from functions.common.utils import SwiperError

logger = logging.getLogger(__name__)


class Answerer:
    def __init__(self):
        self.es = create_es_client()
        self.idx = THOUGHTS_ES_IDX
        # TODO oleksandr: create index if doesn't exist ?

    def index_thought(self, answer_text, answer_thought_id, thought_ctx):
        doc_body = {
            EsKey.ANSWER_THOUGHT_ID: answer_thought_id,
            EsKey.ANSWER: answer_text,

            # TODO oleksandr: should we index bot replies only (skip user thoughts) ?
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

        # TODO oleksandr: do we need this ? it can be extracted from updates; also, it can be fetched from ES itself
        main_bucket.put_object(
            Key=f"answerer-idx-backup/{answer_thought_id}.index.json",
            Body=json.dumps(doc_body).encode('utf8'),
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
        elif answerer_mode == AnswererMode.CTX8_CTX1B13:
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
                                        'boost': 13,
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
                        # TODO oleksandr: also maintain a "queue" (last 15, for ex.) of shown thoughts to exclude them ?
                        #  no! not until we start matching people!
                        #  (by then we will see if anything like this is still needed)
                    },
                },
            }
        else:
            raise SwiperError(f"unsupported answerer mode: {answerer_mode}")

        if ES_EXPLAIN:
            es_query['size'] = 2
            es_query['explain'] = True
        else:
            es_query['size'] = 1

        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH QUERY:\n%s', pformat(es_query))

        response = self.es.search(
            index=self.idx,
            body=es_query,
            # request_timeout=15,  # or  # timeout=15,  # seconds
        )
        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH RESPONSE:\n%s', pformat(response, width=160))

        hits = response['hits']['hits']
        if hits:
            return hits[0]['_source']

        logger.info('ZERO ELASTICSEARCH HITS')
        return None
