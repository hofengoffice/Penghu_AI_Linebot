"""
飛機航班查詢表單 Flex Message

所有欄位集中在同一張靜態卡片（表單送出前不重送、bot 不回傳任何訊息）：
    - 行程類型（單程 / 來回）
    - 出發城市（台北/台中/嘉義/高雄）
    - 出發日期（LINE 原生 datetimepicker）
    - 回程日期（LINE 原生 datetimepicker，不填視為單程）
    - 旅客人數（2歲以上，＋ / － 按鈕）
    - 嬰兒人數（未滿2歲，＋ / － 按鈕）
    - 目的地（澎湖，固定）

互動設計：
    每個按鈕帶有 displayText，點選後對話框會顯示使用者側的泡泡
    （非 bot 訊息，不佔用 reply token），bot 靜默更新 state 即可。
    只有「查詢航班」才會觸發查詢並由 bot 回傳結果。
"""

from datetime import datetime

CITIES = [
    ("TSA", "台北"),
    ("RMQ", "台中"),
    ("CYI", "嘉義"),
    ("KHH", "高雄"),
]

COLOR_PRIMARY  = "#4EADAC"
COLOR_DISABLED = "#CCCCCC"


def get_flight_form():
    """
    回傳飛機查詢表單 bubble dict。
    表單只在「飛機航班」入口送出一次，後續互動不重新渲染。
    """
    today_iso = datetime.now().strftime("%Y-%m-%d")

    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "20px",
            "spacing": "md",
            "contents": [
                # ── 標題 ──
                {
                    "type": "text",
                    "text": "🛫 飛機航班查詢",
                    "weight": "bold",
                    "size": "lg"
                },
                {"type": "separator"},

                # ── 行程類型 ──
                {
                    "type": "text",
                    "text": "行程類型",
                    "size": "sm",
                    "color": "#888888"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        _postback_btn("✈ 單程",  "action=flight_trip_type&value=one_way",   "行程：單程"),
                        _postback_btn("🔄 來回", "action=flight_trip_type&value=round_trip", "行程：來回"),
                    ]
                },

                # ── 出發城市 ──
                {
                    "type": "text",
                    "text": "出發城市",
                    "size": "sm",
                    "color": "#888888"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [_city_btn(code, name) for code, name in CITIES[:2]]
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [_city_btn(code, name) for code, name in CITIES[2:]]
                },

                # ── 出發日期 ──
                {
                    "type": "text",
                    "text": "出發日期",
                    "size": "sm",
                    "color": "#888888"
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "datetimepicker",
                        "label": "選擇出發日期",
                        "data": "action=flight_date",
                        "mode": "date",
                        "initial": today_iso,
                        "min": today_iso
                    }
                },

                # ── 回程日期（不填視為單程）──
                {
                    "type": "text",
                    "text": "回程日期（不填視為單程）",
                    "size": "sm",
                    "color": "#888888"
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "datetimepicker",
                        "label": "選擇回程日期",
                        "data": "action=flight_ret_date",
                        "mode": "date",
                        "initial": today_iso,
                        "min": today_iso
                    }
                },

                # ── 旅客人數 ──
                {
                    "type": "text",
                    "text": "旅客（2歲以上）",
                    "size": "sm",
                    "color": "#888888"
                },
                _counter_row("flight_pax", "旅客"),

                # ── 嬰兒人數 ──
                {
                    "type": "text",
                    "text": "嬰兒（未滿2歲）",
                    "size": "sm",
                    "color": "#888888"
                },
                _counter_row("flight_infant", "嬰兒"),

                # ── 目的地（固定）──
                {"type": "separator"},
                {
                    "type": "box",
                    "layout": "horizontal",
                    "alignItems": "center",
                    "contents": [
                        {
                            "type": "text",
                            "text": "目的地",
                            "size": "sm",
                            "color": "#888888",
                            "flex": 2
                        },
                        {
                            "type": "text",
                            "text": "澎湖 🔒",
                            "size": "sm",
                            "weight": "bold",
                            "flex": 3
                        }
                    ]
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
                    "color": COLOR_PRIMARY,
                    "action": {
                        "type": "postback",
                        "label": "🔍 查詢航班",
                        "data": "action=flight_search",
                        "displayText": "查詢航班"
                    }
                }
            ]
        }
    }


# ── 元件輔助函式 ─────────────────────────────────────

def _postback_btn(label, data, display_text):
    """帶 displayText 的次要按鈕：點選後對話框顯示使用者側泡泡，bot 不回應"""
    return {
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "flex": 1,
        "action": {
            "type": "postback",
            "label": label,
            "data": data,
            "displayText": display_text
        }
    }


def _city_btn(code, name):
    """出發城市按鈕，displayText 顯示選擇結果"""
    return {
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "flex": 1,
        "action": {
            "type": "postback",
            "label": name,
            "data": f"action=flight_city&code={code}&name={name}",
            "displayText": f"出發城市：{name}"
        }
    }


def _counter_row(action_key, label):
    """
    +/- 計數器列，每個按鈕帶 displayText，點選後顯示加減動作：
        左側「－」── 中間說明文字 ── 右側「＋」
    """
    return {
        "type": "box",
        "layout": "horizontal",
        "alignItems": "center",
        "spacing": "sm",
        "contents": [
            {
                "type": "button",
                "style": "primary",
                "color": COLOR_PRIMARY,
                "height": "sm",
                "flex": 2,
                "action": {
                    "type": "postback",
                    "label": "－",
                    "data": f"action={action_key}_dec",
                    "displayText": f"{label}人數 －1"
                }
            },
            {
                "type": "text",
                "text": "點按調整",
                "align": "center",
                "size": "xs",
                "color": "#AAAAAA",
                "flex": 3
            },
            {
                "type": "button",
                "style": "primary",
                "color": COLOR_PRIMARY,
                "height": "sm",
                "flex": 2,
                "action": {
                    "type": "postback",
                    "label": "＋",
                    "data": f"action={action_key}_inc",
                    "displayText": f"{label}人數 ＋1"
                }
            }
        ]
    }
