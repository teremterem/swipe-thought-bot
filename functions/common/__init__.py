"""
Possible log levels:

CRITICAL
ERROR
WARNING
INFO
DEBUG
NOTSET
"""
import logging
import os

LOG_LEVEL = os.environ['LOG_LEVEL']

root_logger = logging.getLogger()
# if root_logger.handlers:
#     for handler in root_logger.handlers:
#         root_logger.removeHandler(handler)
# logging.basicConfig(level=LOG_LEVEL)
root_logger.setLevel(LOG_LEVEL)
