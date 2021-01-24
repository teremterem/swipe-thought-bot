import logging
import os
from pprint import pformat

import boto3
import simplejson  # handles decimal.Decimal

logger = logging.getLogger(__name__)

REGION = os.environ['REGION']
MAIN_S3_BUCKET_NAME = os.environ['MAIN_S3_BUCKET_NAME']

s3 = boto3.resource('s3', region_name=REGION)
main_bucket = s3.Bucket(name=MAIN_S3_BUCKET_NAME)


def put_s3_object(s3_bucket, key, obj_dict):
    if logger.isEnabledFor(logging.INFO):
        logger.info('S3 PUT_OBJECT ( bucket: %s ; key: %s ):\n%s', s3_bucket.name, key, pformat(obj_dict))
    response = s3_bucket.put_object(
        Key=key,
        Body=simplejson.dumps(obj_dict).encode('utf8'),
    )
    if logger.isEnabledFor(logging.INFO):
        logger.info('S3 PUT_OBJECT RESPONSE:\n%s', pformat(response))
    return response
