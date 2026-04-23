"""
交通查詢對話流程 handler

功能：
    - 交通查詢   → 顯示交通選單 Flex Message
    - 飛機航班   → 送出 LIFF 入口按鈕，使用者在 LIFF 網頁填寫查詢條件後送出，
                   bot 在背景執行爬蟲並 push 結果（整個流程不產生中間訊息）
    - 船班資訊   → 顯示台華輪靜態資訊
    - 租車服務 / 機車租借 / 自行車漫遊 → 顯示靜態文字
"""

import os

from flex.transport_menu import get_transport_menu
from flex.flight_liff_btn import get_flight_liff_btn
from utils.liff_token import create as create_liff_token


# ── 訊息入口 ────────────────────────────────────────────────

def handle(user_id, text, reply_token, user_states, reply_fn, push_fn, reply_flex_fn):
    """
    交通查詢主入口（處理文字訊息）。

    回傳：
        True  → 此訊息已由本 handler 處理
        False → 非本 handler 負責，交由下一個 handler 判斷
    """

    # ── 入口：交通選單 ──
    if text == "交通查詢":
        user_states[user_id] = {"step": "start"}
        reply_flex_fn(reply_token, get_transport_menu(), "🚌 交通查詢")
        return True

    # ── 飛機航班：送出 LIFF 入口按鈕（URL 帶一次性 token，不依賴 LIFF userId）──
    if text == "飛機航班":
        liff_id  = os.getenv("LIFF_ID", "")
        token    = create_liff_token(user_id)
        liff_url = f"https://liff.line.me/{liff_id}?token={token}"
        reply_flex_fn(reply_token, get_flight_liff_btn(liff_url), "🛫 飛機航班查詢")
        return True

    # ── 島內交通：靜態資訊 ──
    if text == "租車服務":
        reply_fn(reply_token,
            "🚗 澎湖租車服務\n\n"
            "澎湖島內有多家租車業者，建議提前預約：\n"
            "• 馬公市區及機場附近均有租車點\n"
            "• 可租 4~7 人座轎車或休旅車\n"
            "• 費用約 NT$1,500–2,500 / 天\n\n"
            "建議搜尋「澎湖租車」選擇有口碑的業者，出發前電話確認。"
        )
        user_states[user_id] = {"step": "start"}
        return True

    if text == "機車租借":
        reply_fn(reply_token,
            "🛵 澎湖機車租借\n\n"
            "機車是澎湖最方便的島內交通工具：\n"
            "• 機場、馬公市區、各大飯店附近均有租借點\n"
            "• 需持有效機車駕照（含國際駕照）\n"
            "• 費用約 NT$300–500 / 天（機車）\n"
            "• 電動機車也可租借，更環保省錢\n\n"
            "⚠️ 澎湖多風，騎車請注意安全，戴好安全帽！"
        )
        user_states[user_id] = {"step": "start"}
        return True

    if text == "自行車漫遊":
        reply_fn(reply_token,
            "🚲 澎湖自行車漫遊\n\n"
            "享受慢遊澎湖的愜意時光：\n"
            "• 馬公市區及觀音亭周邊有自行車道\n"
            "• 租借費用約 NT$100–200 / 小時\n"
            "• 適合短程景點遊覽，不適合跨島\n\n"
            "推薦路線：觀音亭海濱公園 → 馬公老街 → 天后宮"
        )
        user_states[user_id] = {"step": "start"}
        return True

    # ── 入島交通：船班資訊（靜態） ──
    if text == "船班資訊":
        reply_fn(reply_token,
            "⛴ 澎湖船班資訊\n\n"
            "【台華輪】高雄 ↔ 馬公\n"
            "• 航程約 4–6 小時\n"
            "• 每日一至數班（依季節調整）\n"
            "• 訂票：台灣航業官網或電話\n"
            "  📞 07-561-3866（高雄）\n\n"
            "【台馬輪】基隆/台中 ↔ 馬公\n"
            "• 航程約 8–10 小時（含離島航線）\n\n"
            "⚠️ 船班受天候影響，出發前請確認最新動態。\n"
            "🔗 建議至台灣航業官網查詢即時班次。"
        )
        user_states[user_id] = {"step": "start"}
        return True

    return False


# ── Postback 入口 ────────────────────────────────────────────

def handle_postback(user_id, data, date_param, reply_token, user_states,
                    reply_fn, push_fn, reply_flex_fn):
    """
    飛機查詢已改為 LIFF 流程，此 handler 不再處理 flight_* postback。
    保留函式簽名供 app.py 呼叫，一律回傳 False。
    """
    return False
