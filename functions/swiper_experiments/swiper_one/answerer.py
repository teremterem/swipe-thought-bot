import json
import logging
from pprint import pformat

from functions.common.constants import EsKey, AnswererMode
from functions.common.elasticsearch import create_es_client, THOUGHTS_ES_IDX, ES_NUM_OF_RESULTS, ES_EXPLAIN, \
    ES_SHOW_ANALYSIS
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

    def _show_analysis(self, text_to_analyze):
        if ES_SHOW_ANALYSIS and logger.isEnabledFor(logging.INFO):
            es_analysis = self.es.indices.analyze(body={
                'analyzer': ES_SHOW_ANALYSIS,
                'text': text_to_analyze,
            })
            logger.info(
                'ES ANALYSIS (%s):\n%s\n\nANALYZED TEXT:\n%s\n\nORIGINAL TEXT:\n%s',
                ES_SHOW_ANALYSIS,
                pformat(es_analysis),
                ' '.join([t['token'] for t in es_analysis.get('tokens', [])]),
                text_to_analyze,
            )

    def answer(self, thought_ctx, answerer_mode):
        logger.info('ANSWERER MODE: %s', answerer_mode)

        if answerer_mode == AnswererMode.SIMPLEST_QUESTION_MATCH:

            text_to_analyze = thought_ctx.concat_latest_thoughts(1)

            # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query.html
            es_query = {
                'query': {
                    'match': {
                        EsKey.CTX1: {
                            # 1024 tokens limit can probably be ignored in case of one message -
                            # telegram limits messages to 4096 chars which isn't likely to contain 1024 separate tokens.
                            'query': text_to_analyze,
                            'fuzziness': 'AUTO',
                        },
                    },
                },
            }
            self._show_analysis(text_to_analyze)

        elif answerer_mode == AnswererMode.CTX8_CTX1B13:

            text_to_analyze = thought_ctx.concat_latest_thoughts(8, user_only=True)

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
                                        'query': text_to_analyze,
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
            self._show_analysis(text_to_analyze)

        else:
            raise SwiperError(f"unsupported answerer mode: {answerer_mode}")

        es_query['size'] = ES_NUM_OF_RESULTS
        if ES_EXPLAIN:
            es_query['explain'] = True

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
