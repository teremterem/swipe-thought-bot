import logging
from pprint import pformat

from functions.common.constants import EsKey
from functions.common.elasticsearch import create_es_client, THOUGHTS_ES_IDX, ES_NUM_OF_RESULTS, ES_EXPLAIN, \
    ES_SHOW_ANALYSIS

logger = logging.getLogger(__name__)


class SwiperMatch:
    def __init__(self):
        self.es = create_es_client()
        self.idx = THOUGHTS_ES_IDX
        # TODO oleksandr: create index if doesn't exist ?

    def index_thought(self, thought_id, body):
        if logger.isEnabledFor(logging.INFO):
            logger.info('INDEX THOUGHT IN ES (%s):\n%s', thought_id, pformat(body))

        response = self.es.index(
            index=self.idx,
            id=thought_id,
            body=body,
        )

        if logger.isEnabledFor(logging.INFO):
            logger.info('THOUGHT INDEXING ES RESPONSE:\n%s', pformat(response))
        return response

    def _show_analysis(self, text_to_analyze):
        if ES_SHOW_ANALYSIS and logger.isEnabledFor(logging.INFO):
            es_analysis = self.es.indices.analyze(
                body={
                    'text': text_to_analyze,
                },
                index=self.idx,
            )
            logger.info(
                'ES ANALYSIS:\n%s\n\nANALYZED TEXT:\n%s\n\nORIGINAL TEXT:\n%s',
                pformat(es_analysis),
                ' '.join([t['token'] for t in es_analysis.get('tokens', [])]),
                text_to_analyze,
            )

    def find_similar_thought(self, thought):
        self._show_analysis(thought)
        es_query = {
            'query': {
                'bool': {
                    # TODO oleksandr: handle hitting 1024 tokens limit gracefully ?
                    'should': [
                        {
                            'match': {
                                EsKey.THOUGHT: {
                                    'query': thought,
                                    'fuzziness': 'AUTO',
                                },
                            },
                        },
                    ],
                    # 'must_not': {
                    #     # https://stackoverflow.com/a/42646653/2040370
                    #     'terms': {
                    #         EsKey.ANSWER_THOUGHT_ID: thought_ctx.get_latest_thought_ids(7, user_only=True),
                    #     },
                    # },
                    # # TODO oleksandr: also maintain a "queue" (last 15, for ex.) of shown thoughts to exclude them ?
                    # #  no! not until we start matching people!
                    # #  (by then we will see if anything like this is still needed)
                },
            },
            'size': ES_NUM_OF_RESULTS,
        }

        if ES_EXPLAIN:
            es_query['explain'] = True

        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH QUERY:\n%s', pformat(es_query))

        response = self.es.search(
            index=self.idx,
            body=es_query,
            # request_timeout=15,  # seconds
        )
        if logger.isEnabledFor(logging.INFO):
            logger.info('ES SEARCH RESPONSE:\n%s', pformat(response, width=160))

        hits = response['hits']['hits']
        if hits:
            return hits[0]['_source']

        logger.info('ZERO ELASTICSEARCH HITS')
        return None
