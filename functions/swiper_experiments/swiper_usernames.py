import secrets

from telegram import MessageEntity

from functions.common.dynamodb import DdbFields
from functions.common.utils import utf16_cp_len
from functions.swiper_experiments.japanese_names import JAPANESE_UNISEX_GIVEN_NAMES


def generate_swiper_username():
    japanese_given_name = secrets.choice(JAPANESE_UNISEX_GIVEN_NAMES)
    random_number = secrets.randbelow(7900) + 2100
    username = f"{japanese_given_name}{random_number}"

    username_obj = {
        DdbFields.USERNAME: username,
        DdbFields.BASE_NAME: japanese_given_name,
    }
    return username_obj


def append_swiper_username(text, entities, username):
    text = text or ''
    entities = entities or []

    delimiter = '\n\n👤 '
    resulting_text = ''.join([text, delimiter, username])

    entities = entities + [MessageEntity(
        length=utf16_cp_len(username),
        offset=utf16_cp_len(text) + utf16_cp_len(delimiter),
        type='italic',
    )]

    return resulting_text, entities
