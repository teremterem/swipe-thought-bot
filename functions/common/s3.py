import logging
import os

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ['REGION']
MAIN_S3_BUCKET_NAME = os.environ['MAIN_S3_BUCKET_NAME']

s3 = boto3.resource('s3', region_name=REGION)
main_bucket = s3.Bucket(name=MAIN_S3_BUCKET_NAME)
