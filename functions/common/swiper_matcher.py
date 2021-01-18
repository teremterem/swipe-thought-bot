import os

SWIPER1_CHAT_ID = os.environ['SWIPER1_CHAT_ID']
SWIPER2_CHAT_ID = os.environ['SWIPER2_CHAT_ID']
SWIPER3_CHAT_ID = os.environ['SWIPER3_CHAT_ID']


def get_all_swiper_chat_ids():
    # TODO oleksandr: get rid of this function later - it does not make much sense outside of prototype
    all_swipers = {
        SWIPER1_CHAT_ID,
        SWIPER2_CHAT_ID,
        SWIPER3_CHAT_ID,
    }
    return all_swipers
