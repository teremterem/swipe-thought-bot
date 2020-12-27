import logging
import os

from .dynamodb import dynamodb

logger = logging.getLogger(__name__)

TELEGRAM_CONV_STATE_DDB_TABLE_NAME = os.environ['TELEGRAM_CONV_STATE_DDB_TABLE_NAME']

telegram_conv_state_table = dynamodb.Table(TELEGRAM_CONV_STATE_DDB_TABLE_NAME)
