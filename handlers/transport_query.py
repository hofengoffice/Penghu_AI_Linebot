"""
交通查詢對話流程 handler

功能：
    - 交通查詢   → 顯示交通選單 Flex Message
    - 飛機航班   → 送出 LIFF 入口按鈕
    - 船班資訊 / 租車服務 / 機車租借 / 自行車漫遊
                 → 顯示資訊卡片，含「加入心願清單」按鈕
                 → 選數量後存入收藏清單
"""

import os
import json
from datetime import datetime

from flex.transport_menu import get_transport_menu
from flex.flight_liff_btn import get_flight_liff_btn
from utils.liff_token import create as create_liff_token

FAVORITES_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "favorites")

_TRANSPORT_INFO = {
    "船班資訊": {
        "emoji": "⛴️",
        "color": "#3a7abf",
        "unit": "張",
        "info": (
            "【台華輪】高雄 ↔ 馬公\n"
            "• 航程約 4–6 小時\n"
            "• 每日一至數班（依季節調整）\n"
            "• 訂票：台灣航業官網或電話\n"
            "  📞 07-561-3866（高雄）\n\n"
            "【台馬輪】基隆/台中 ↔ 馬公\n"
            "• 航程約 8–10 小時（含離島航線）\n\n"
            "⚠️ 船班受天候影響，出發前請確認最新動態。"
        )
    },
    "租車服務": {
        "emoji": "🚗",
        "color": "#E08840",
        "unit": "台",
        "info": (
            "澎湖島內有多家租車業者，建議提前預約：\n"
            "• 馬公市區及機場附近均有租車點\n"
            "• 可租 4~7 人座轎車或休旅車\n"
            "• 費用約 NT$1,500–2,500 / 天\n\n"
            "建議搜尋「澎湖租車」選擇有口碑的業者，出發前電話確認。"
        )
    },
    "機車租借": {
        "emoji": "🛵",
        "color": "#E05C5C",
        "unit": "台",
        "info": (
            "機車是澎湖最方便的島內交通工具：\n"
            "• 機場、馬公市區、各大飯店附近均有租借點\n"
            "• 需持有效機車駕照（含國際駕照）\n"
            "• 費用約 NT$300–500 / 天（機車）\n"
            "• 電動機車也可租借，更環保省錢\n\n"
            "⚠️ 澎湖多風，騎車請注意安全，戴好安全帽！"
        )
    },
    "自行車漫遊": {
        "emoji": "🚲",
        "color": "#3aab6a",
        "unit": "台",
        "info": (
            "享受慢遊澎湖的愜意時光：\n"
            "• 馬公市區及觀音亭周邊有自行車道\n"
            "• 租借費用約 NT$100–200 / 小時\n"
            "• 適合短程景點遊覽，不適合跨島\n\n"
            "推薦路線：觀音亭海濱公園 → 馬公老街 → 天后宮"
        )
    },
}


def _get_transport_info_flex(transport_type):
    """回傳交通資訊 Flex bubble，含加入心願清單按鈕"""
    info = _TRANSPORT_INFO[transport_type]
    return {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": info["color"],
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": f"{info['emoji']} {transport_type}",
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "text",
                    "text": info["info"],
                    "size": "sm",
                    "color": "#555555",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": info["color"],
                    "action": {
                        "type": "postback",
                        "label": "📋 加入心願清單",
                        "data": f"transport_book={transport_type}",
                        "displayText": f"加入 {transport_type} 至心願清單"
                    }
                }
            ]
        }
    }


def _get_favorites(user_id):
    os.makedirs(FAVORITES_DIR, exist_ok=True)
    path = os.path.join(FAVORITES_DIR, f"{user_id}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_favorites(user_id, favorites):
    os.makedirs(FAVORITES_DIR, exist_ok=True)
    path = os.path.join(FAVORITES_DIR, f"{user_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


# ── 訊息入口 ────────────────────────────────────────────────

def handle(user_id, text, reply_token, user_states, reply_fn, push_fn, reply_flex_fn):
    # ── 入口：交通選單 ──
    if text == "交通查詢":
        user_states[user_id] = {"step": "start"}
        reply_flex_fn(reply_token, get_transport_menu(), "🚌 交通查詢")
        return True

    # ── 飛機航班：LIFF ──
    if text == "飛機航班":
        liff_id  = os.getenv("LIFF_ID", "")
        token    = create_liff_token(user_id)
        liff_url = f"https://liff.line.me/{liff_id}?token={token}"
        reply_flex_fn(reply_token, get_flight_liff_btn(liff_url), "🛫 飛機航班查詢")
        return True

    # ── 其他交通：資訊卡片 + 加入清單按鈕 ──
    if text in _TRANSPORT_INFO:
        user_states[user_id] = {"step": "start"}
        reply_flex_fn(reply_token, _get_transport_info_flex(text), f"{text}")
        return True

    return False


# ── Postback 入口 ────────────────────────────────────────────

def handle_postback(user_id, data, date_param, reply_token, user_states,
                    reply_fn, push_fn, reply_flex_fn, reply_quick_reply_fn=None):
    # ── 加入心願清單：選數量 ──
    if data.startswith("transport_book="):
        transport_type = data.split("=", 1)[1]
        info = _TRANSPORT_INFO.get(transport_type)
        if not info or not reply_quick_reply_fn:
            return False
        unit = info["unit"]
        reply_quick_reply_fn(
            reply_token,
            f"請選擇 {info['emoji']} {transport_type} 的數量：",
            [(f"{i} {unit}", f"transport_qty={transport_type}&val={i}") for i in range(1, 7)]
        )
        return True

    # ── 確認數量：存入收藏 ──
    if data.startswith("transport_qty="):
        from urllib.parse import parse_qs
        params = parse_qs(data)
        transport_type = params.get("transport_qty", [""])[0]
        qty = int(params.get("val", ["1"])[0])
        info = _TRANSPORT_INFO.get(transport_type, {})

        now = datetime.now()
        item_id   = f"transport_{transport_type}_{now.strftime('%Y%m%d%H%M%S')}"
        item_name = f"{info.get('emoji', '🚌')} {transport_type} x{qty}"

        favorites = _get_favorites(user_id)
        favorites.append({"id": item_id, "name": item_name, "type": "transport"})
        _save_favorites(user_id, favorites)

        reply_fn(reply_token,
            f"✅ 已將「{item_name}」加入心願清單！\n\n"
            f"可至「收藏清單」查看並送出詢價。"
        )
        return True

    return False
