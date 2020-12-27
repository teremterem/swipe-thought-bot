import logging
import os

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ['REGION']

dynamodb = boto3.resource('dynamodb', region_name=REGION)
