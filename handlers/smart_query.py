"""
智慧查詢對話流程處理器

觸發條件：使用者點選主選單「智慧查詢」按鈕
流程：
    1. 使用者點「智慧查詢」→ 回覆引導訊息，等待輸入需求
    2. 使用者輸入需求      → 先回覆「規劃中」，背景執行 RAG pipeline
    3. RAG 完成            → 儲存結果至 storage/itineraries/，push Flex 卡片給使用者
"""

import os
import threading
from services.rag_service import rag_smart_reply
from flex.smart_result import get_smart_result_bubble

# 儲存每位用戶最新 AI 行程的目錄
ITINERARIES_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "itineraries")


def save_latest_itinerary(user_id, text):
    """將行程文字儲存為 storage/itineraries/{user_id}_latest.txt"""
    os.makedirs(ITINERARIES_DIR, exist_ok=True)
    path = os.path.join(ITINERARIES_DIR, f"{user_id}_latest.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_latest_itinerary(user_id):
    """讀取該用戶最新的 AI 行程文字，不存在則回傳 None"""
    path = os.path.join(ITINERARIES_DIR, f"{user_id}_latest.txt")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def handle(user_id, text, reply_token, user_states, reply_fn, push_fn, push_flex_fn):
    """
    智慧查詢的訊息處理入口。

    參數：
        user_id      : LINE 使用者 ID
        text         : 使用者傳入的文字
        reply_token  : LINE reply token（只能用一次，且有時效）
        user_states  : 全域對話狀態 dict，記錄每位使用者目前的步驟
        reply_fn     : reply(reply_token, text) — 即時回覆（有時效限制）
        push_fn      : push(user_id, text)      — 主動推送文字（無時效限制）
        push_flex_fn : push_flex(user_id, flex_dict, alt_text) — 主動推送 Flex

    回傳：
        True  — 此訊息已被智慧查詢處理，app.py 不需再往下判斷
        False — 此訊息與智慧查詢無關，交還給 app.py 繼續處理
    """
    state = user_states.get(user_id, {})
    step = state.get("step", "start")

    # ── Step 1：使用者點選「智慧查詢」────────────────────
    if text == "智慧查詢":
        user_states[user_id] = {"step": "smart_query_input"}
        reply_fn(reply_token, "🤖 請輸入你的需求，例如：\n「喜歡吃海鮮、玩水，規劃三天兩夜」")
        return True

    # ── Step 2：使用者輸入需求────────────────────────────
    if step == "smart_query_input":
        reply_fn(reply_token, "⏳ 正在幫你規劃澎湖行程，約需 30 秒，請稍候...")
        user_states[user_id] = {"step": "start"}

        def _run():
            result = rag_smart_reply(text)
            # 儲存結果，供收藏功能使用
            save_latest_itinerary(user_id, result)
            # 推送 Flex 卡片
            push_flex_fn(user_id, get_smart_result_bubble(result, user_id), "🤖 AI 行程規劃")

        threading.Thread(target=_run, daemon=True).start()
        return True

    return False
