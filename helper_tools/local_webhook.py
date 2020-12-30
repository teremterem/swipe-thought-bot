import json
import os
import sys

from flask import Flask, request

sys.path.insert(0, os.getcwd())

from helper_tools.helper_utils import set_env_vars

set_env_vars(for_local=True, project_dir='./')

from functions.common.swiper_telegram import bot
from functions.telegram_webhook import webhook
from functions.common import logging, LOG_LEVEL

logging.basicConfig(level=LOG_LEVEL)

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

    webhook_set = bot.set_webhook(url)
    if webhook_set:
        return url
    return 'FAILED TO SET WEBHOOK'


@app.route(WEBHOOK_PATH, methods=['POST'])
def local_webhook():
    event = {
        'httpMethod': 'POST',
        'body': json.dumps(request.json),
    }
    response = webhook(event, None)

    # response = Response(json.dumps('ok'), status=200)
    # response.headers['Content-Type'] = 'application/json'
    # return response
    return ''  # 200 with no body