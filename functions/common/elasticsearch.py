import logging
import os
from distutils.util import strtobool

import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)

THOUGHTS_ES_IDX = os.environ['THOUGHTS_ES_IDX']

ES_REGION = os.environ['ES_REGION']
ES_HOST = os.environ['ES_HOST']

ES_SHOW_ANALYSIS = os.environ['ES_SHOW_ANALYSIS'].strip()  # either name of analyzer (like 'english') or empty string
ES_EXPLAIN = bool(strtobool(os.environ['ES_EXPLAIN']))
ES_NUM_OF_RESULTS = int(os.environ['ES_NUM_OF_RESULTS'])


def create_es_client():
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key, credentials.secret_key, ES_REGION, 'es', session_token=credentials.token
    )

    es = Elasticsearch(  # this cannot go to global scope because credentials will eventually expire
        hosts=[{'host': ES_HOST}],
        scheme="https",
        port=443,
        http_auth=aws_auth,
        connection_class=RequestsHttpConnection,
    )
    logger.info('Created ES client for %s', ES_HOST)

    return es
