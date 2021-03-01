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
    HELP = (
        "👋 Вітаю! Мене звати Свайпі🙃\n"
        "\n"
        "Відправте мені повідомлення, щоб створити тему для анонімного обговорення з іншими учасниками спільноти.\n"
        "\n"
        "Повідомлення може бути текстовим, голосовим, світлиною, наліпкою, анімацією, опитуванням, відео тощо.\n"
        "\n"
        "Також можете просто залишатись на зв`язку та відповідати на повідомлення-теми, які вас зацікавлять.\n"
        "\n"
        "Щоб відповісти на повідомлення, проведіть по ньому пальцем вліво⬅️ або ж скористайтесь опцією "
        "\"Відповісти\".\n"
        "\n"
        "--\n"
        "Чорне сердечко🖤 - повідомлення отримали не лише ви, а й інші учасники спільноти (створено нову тему).\n"
        "\n"
        "Червоне сердечко❤️ - вам відповіли і цю відповідь бачите лише ви.\n"
        "\n"
        "<i>Повідомлення-відповіді надходять лише одній людині.</i>\n"
        "\n"
        f"Отримати про це більше інформації: /{Commands.ABOUT}\n"
        f"Показати цей текст ще раз: /{Commands.HELP}"
    )
    READ_MORE = "<i>https://toporok.medium.com/що-таке-swipy-de15d59b1f0b</i>"

    READ_HEART = "❤️"
    BLACK_HEART = "🖤"
    REPLY = "Відповісти"
    # STOP = "❌Зупинити"

    NEW_TOPIC_STARTED = f"<i>Ви створили нову тему для розмов - очікуйте відповідей ⏳\n/{Commands.HELP}</i>"
    # REVOKE_TOPIC = "⛔️Відкликати"

    TALK_NOT_FOUND = f"<i>💔 Розмову не знайдено\n/{Commands.HELP}</i>"
    MESSAGE_NOT_TRANSMITTED = f"<i>Повідомлення не відправлено 😞\n/{Commands.HELP}</i>"
    FAILED_TO_EDIT_AT_RECEIVER = f"<i>Не вдалося відредагувати у отримувача 😞\n/{Commands.HELP}</i>"
