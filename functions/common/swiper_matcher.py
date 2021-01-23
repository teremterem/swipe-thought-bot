import os
import random

SWIPER1_CHAT_ID = os.environ['SWIPER1_CHAT_ID']
SWIPER2_CHAT_ID = os.environ['SWIPER2_CHAT_ID']
SWIPER3_CHAT_ID = os.environ['SWIPER3_CHAT_ID']
SWIPER4_CHAT_ID = os.environ['SWIPER4_CHAT_ID']


def get_all_swiper_chat_ids():
    # TODO oleksandr: get rid of this function later - it does not make much sense outside of prototype
    all_swiper_chat_ids = {
        SWIPER1_CHAT_ID,
        SWIPER2_CHAT_ID,
        SWIPER3_CHAT_ID,
        SWIPER4_CHAT_ID,
    }
    return all_swiper_chat_ids


def find_match_for_swiper(swiper_chat_id, exclude_swiper_chat_id=None):
    all_swiper_chat_ids = get_all_swiper_chat_ids()

    all_swiper_chat_ids.remove(str(swiper_chat_id))
    if exclude_swiper_chat_id is not None:
        # TODO oleksandr: get rid of this parameter later - it will not make much sense outside of prototype
        all_swiper_chat_ids.remove(str(exclude_swiper_chat_id))

    return random.choice(tuple(all_swiper_chat_ids))
