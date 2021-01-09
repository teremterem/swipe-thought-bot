import logging

from functions.common.constants import DataKey, ConvState
from functions.common.utils import timestamp_now_ms, SwiperError

logger = logging.getLogger(__name__)


def construct_thought_id(msg_id, chat_id, bot_id):
    thought_id = f"m{msg_id}_c{chat_id}_b{bot_id}"
    logger.info('THOUGHT ID CONSTRUCTED: %s', thought_id)
    return thought_id


class ThoughtContext:
    def __init__(self, ptb_context):
        self.ptb_ctx = ptb_context

    def get_list(self):
        return self.ptb_ctx.chat_data.setdefault(DataKey.THOUGHT_CTX, [])

    def append_thought(self, text, thought_id, msg_id, conv_state):
        self.get_list().append({
            DataKey.TEXT: text,
            DataKey.THOUGHT_ID: thought_id,
            DataKey.MSG_ID: msg_id,
            DataKey.CONV_STATE: conv_state,
            DataKey.TIMESTAMP_MS: timestamp_now_ms(),
        })

    def trim_context(self, max_thought_ctx_len=15):
        self.ptb_ctx.chat_data[DataKey.THOUGHT_CTX] = self.get_list()[-max_thought_ctx_len:]

    def reject_latest_thought(self, validate_msg_id):
        thoughts = self.get_list()
        if not thoughts:
            raise SwiperError('cannot reject latest thought from context - thought context is empty')

        latest_thought = thoughts[-1]
        latest_thought_msg_id = latest_thought[DataKey.MSG_ID]
        if latest_thought_msg_id != validate_msg_id:
            raise SwiperError(
                f"failed to reject latest thought from context - message id validation failed: "
                f"{validate_msg_id} expected to be latest thought msg id but actual latest was {latest_thought_msg_id}"
            )

        logger.info(
            'REJECTING THOUGHT FROM CONTEXT (msg_id=%s):\n%s', latest_thought_msg_id, latest_thought[DataKey.TEXT]
        )
        del thoughts[-1]

    def get_latest_conv_state(self):
        thoughts = self.get_list()
        if not thoughts:
            return None
        return thoughts[-1][DataKey.CONV_STATE]

    def get_latest_thoughts(self, context_size, user_only=False):
        thoughts = self.get_list()[-context_size:]
        if user_only:
            thoughts = [t for t in thoughts if t[DataKey.CONV_STATE] == ConvState.USER_REPLIED]
        return thoughts

    def concat_latest_thoughts(self, context_size, user_only=False):
        return '\n.\n'.join([t[DataKey.TEXT] for t in self.get_latest_thoughts(context_size, user_only=user_only)])

    def get_latest_thought_ids(self, context_size, user_only=False):
        return [t[DataKey.THOUGHT_ID] for t in self.get_latest_thoughts(context_size, user_only=user_only)]
