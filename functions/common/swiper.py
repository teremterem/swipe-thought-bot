# TODO oleksandr: move this module outside of common ?
#  give it a more descriptive name, too ?
#  and also rename swiper_telegram.py to something else ?
import logging

from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters

from functions.common.swiper_telegram import BaseSwiperConversation, StateAwareHandlers, BaseSwiperPresentation

logger = logging.getLogger(__name__)


class ConvState:
    # using plain str constants because json lib doesn't serialize Enum
    ENTRY_STATE = 'ENTRY_STATE'

    USER_REPLIED = 'USER_REPLIED'
    BOT_REPLIED = 'BOT_REPLIED'

    FALLBACK_STATE = 'FALLBACK_STATE'


class SwiperConversation(BaseSwiperConversation):
    def init_swiper_presentation(self, swiper_presentation):
        if not swiper_presentation:
            swiper_presentation = SwiperPresentation(swiper_conversation=self)
        return swiper_presentation

    def configure_dispatcher(self, dispatcher):
        conv_state_dict = {}
        CommonStateHandlers(ConvState.USER_REPLIED, self).register_state_handlers(conv_state_dict)
        CommonStateHandlers(ConvState.BOT_REPLIED, self).register_state_handlers(conv_state_dict)

        conv_handler = ConversationHandler(
            per_chat=True,
            per_user=False,
            per_message=False,
            entry_points=CommonStateHandlers(ConvState.ENTRY_STATE, self).handlers,
            allow_reentry=False,
            states=conv_state_dict,
            fallbacks=CommonStateHandlers(ConvState.FALLBACK_STATE, self).handlers,
            name='swiper_main',
            persistent=True,
        )
        dispatcher.add_handler(conv_handler)


class CommonStateHandlers(StateAwareHandlers):
    def configure_handlers(self):
        handlers = [
            CommandHandler('start', self.start),
            MessageHandler(Filters.text & ~Filters.command, self.user_thought),
        ]
        return handlers

    def start(self, update, context):
        self.swiper_presentation.say_hello(update, context, self.conv_state)
        return ConvState.BOT_REPLIED

    def user_thought(self, update, context):
        self.swiper_presentation.say_test(update, context, self.conv_state)
        return ConvState.USER_REPLIED


class SwiperPresentation(BaseSwiperPresentation):
    def say_hello(self, update, context, conv_state):
        update.effective_chat.send_message(
            f"Hello, human!\n"
            f"The last state of our conversation was: {conv_state}"
        )

    def say_test(self, update, context, conv_state):
        update.effective_chat.send_message(
            f"TEST!\n"
            f"The last state of our conversation was: {conv_state}"
        )
