import os
import sys
from threading import Thread

from flask import Flask, request

sys.path.insert(0, os.getcwd())

from helper_tools.helper_utils import set_env_vars

set_env_vars(project_dir='./', local_overlay=True)

from functions.telegram_webhook import webhook, swiper
from functions.common import logging, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.ERROR)

app = Flask(__name__)

WEBHOOK_PATH = '/webhook'


@app.route('/')
def set_local_webhook():
    url = request.url

    if url.endswith('/'):
        url = url[:-1]
    if url.lower().startswith('http://'):
        url = 'https' + url[4:]

    url += WEBHOOK_PATH
    print(url)

    webhook_set = swiper.bot.set_webhook(url)
    if webhook_set:
        return url
    return 'FAILED TO SET WEBHOOK'


@app.route(WEBHOOK_PATH, methods=['POST'])
def local_webhook():
    event = {'body': request.json}
    thread = Thread(target=webhook, args=(event, None))
    thread.start()

    # response = Response(json.dumps('ok'), status=200)
    # response.headers['Content-Type'] = 'application/json'
    # return response
    return ''  # 200 with no body
