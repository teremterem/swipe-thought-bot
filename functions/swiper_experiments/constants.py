import os
from distutils.util import strtobool

# TODO oleksandr: rename to NEW_TOPICS_ARE_SILENT ?
BLACK_HEARTS_ARE_SILENT = bool(strtobool(os.environ['BLACK_HEARTS_ARE_SILENT']))


class CallbackData:
    REPLY = 'reply'


class Commands:
    START = 'start'
    HELP = 'help'
    ABOUT = 'about'


class Texts:
    READ_MORE = "<i>https://toporok.medium.com/що-таке-swipy-de15d59b1f0b</i>"

    READ_HEART = "❤️"
    BLACK_HEART = "🖤"
    REPLY = "Відповісти"
    # STOP = "❌Зупинити"
    # REVOKE_TOPIC = "⛔️Відкликати"

    TALK_NOT_FOUND = f"<i>💔 Розмову не знайдено\n/{Commands.HELP}</i>"
    MESSAGE_NOT_TRANSMITTED = f"<i>Повідомлення не відправлено 😞\n/{Commands.HELP}</i>"
    FAILED_TO_EDIT_AT_RECEIVER = f"<i>Не вдалося відредагувати у отримувача 😞\n/{Commands.HELP}</i>"

    @staticmethod
    def get_new_topic_started_msg(username):
        _new_topic_started = (
            f"<i>Ви ({username}) створили нову тему для розмов - очікуйте відповідей ⏳\n"
            f"/{Commands.HELP}</i>"
        )
        return _new_topic_started.strip()

    @staticmethod
    def get_help_msg(username):
        _help = (
            "👋 Вітаю! Мене звати Свайпі🙃\n"
            "\n"
            "Відправ мені повідомлення, щоб створити тему для анонімного обговорення з іншими учасниками спільноти.\n"
            "\n"
            "Повідомлення може бути текстовим, голосовим, світлиною, наліпкою, анімацією, опитуванням, відео тощо.\n"
            "\n"
            "Також можеш просто залишатись на зв`язку та відповідати на повідомлення-теми, що зацікавлять.\n"
            "\n"
            "Щоб відповісти на повідомлення, проведи по ньому пальцем вліво⬅️ або ж скористайся опцією "
            "\"Відповісти\".\n"
            "\n"
            "--\n"
            "Чорне сердечко🖤 - повідомлення отримали усі учасники спільноти (створено нову тему).\n"
            "\n"
            "Червоне сердечко❤️ - тобі відповіли і цю відповідь бачиш лише ти.\n"
            "\n"
            f"Твій псевдонім: 👤 <i>{username}</i>\n"
            "\n"
            f"Більше інформації: /{Commands.ABOUT}\n"
            f"Показати цей текст ще раз: /{Commands.HELP}\n"
        )
        return _help.strip()
