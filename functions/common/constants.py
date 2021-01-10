class ConvState:
    # using plain str constants because json lib doesn't serialize Enum
    ENTRY_STATE = 'ENTRY_STATE'

    USER_REPLIED = 'USER_REPLIED'
    BOT_REPLIED = 'BOT_REPLIED'

    FALLBACK_STATE = 'FALLBACK_STATE'


class SwiperState:
    """
    Swiper states are maintained separately from PTB conversation states because their purpose is to help with matching
    people rather than to track the "mechanics" of the conversation (the latter being the case with PTB conversation
    states).
    The logic of swiper states is meant to be simpler than that of PTB conversation states. The latter is expected to
    have more states and be tracked at more than one level (per chat, per message, nested conversations, maybe per user
    as well) while the former is supposed to only have one level (a state of the swiper aka user so the system can
    decide whom to match with whom at any given moment).
    """
    # TODO oleksandr
    ...


class DataKey:
    UPDATE_FILENAME = 'update_filename'

    IS_BOT_SILENT = 'is_bot_silent'

    LATEST_MSG_ID = 'latest_msg_id'  # this can be either a user thought or a bot answer to it
    LATEST_ANSWER_MSG_ID = 'latest_answer_msg_id'

    THOUGHT_CTX = 'thought_ctx'
    TEXT = 'text'
    THOUGHT_ID = 'thought_id'
    MSG_ID = 'msg_id'
    CONV_STATE = 'conv_state'
    TIMESTAMP_MS = 'timestamp_ms'

    ANSWERER_MODE = 'answerer_mode'

    # "volatile" objects
    ANSWERER = 'answerer'


class EsKey:
    ANSWER = 'answer'
    ANSWER_THOUGHT_ID = 'answer_thought_id'
    CTX1 = 'ctx1'
    CTX2 = 'ctx2'
    CTX3 = 'ctx3'
    CTX5 = 'ctx5'
    CTX8 = 'ctx8'
    CTX13 = 'ctx13'


class AnswererMode:
    SIMPLEST_QUESTION_MATCH = 'simplest-question-match'
    CTX8_CTX1B13 = 'ctx8-ctx1b13'

    DEFAULT = SIMPLEST_QUESTION_MATCH
