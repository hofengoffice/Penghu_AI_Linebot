"""
空房查詢對話流程 handler

觸發詞：
    空房查詢         → 顯示空房查詢主選單
    立即查詢住宿日期  → 引導輸入入住／退房日期（待串接飯店 API）
    價格與優惠       → 顯示價格說明（待填入）
    房間照片         → 顯示房間照片（待填入）
    房間預定         → 互動式流程：日曆選日期 → Quick Reply 選人數 → Quick Reply 選備註
"""

import os
import json
from datetime import datetime
from flex.room_menu import get_room_menu

FAVORITES_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "favorites")

_NOTE_OPTIONS = ["無備註", "需嬰兒床", "蜜月旅行", "慶生", "親子出遊", "無障礙需求"]


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


def _get_date_picker_bubble(title, action_data, min_date=None):
    """回傳帶有 datetimepicker 按鈕的 Flex bubble"""
    action = {
        "type": "datetimepicker",
        "label": "點此選擇日期",
        "data": action_data,
        "mode": "date"
    }
    if min_date:
        action["min"] = min_date.replace("/", "-")

    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "md",
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
                    "color": "#4EADAC",
                    "action": action
                }
            ]
        }
    }


def handle(user_id, text, reply_token, user_states, reply_fn, push_fn, reply_flex_fn, reply_quick_reply_fn=None):
    state = user_states.get(user_id, {})

    # ── 入口 ──────────────────────────────────────────────
    if text == "空房查詢":
        user_states[user_id] = {"step": "start"}
        reply_flex_fn(reply_token, get_room_menu(), "🏨 空房查詢")
        return True

    # ── 立即查詢住宿日期 ───────────────────────────────────
    if text == "立即查詢住宿日期":
        user_states[user_id] = {"step": "room_checkin"}
        reply_fn(reply_token, "📅 請輸入入住日期：\n格式：2026/07/01")
        return True

    if state.get("step") == "room_checkin":
        date = _parse_date(text)
        if not date:
            reply_fn(reply_token, "❌ 日期格式錯誤，請使用 2026/07/01 格式")
            return True
        user_states[user_id] = {"step": "room_checkout", "checkin": date}
        reply_fn(reply_token, f"📅 入住：{date}\n\n請輸入退房日期：")
        return True

    if state.get("step") == "room_checkout":
        date = _parse_date(text)
        if not date:
            reply_fn(reply_token, "❌ 日期格式錯誤，請使用 2026/07/01 格式")
            return True
        checkin = state.get("checkin")
        user_states[user_id] = {"step": "start"}
        reply_fn(reply_token,
            f"🔍 查詢中...\n\n"
            f"📅 入住：{checkin}\n"
            f"📅 退房：{date}\n\n"
            f"（空房查詢功能開發中，敬請期待）"
        )
        return True

    # ── 房間預定：送出日曆選取器 ────────────────────────────
    if text == "房間預定":
        user_states[user_id] = {"step": "room_book_waiting"}
        reply_flex_fn(reply_token, _get_date_picker_bubble(
            "🏨 房間預定\n\n第 1 步：請選擇入住日期",
            "room_book_step=checkin"
        ), "選擇入住日期")
        return True

    # ── 靜態資訊回覆（待填入正式內容） ───────────────────────
    if text == "價格與優惠":
        reply_fn(reply_token, "💰 價格與優惠\n\n（內容待填入）")
        user_states[user_id] = {"step": "start"}
        return True

    if text == "房間照片":
        reply_fn(reply_token, "📷 房間照片\n\n（內容待填入）")
        user_states[user_id] = {"step": "start"}
        return True

    return False


def handle_postback(user_id, data, date_param, reply_token, user_states, reply_fn, reply_quick_reply_fn, reply_flex_fn):
    """處理房間預定相關 postback（日期選取、人數、備註）"""
    if not data.startswith("room_book_step="):
        return False

    from urllib.parse import parse_qs
    params = parse_qs(data)
    step  = params.get("room_book_step", [""])[0]
    state = user_states.get(user_id, {})

    # ── 選完入住日期 → 送出退房日曆 ───────────────────────
    if step == "checkin":
        checkin = date_param.replace("-", "/") if date_param else None
        if not checkin:
            reply_fn(reply_token, "❌ 日期取得失敗，請重新操作")
            return True
        user_states[user_id] = {"step": "room_book_waiting", "checkin": checkin}
        reply_flex_fn(reply_token, _get_date_picker_bubble(
            f"✅ 入住：{checkin}\n\n第 2 步：請選擇退房日期",
            "room_book_step=checkout",
            min_date=checkin
        ), "選擇退房日期")
        return True

    # ── 選完退房日期 → Quick Reply 選人數 ─────────────────
    if step == "checkout":
        checkout = date_param.replace("-", "/") if date_param else None
        checkin  = state.get("checkin")
        if not checkout:
            reply_fn(reply_token, "❌ 日期取得失敗，請重新操作")
            return True
        if checkout <= checkin:
            reply_flex_fn(reply_token, _get_date_picker_bubble(
                f"入住：{checkin}\n❌ 退房需晚於入住，請重新選擇",
                "room_book_step=checkout",
                min_date=checkin
            ), "重新選擇退房日期")
            return True
        user_states[user_id] = {**state, "checkout": checkout}
        reply_quick_reply_fn(
            reply_token,
            f"✅ 入住：{checkin} → 退房：{checkout}\n\n第 3 步：請選擇入住人數",
            [(f"{i} 人", f"room_book_step=pax&val={i}") for i in range(1, 7)]
        )
        return True

    # ── 選完人數 → Quick Reply 選備註 ─────────────────────
    if step == "pax":
        pax = int(params.get("val", ["1"])[0])
        user_states[user_id] = {**state, "pax": pax}
        checkin  = state.get("checkin")
        checkout = state.get("checkout")
        reply_quick_reply_fn(
            reply_token,
            f"✅ 入住：{checkin} → 退房：{checkout}　{pax} 人\n\n第 4 步：請選擇備註",
            [(opt, f"room_book_step=note&val={opt}") for opt in _NOTE_OPTIONS]
        )
        return True

    # ── 選完備註 → 存入收藏 ────────────────────────────────
    if step == "note":
        note     = params.get("val", ["無備註"])[0]
        checkin  = state.get("checkin")
        checkout = state.get("checkout")
        pax      = state.get("pax", 1)
        user_states[user_id] = {"step": "start"}

        now = datetime.now()
        item_id   = f"accommodation_{user_id}_{now.strftime('%Y%m%d%H%M%S')}"
        item_name = f"🏨 住宿預定 {checkin}～{checkout} {pax}人"

        favorites = _get_favorites(user_id)
        favorites.append({
            "id":       item_id,
            "name":     item_name,
            "type":     "accommodation",
            "checkin":  checkin,
            "checkout": checkout,
            "pax":      pax,
            "note":     note
        })
        _save_favorites(user_id, favorites)

        reply_fn(reply_token,
            f"✅ 已將住宿預定加入收藏清單！\n\n"
            f"📅 入住：{checkin}\n"
            f"📅 退房：{checkout}\n"
            f"👥 人數：{pax} 人\n"
            + (f"📝 備註：{note}\n" if note != "無備註" else "") +
            f"\n可至「收藏清單」查看並送出詢價。"
        )
        return True

    return False


def _parse_date(text):
    """解析日期，支援 2026/07/01 或 2026-07-01，回傳標準格式或 None"""
    import re
    m = re.fullmatch(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", text.strip())
    if m:
        return f"{m.group(1)}/{int(m.group(2)):02d}/{int(m.group(3)):02d}"
    return None
