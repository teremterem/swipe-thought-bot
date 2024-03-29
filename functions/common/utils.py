import logging
import time
import uuid
from functools import wraps
from pprint import pformat

logger = logging.getLogger(__name__)


def generate_uuid():
    return str(uuid.uuid4())


def safe_int(value):
    if value is None:
        return None
    return int(value)


def timestamp_now_ms():
    return int(time.time() * 1000)


def utf16_cp_len(text):
    """
    https://stackoverflow.com/a/39280419/2040370
    https://github.com/python-telegram-bot/python-telegram-bot/issues/400
    """
    return len(text.encode('utf-16-le')) // 2


def split_text(text, limit):
    for i in range(0, len(text), limit):
        yield text[i:i + limit]


def send_partitioned_text(chat, text, limit=4000):
    for text_part in split_text(text, limit):
        chat.send_message(text_part)


def log_event_and_response(lambda_handler):
    @wraps(lambda_handler)
    def wrapper(event, *args, **kwargs):
        if logger.isEnabledFor(logging.INFO):
            logger.info('LAMBDA EVENT:\n%s', pformat(event))

        response = lambda_handler(event, *args, **kwargs)

        if logger.isEnabledFor(logging.INFO):
            logger.info('LAMBDA RESPONSE:\n%s', pformat(response))

        return response

    return wrapper


def fail_safely(static_response=None):
    # TODO oleksandr: make decoration possible with and without parameters ?
    #  @fail_safely should have the same effect as @fail_safely()
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            response = None
            try:
                response = func(*args, **kwargs)
            except:
                logger.exception('')

            if response is None:
                # static_response in two cases: exception happened or func worked fine but returned None
                response = static_response
            return response

        return wrapper

    return decorator


class SwiperError(Exception):
    ...
