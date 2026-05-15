"""
收藏清單 handler

功能：
    - handle()         : 處理「收藏清單」觸發詞，以 Flex bubble 分類顯示收藏列表
    - handle_postback(): 處理收藏、刪除、詳情、收藏AI行程、收藏航班五種 postback action

收藏分類（type 欄位）：
    trip          → 🗺️ 行程（熱門行程）
    itinerary     → 🗺️ 行程（AI 智慧查詢行程）
    transport     → ✈️ 交通（航班）
    accommodation → 🏨 住宿（未來擴充）
"""

import json
import os
import shutil
import threading
from datetime import datetime
from urllib.parse import parse_qs
from flex.trip_detail import get_trip_detail_carousel

FAVORITES_DIR   = os.path.join(os.path.dirname(__file__), "..", "storage", "favorites")
ITINERARIES_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "itineraries")
_TRIPS_PATH     = os.path.join(os.path.dirname(__file__), "..", "data", "popular_trips.json")

# 分類定義：(顯示標題, 包含的 type 清單)
_CATEGORIES = [
    ("🗺️ 行程",  ["trip", "itinerary"]),
    ("✈️ 交通",  ["transport"]),
    ("🏨 住宿",  ["accommodation"]),
]


# ── 工具函式 ───────────────────────────────────────────────

def _get_favorites(user_id):
    """讀取用戶收藏清單，不存在則回傳空 list"""
    os.makedirs(FAVORITES_DIR, exist_ok=True)
    path = os.path.join(FAVORITES_DIR, f"{user_id}.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_favorites(user_id, favorites):
    """儲存用戶收藏清單"""
    os.makedirs(FAVORITES_DIR, exist_ok=True)
    path = os.path.join(FAVORITES_DIR, f"{user_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def _find_trip(trip_id):
    """從 popular_trips.json 以 id 查找行程 dict，查無回傳 None"""
    with open(_TRIPS_PATH, "r", encoding="utf-8") as f:
        all_trips = json.load(f)
    for trips in all_trips.values():
        for t in trips:
            if t["id"] == trip_id:
                return t
    return None


def _build_favorites_bubble(favorites):
    """
    將收藏 list 轉為單一 bubble，依行程／交通／住宿分類顯示。
    - 行程類：名稱 + 詳情按鈕（trip）或無詳情（itinerary）+ 刪除
    - 交通類：名稱 + 刪除
    - 住宿類：名稱 + 刪除
    """
    contents = [
        {
            "type": "text",
            "text": "⭐ 收藏清單",
            "weight": "bold",
            "size": "lg",
            "margin": "none"
        },
        {"type": "separator", "margin": "md"}
    ]

    has_any = False

    for cat_title, cat_types in _CATEGORIES:
        items = [f for f in favorites if f.get("type") in cat_types]
        if not items:
            continue
        has_any = True

        # 分類標題
        contents.append({
            "type": "text",
            "text": cat_title,
            "weight": "bold",
            "size": "sm",
            "color": "#4EADAC",
            "margin": "lg"
        })

        for item in items:
            row = [
                {
                    "type": "text",
                    "text": item["name"],
                    "flex": 3,
                    "size": "sm",
                    "wrap": True
                }
            ]

            # 熱門行程 & AI 行程有詳情按鈕；航班不需要（資訊已在名稱中）
            if item.get("type") in ("trip", "itinerary"):
                row.append({
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "flex": 2,
                    "action": {
                        "type": "postback",
                        "label": "詳情",
                        "data": f"action=trip_detail&id={item['id']}" if item.get("type") == "trip" else f"action=itinerary_detail&id={item['id']}",
                        "displayText": f"查看「{item['name']}」詳情"
                    }
                })

            row.append({
                "type": "button",
                "style": "primary",
                "color": "#E05C5C",
                "height": "sm",
                "flex": 2,
                "margin": "sm",
                "action": {
                    "type": "postback",
                    "label": "刪除",
                    "data": f"action=unfavorite&id={item['id']}&name={item['name']}",
                    "displayText": f"刪除「{item['name']}」"
                }
            })

            contents.append({
                "type": "box",
                "layout": "horizontal",
                "alignItems": "center",
                "margin": "sm",
                "contents": row
            })

    if not has_any:
        contents.append({
            "type": "text",
            "text": "尚無收藏項目",
            "size": "sm",
            "color": "#AAAAAA",
            "align": "center",
            "margin": "xl"
        })

    bubble = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": contents
        }
    }

    # 有收藏項目時，在 footer 加「確認詢價」按鈕
    if has_any:
        bubble["footer"] = {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#4EADAC",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "📩 確認詢價，通知負責人",
                        "data": "action=confirm_inquiry",
                        "displayText": "確認送出心願清單詢價"
                    }
                }
            ]
        }

    return bubble


# ── 主要 handler ───────────────────────────────────────────

def handle(user_id, text, reply_token, user_states, reply_fn, push_fn, reply_flex_fn):
    """處理「收藏清單」觸發詞，以 Flex bubble 分類顯示收藏列表"""
    if text != "收藏清單":
        return False

    favorites = _get_favorites(user_id)

    if not favorites:
        reply_fn(reply_token, "你的收藏清單是空的！\n快去熱門行程找喜歡的行程收藏吧 ⭐")
        return True

    reply_flex_fn(reply_token, _build_favorites_bubble(favorites), "⭐ 收藏清單")
    return True


def handle_postback(user_id, data, reply_token, reply_fn, reply_flex_fn):
    """
    處理五種 postback action：
        favorite           → 收藏熱門行程
        unfavorite         → 刪除收藏
        trip_detail        → 顯示行程詳細卡片
        favorite_itinerary → 收藏 AI 智慧查詢產生的行程
        flight_favorite    → 收藏航班查詢結果
    """
    params = parse_qs(data)
    action = params.get("action", [""])[0]

    # ── 收藏熱門行程 ──
    if action == "favorite":
        trip_id   = params.get("id",   [""])[0]
        trip_name = params.get("name", [""])[0]
        favorites = _get_favorites(user_id)

        if any(f["id"] == trip_id for f in favorites):
            reply_fn(reply_token, f"「{trip_name}」已在收藏清單中 ⭐")
            return

        favorites.append({"id": trip_id, "name": trip_name, "type": "trip"})
        _save_favorites(user_id, favorites)
        reply_fn(reply_token, f"✅ 已收藏「{trip_name}」！\n可至「收藏清單」查看所有收藏。")

    # ── 刪除 ──
    elif action == "unfavorite":
        trip_id   = params.get("id",   [""])[0]
        trip_name = params.get("name", [""])[0]
        favorites = _get_favorites(user_id)
        new_list  = [f for f in favorites if f["id"] != trip_id]

        if len(new_list) == len(favorites):
            reply_fn(reply_token, "找不到該收藏項目。")
            return

        _save_favorites(user_id, new_list)
        reply_fn(reply_token, f"🗑 已刪除「{trip_name}」")

    # ── 熱門行程詳情 ──
    elif action == "trip_detail":
        trip_id = params.get("id", [""])[0]
        trip    = _find_trip(trip_id)

        if not trip:
            reply_fn(reply_token, "找不到該行程資料。")
            return

        reply_flex_fn(reply_token, get_trip_detail_carousel([trip], unfavorite=True), trip["name"])

    # ── 收藏 AI 行程 ──
    elif action == "favorite_itinerary":
        # 讀取該用戶最新的 AI 行程文字
        path = os.path.join(ITINERARIES_DIR, f"{user_id}_latest.txt")
        if not os.path.exists(path):
            reply_fn(reply_token, "找不到行程內容，請重新查詢。")
            return

        # 用時間戳產生唯一 id，顯示名稱加上日期
        now = datetime.now()
        itinerary_id   = f"itinerary_{user_id}_{now.strftime('%Y%m%d%H%M%S')}"
        itinerary_name = f"AI行程 {now.strftime('%m/%d %H:%M')}"

        favorites = _get_favorites(user_id)

        # 避免重複收藏同一份（同秒內）
        if any(f["id"] == itinerary_id for f in favorites):
            reply_fn(reply_token, "此行程已在收藏清單中 ⭐")
            return

        favorites.append({"id": itinerary_id, "name": itinerary_name, "type": "itinerary"})
        _save_favorites(user_id, favorites)
        # 存一份以 itinerary_id 命名的副本，供日後詳情查看使用
        shutil.copy(path, os.path.join(ITINERARIES_DIR, f"{itinerary_id}.txt"))
        reply_fn(reply_token, f"✅ 已收藏「{itinerary_name}」！\n可至「收藏清單」查看。")

    # ── AI 行程詳情 ──
    elif action == "itinerary_detail":
        trip_id   = params.get("id", [""])[0]
        itin_path = os.path.join(ITINERARIES_DIR, f"{trip_id}.txt")
        if not os.path.exists(itin_path):
            reply_fn(reply_token, "找不到行程內容，可能已過期，請重新查詢。")
            return
        with open(itin_path, "r", encoding="utf-8") as f:
            content = f.read()
        reply_fn(reply_token, content[:4000])   # LINE 單則文字上限 5000 字

    # ── 收藏航班 ──
    elif action == "flight_favorite":
        flight_id   = params.get("id",      [""])[0]
        flight_name = params.get("name",    [""])[0]
        airline     = params.get("airline", [""])[0]
        favorites   = _get_favorites(user_id)

        if any(f["id"] == flight_id for f in favorites):
            reply_fn(reply_token, f"「{flight_name}」已在收藏清單中 ⭐")
            return

        favorites.append({
            "id":      flight_id,
            "name":    flight_name,
            "type":    "transport",
            "airline": airline
        })
        _save_favorites(user_id, favorites)
        reply_fn(reply_token, f"✅ 已收藏「{flight_name}」！\n可至「收藏清單」查看。")

    # ── 確認詢價，寄 email 給負責人 ──
    elif action == "confirm_inquiry":
        from services.email_service import send_inquiry_email, generate_order_no
        favorites = _get_favorites(user_id)

        if not favorites:
            reply_fn(reply_token, "收藏清單是空的，無法送出詢價。")
            return

        order_no = generate_order_no()
        reply_fn(reply_token,
                 f"✅ 已收到您的心願清單！\n"
                 f"訂單編號：{order_no}\n\n"
                 f"我們的工作人員將儘速與您聯繫，請稍候。")

        def _send():
            try:
                send_inquiry_email(order_no, favorites)
                print(f"[Email] 詢價通知已寄出，order_no={order_no!r}")
            except Exception as e:
                print(f"[Email] 寄送失敗：{e}")

        threading.Thread(target=_send, daemon=True).start()
