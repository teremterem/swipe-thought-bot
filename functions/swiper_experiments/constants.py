class CallbackData:
    REPLY = 'reply'
    STOP = 'stop'


class Commands:
    START = 'start'
    HELP = 'help'
    ABOUT = 'about'


class Text:
    READ_HEART = "❤️"
    BLACK_HEART = "🖤"
    REPLY = "Відповісти"
    STOP = "❌Зупинити"

    HELP = (
        "👋 Привіт, мене звати Свайпі🙃\n"
        "\n"
        "Відправ мені повідомлення, щоб створити тему для обговорення з іншими учасниками спільноти.\n"
        "\n"
        "Повідомлення може бути текстове, звукове, відео, стікер, світлина, опитування тощо.\n"
        "\n"
        "Або ж просто залишайся на зв`язку та відповідай на повідомлення, що надходитимуть.\n"
        "\n"
        "Якщо ти створиш тему для обговорення, вона буде <i><b>анонімно</b></i> надіслана <i><b>усім</b></i> "
        "учасникам спільноти.\n"
        "\n"
        "А якщо ти відповіси на повідомлення, що надійшло тобі, твою відповідь побачить <i><b>лише</b></i> автор "
        "повідомлення, що надійшло (це буде також анонімно).\n"
        "\n"
        f"/{Commands.HELP} - показати цей текст\n"
        f"/{Commands.ABOUT} - про бота"
    )
    READ_MORE = (
        "<i>https://toporok.medium.com/як-swipy-працює-зараз-404d70a64cfb</i>"
    )

    TALK_NOT_FOUND = f"<i>💔 Розмову не знайдено</i>\n/{Commands.HELP}"
    TALK_STOPPED = "🚧 Ця функція поки що не реалізована"

    NEW_TOPIC_STARTED = f"<i>Ви створили нову тему для розмов - очікуйте відповідей ⏳</i>\n/{Commands.HELP}"
    REVOKE_TOPIC = "⛔️Відкликати"

    MESSAGE_NOT_TRANSMITTED = f"<i>Повідомлення не відправлено 😞</i>\n/{Commands.HELP}"
    FAILED_TO_EDIT_AT_RECEIVER = f"<i>Не вдалося відредакгувати у отримувача 😞</i>\n/{Commands.HELP}"
