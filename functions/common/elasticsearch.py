import logging
import os

import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

logger = logging.getLogger(__name__)

THOUGHTS_ES_IDX = os.environ['THOUGHTS_ES_IDX']

ES_REGION = os.environ['ES_REGION']
ES_HOST = os.environ['ES_HOST']


def create_es_client():
    credentials = boto3.Session().get_credentials()
    aws_auth = AWS4Auth(
        credentials.access_key, credentials.secret_key, ES_REGION, 'es', session_token=credentials.token
    )

    es = Elasticsearch(
        hosts=[{'host': ES_HOST}],
        scheme="https",
        port=443,
        http_auth=aws_auth,
        connection_class=RequestsHttpConnection,
    )
    logger.info('Created ES client for %s', ES_HOST)

    return es
