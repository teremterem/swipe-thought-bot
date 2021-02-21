class CallbackData:
    REPLY = 'reply'


class Commands:
    START = 'start'
    HELP = 'help'
    ABOUT = 'about'


class Text:
    HELP = (
        "👋 Привіт, мене звати Свайпі🙃\n"
        "\n"
        "Відправ мені повідомлення, щоб створити тему для анонімного обговорення з іншими учасниками спільноти.\n"
        "\n"
        "Повідомлення може бути текстове, звукове, відео, стікер, світлина, опитування тощо.\n"
        "\n"
        "Або ж просто залишайся на зв`язку та відповідай на повідомлення-теми, що надходитимуть.\n"
        "\n"
        "Чорне сердечко🖤 - повідомлення отримали не лише ви, але й інші учасники сервісу (створено нову тему).\n"
        "\n"
        "Червоне сердечко❤️ - вам відповіли і цю відповідь бачите лише ви.\n"
        "\n"
        "Коли ви комусь відповідаєте, ваші відповіді надходять з червоним❤️ сердечком і лише одній людині.\n"
        "\n"
        f"/{Commands.HELP} - показати цей текст\n"
        f"/{Commands.ABOUT} - про бота"
    )
    READ_MORE = "<i>https://toporok.medium.com/як-swipy-працює-зараз-404d70a64cfb</i>"

    READ_HEART = "❤️"
    BLACK_HEART = "🖤"
    REPLY = "Відповісти"
    # STOP = "❌Зупинити"

    NEW_TOPIC_STARTED = f"<i>Ви створили нову тему для розмов - очікуйте відповідей ⏳</i>\n/{Commands.HELP}"
    # REVOKE_TOPIC = "⛔️Відкликати"

    TALK_NOT_FOUND = f"<i>💔 Розмову не знайдено</i>\n/{Commands.HELP}"
    MESSAGE_NOT_TRANSMITTED = f"<i>Повідомлення не відправлено 😞</i>\n/{Commands.HELP}"
    FAILED_TO_EDIT_AT_RECEIVER = f"<i>Не вдалося відредагувати у отримувача 😞</i>\n/{Commands.HELP}"
