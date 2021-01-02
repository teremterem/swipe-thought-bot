import logging
import time
from functools import wraps
from pprint import pformat

logger = logging.getLogger(__name__)


def safe_int(value):
    if value is None:
        return None
    return int(value)


def timestamp_now_ms():
    return int(time.time() * 1000)


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
    #  @fail_quietly should have the same effect as @fail_quietly()
    def decorator(lambda_handler):
        @wraps(lambda_handler)
        def wrapper(*args, **kwargs):
            response = None
            try:
                response = lambda_handler(*args, **kwargs)
            except:
                logger.exception('')

            if response is None:
                # static_response in two cases: exception happened or lambda worked fine but did not return anything
                response = static_response
            return response

        return wrapper

    return decorator


class SwiperError(Exception):
    ...
