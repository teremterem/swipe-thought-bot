import logging
import os

import boto3

logger = logging.getLogger(__name__)

REGION = os.environ['REGION']

SWIPER_CHAT_DATA_DDB_TABLE_NAME = os.environ['SWIPER_CHAT_DATA_DDB_TABLE_NAME']
MESSAGE_TRANSMISSION_DDB_TABLE_NAME = os.environ['MESSAGE_TRANSMISSION_DDB_TABLE_NAME']
TOPIC_DDB_TABLE_NAME = os.environ['TOPIC_DDB_TABLE_NAME']
SUBTOPIC_DDB_TABLE_NAME = os.environ['SUBTOPIC_DDB_TABLE_NAME']
ALLOGROOMING_DDB_TABLE_NAME = os.environ['ALLOGROOMING_DDB_TABLE_NAME']

dynamodb = boto3.resource('dynamodb', region_name=REGION)

swiper_chat_data_table = dynamodb.Table(SWIPER_CHAT_DATA_DDB_TABLE_NAME)
msg_transmission_table = dynamodb.Table(MESSAGE_TRANSMISSION_DDB_TABLE_NAME)
topic_table = dynamodb.Table(TOPIC_DDB_TABLE_NAME)
subtopic_table = dynamodb.Table(SUBTOPIC_DDB_TABLE_NAME)
allogrooming_table = dynamodb.Table(ALLOGROOMING_DDB_TABLE_NAME)


class DdbFields:
    ID = 'id'

    CHAT_ID = 'chat_id'
    BOT_ID = 'bot_id'

    CHAT = 'chat'
    IS_SWIPER_AUTHORIZED = 'is_swiper_authorized'
    SWIPER_USERNAME = 'swiper_username'
    USERNAME = 'username'
    BASE_NAME = 'base_name'

    TOPIC_ID = 'topic_id'
    SUBTOPIC_ID = 'subtopic_id'
    ALLOGROOMING_ID = 'allogrooming_id'
    ORIGINAL_MSG_TRANS_ID = 'original_msg_trans_id'

    SENDER_MSG_ID = 'sender_msg_id'
    SENDER_CHAT_ID = 'sender_chat_id'
    SENDER_BOT_ID = 'sender_bot_id'

    RECEIVER_MSG_ID = 'receiver_msg_id'
    RECEIVER_CHAT_ID = 'receiver_chat_id'
    RECEIVER_BOT_ID = 'receiver_bot_id'

    REPLY_TO_MSG_ID = 'reply_to_msg_id'
    REPLY_TO_TRANSMISSION_ID = 'reply_to_transmission_id'

    RED_HEART = 'red_heart'

    SENDER_UPDATE_S3_KEY = 'sender_update_s3_key'
    RECEIVER_MSG_S3_KEY = 'receiver_msg_s3_key'
