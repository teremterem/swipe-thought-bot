class ConvState:
    # using plain str constants because json lib doesn't serialize Enum
    ENTRY_STATE = 'ENTRY_STATE'

    USER_REPLIED = 'USER_REPLIED'
    BOT_REPLIED = 'BOT_REPLIED'

    FALLBACK_STATE = 'FALLBACK_STATE'


class DataKey:
    LATEST_MSG_ID = 'latest_msg_id'  # this can be either a user thought or a bot answer to it
    LATEST_ANSWER_MSG_ID = 'latest_answer_msg_id'

    THOUGHT_CTX = 'thought_ctx'
    TEXT = 'text'
    THOUGHT_ID = 'thought_id'
    MSG_ID = 'msg_id'
    CONV_STATE = 'conv_state'
    TIMESTAMP_MS = 'timestamp_ms'

    ANSWERER_MODE = 'answerer_mode'


class EsKey:
    ANSWER = 'answer'
    ANSWER_THOUGHT_ID = 'answer_thought_id'
    CTX1 = 'ctx1'
    CTX3 = 'ctx3'
    CTX8 = 'ctx8'


class AnswererMode:
    SIMPLEST_QUESTION_MATCH = 'simplest_question_match'
