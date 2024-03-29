import os

from functions.common import logging  # force log config of functions/common/__init__.py
from functions.common.utils import log_event_and_response, fail_safely
from functions.swiper_experiments.swiper_transparency import SwiperTransparency

logger = logging.getLogger()

swiper_conversation = SwiperTransparency()


@log_event_and_response
@fail_safely()
def webhook(event, context):
    update_json = event['body']
    swiper_conversation.process_update_json(update_json)


@log_event_and_response
def set_webhook(event, context):
    webhook_token = os.environ['TELEGRAM_TOKEN'].replace(':', '_')
    url = f"https://{event.get('headers').get('Host')}/{event.get('requestContext').get('stage')}/{webhook_token}"

    # # Uncomment the following line at your own risk... Better not to flash our secret url in logs, right?
    # logger.info('SETTING WEBHOOK IN TELEGRAM: %s', url)

    webhook_set = swiper_conversation.dispatcher.bot.set_webhook(url)

    if webhook_set:
        return {
            'statusCode': 200,
            'body': 'Telegram webhook set successfully!',
        }

    return {
        'statusCode': 400,
        'body': 'FAILED to set telegram webhook!',
    }
