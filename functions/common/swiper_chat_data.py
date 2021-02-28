import logging
import os
from distutils.util import strtobool
from pprint import pformat

from boto3.dynamodb.conditions import Attr

from functions.common.dynamodb import swiper_chat_data_table, DdbFields

logger = logging.getLogger(__name__)

AUTHORIZE_STRANGERS_BY_DEFAULT = bool(strtobool(os.environ['AUTHORIZE_STRANGERS_BY_DEFAULT']))


def read_swiper_chat_data(chat_id, bot_id):
    empty_item = {
        DdbFields.CHAT_ID: int(chat_id),
        DdbFields.BOT_ID: int(bot_id),
    }
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - GET_ITEM (DDB) KEY:\n%s', pformat(empty_item))
    response = swiper_chat_data_table.get_item(Key=empty_item)
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - GET_ITEM (DDB):\n%s', pformat(response))

    item = response.get('Item')
    if not item:
        # does not exist yet
        empty_item[DdbFields.IS_SWIPER_AUTHORIZED] = AUTHORIZE_STRANGERS_BY_DEFAULT
        return empty_item

    return item


def write_swiper_chat_data(swiper_chat_data):
    # https://stackoverflow.com/questions/43667229/difference-between-dynamodb-putitem-vs-updateitem
    # TODO oleksandr: implement optimistic locking using conditional DDB writing (and exception if condition not met)
    response = swiper_chat_data_table.put_item(Item=swiper_chat_data)
    if logger.isEnabledFor(logging.INFO):
        logger.info('SWIPER CHAT DATA - PUT_ITEM (DDB):\n%s', pformat(response))

    return response


def find_all_active_swiper_chat_ids(bot_id):
    bot_id = int(bot_id)

    # TODo oleksandr: do we need to paginate over the results ?
    scan_result = swiper_chat_data_table.scan(
        # TODO oleksandr: do we need to create a correspondent global secondary index ?
        FilterExpression=(
                Attr(DdbFields.BOT_ID).eq(bot_id) &
                Attr(DdbFields.IS_SWIPER_AUTHORIZED).eq(True)
        ),
        ProjectionExpression=DdbFields.CHAT_ID,
    )
    if logger.isEnabledFor(logging.INFO):
        logger.info('FIND ACTIVE SWIPER CHAT IDS (DDB SCAN RESPONSE):\n%s', scan_result)

    swiper_chat_ids = {item[DdbFields.CHAT_ID] for item in scan_result['Items']}
    return swiper_chat_ids
