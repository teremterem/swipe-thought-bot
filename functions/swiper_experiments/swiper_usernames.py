import secrets

from telegram import MessageEntity

from functions.swiper_experiments.japanese_names import JAPANESE_UNISEX_GIVEN_NAMES


def generate_swiper_username():
    japanese_given_name = secrets.choice(JAPANESE_UNISEX_GIVEN_NAMES)
    random_number = secrets.randbelow(9000) + 1000
    username = f"{japanese_given_name}{random_number}"
    return username


def utf16_cp_len(text):
    """
    https://stackoverflow.com/a/39280419/2040370
    https://github.com/python-telegram-bot/python-telegram-bot/issues/400
    """
    return len(text.encode('utf-16-le')) // 2


def append_username(text, entities):
    text = text or ''
    entities = entities or []

    username = generate_swiper_username()
    delimiter = '\n\n👤 '
    resulting_text = ''.join([text, delimiter, username])

    entities = entities + [MessageEntity(
        length=utf16_cp_len(username),
        offset=utf16_cp_len(text) + utf16_cp_len(delimiter),
        type='italic',
    )]

    return resulting_text, entities
