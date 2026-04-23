"""
主題清單 handler

功能：
    - 行程主題 → 送出行程類型 carousel（可左右滑）
    - 美食主題 → 送出美食類型 carousel（可左右滑）
    - 交通主題 → 送出交通方式 carousel（可左右滑）
"""

from flex.theme_trip       import get_theme_trip_carousel
from flex.theme_food       import get_theme_food_carousel
from flex.theme_transport  import get_theme_transport_carousel


def handle(user_id, text, reply_token, user_states, reply_fn, push_fn, reply_flex_fn):
    """
    回傳：
        True  → 此訊息已由本 handler 處理
        False → 非本 handler 負責
    """
    if text == "行程主題":
        reply_flex_fn(reply_token, get_theme_trip_carousel(), "🗺️ 行程主題")
        return True

    if text == "美食主題":
        reply_flex_fn(reply_token, get_theme_food_carousel(), "🍽️ 美食主題")
        return True

    if text == "交通主題":
        reply_flex_fn(reply_token, get_theme_transport_carousel(), "🚌 交通主題")
        return True

    return False
