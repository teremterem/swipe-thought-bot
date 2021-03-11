"""
INFO:functions.common.utils:LAMBDA EVENT:
{'body': {'message': {'caption': 'Идти уже домой или нет?\n\nEto-Utzuki-3786',
                      'caption_entities': [{'length': 15,
                                            'offset': 25,
                                            'type': 'italic'}],
                      'chat': {'first_name': 'teremterem',
                               'id': 210723289,
                               'type': 'private',
                               'username': 'teremterem'},
                      'date': 1615407165,
                      'from': {'first_name': 'teremterem',
                               'id': 210723289,
                               'is_bot': False,
                               'language_code': 'uk',
                               'username': 'teremterem'},
                      'message_id': 3099,
                      'photo': [{'file_id': 'AgACAgIAAxkBAAIMG2BJKD3OT1I9...o3gE6Q6bQ2GGaJni4AAwEAAwIAA20AA9OPAwABHgQ',
                                 'file_size': 6115,
                                 'file_unique_id': 'AQADGGaJni4AA9OPAwAB',
                                 'height': 320,
                                 'width': 256},
                                {'file_id': 'AgACAgIAAxkBAAIMG2BJKD3OT1I9...o3gE6Q6bQ2GGaJni4AAwEAAwIAA3gAA9SPAwABHgQ',
                                 'file_size': 27340,
                                 'file_unique_id': 'AQADGGaJni4AA9SPAwAB',
                                 'height': 800,
                                 'width': 640},
                                {'file_id': 'AgACAgIAAxkBAAIMG2BJKD3OT1I9...o3gE6Q6bQ2GGaJni4AAwEAAwIAA3kAA9GPAwABHgQ',
                                 'file_size': 41475,
                                 'file_unique_id': 'AQADGGaJni4AA9GPAwAB',
                                 'height': 1280,
                                 'width': 1024}]},
          'update_id': 284002334}}
"""
import random

from telegram import MessageEntity


def kind_of_random_username():
    kind_of_random_set = [
        'Komatsu-Chiyuki-5580',
        'Otonari-Ichi-9984',
        'Eto-Utzuki-3786',
        'Haruyama-Torio-6952',
        'Kashiwagi-Sosa-3923',
    ]
    return random.choice(kind_of_random_set)


def append_username(text, entities):
    text = text or ''
    entities = entities or []

    username = kind_of_random_username()
    # TODO oleksandr: use rstrip on text ? would existing entities need to be adjusted to that ?
    resulting_text = f"{text}\n\n{username}"

    entities += [MessageEntity(
        length=len(username),
        offset=len(text) + 2,
        type='italic',
    )]

    return resulting_text, entities
