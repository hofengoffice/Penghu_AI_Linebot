"""
航班查詢結果 Flex Carousel

每張卡片代表一個班次，包含：
    - 方向標籤（去程 / 回程）+ 航空公司
    - 班次號碼
    - 出發 → 抵達時間
    - 路線 + 日期
    - 狀態
    - ⭐ 收藏按鈕

所有班次依出發時間排序，去程與回程在同一個 carousel 中呈現。
"""

COLOR_MANDARIN = "#2B6CB0"   # 華信航空（藍）
COLOR_UNIAIR   = "#2E8B3A"   # 立榮航空（綠）
COLOR_OK       = "#00AA44"   # 有位
COLOR_FULL     = "#CC3333"   # 售完


def get_flight_result_flex(outbound_flights, dep_name, arr_name, date_str,
                            return_flights=None, ret_date=None):
    """
    回傳航班查詢結果 carousel dict。

    參數：
        outbound_flights : 去程航班 list（search_flights 回傳格式）
        dep_name         : 出發城市中文名稱
        arr_name         : 到達城市中文名稱（通常為「澎湖」）
        date_str         : 去程日期（YYYY/MM/DD）
        return_flights   : 回程航班 list（可選）
        ret_date         : 回程日期（可選）
    """
    bubbles = []

    # ── 去程 ──
    for f in _sort_by_time(outbound_flights):
        bubbles.append(_bubble(f, dep_name, arr_name, date_str, "去程"))

    # ── 回程 ──
    if return_flights and ret_date:
        for f in _sort_by_time(return_flights):
            bubbles.append(_bubble(f, arr_name, dep_name, ret_date, "回程"))

    if not bubbles:
        return _empty_bubble(dep_name, arr_name, date_str)

    return {
        "type": "carousel",
        "contents": bubbles[:12]   # LINE carousel 上限 12 張
    }


# ── 內部工具函式 ──────────────────────────────────────────────

def _sort_by_time(flights: list) -> list:
    """依起飛時間（HH:MM）升冪排序"""
    return sorted(flights, key=lambda f: (f.get("起飛", "") or "")[:5])


def _bubble(flight: dict, dep_name: str, arr_name: str,
            date_str: str, direction: str) -> dict:
    airline   = flight.get("航空公司", "")
    flight_no = flight.get("航班", "")
    header_color = COLOR_UNIAIR if "立榮" in airline else COLOR_MANDARIN
    dep_time  = (flight.get("起飛", "") or "")[:5]
    arr_time  = (flight.get("抵達", "") or "")[:5]
    status    = flight.get("狀態", "")

    is_ok        = "有位" in status
    status_color = COLOR_OK if is_ok else COLOR_FULL

    # postback data — 控制在 300 bytes 以內
    save_id   = f"flt_{flight_no}_{date_str.replace('/', '')}_{dep_name}{arr_name}"
    save_name = f"{flight_no} {dep_name}→{arr_name} {dep_time} ({date_str})"
    pb_data   = f"action=flight_favorite&id={save_id}&name={save_name}&airline={airline}"

    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "horizontal",
            "backgroundColor": header_color,
            "paddingAll": "10px",
            "contents": [
                {"type": "text", "text": direction, "color": "#FFFFFF",
                 "size": "xs", "weight": "bold", "flex": 1},
                {"type": "text", "text": airline,   "color": "#FFFFFF",
                 "size": "xs", "align": "end",      "flex": 2}
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "14px",
            "contents": [
                # 班次號
                {
                    "type": "text",
                    "text": flight_no,
                    "weight": "bold",
                    "size": "lg",
                    "align": "center"
                },
                # 時間
                {
                    "type": "box",
                    "layout": "horizontal",
                    "alignItems": "center",
                    "margin": "sm",
                    "contents": [
                        {"type": "text", "text": dep_time, "weight": "bold",
                         "size": "xl", "flex": 2, "align": "center"},
                        {"type": "text", "text": "→",
                         "color": "#AAAAAA", "flex": 1, "align": "center"},
                        {"type": "text", "text": arr_time, "weight": "bold",
                         "size": "xl", "flex": 2, "align": "center"}
                    ]
                },
                # 路線
                {
                    "type": "text",
                    "text": f"{dep_name} → {arr_name}",
                    "size": "xs", "color": "#888888", "align": "center"
                },
                # 日期
                {
                    "type": "text",
                    "text": date_str,
                    "size": "xs", "color": "#888888", "align": "center"
                },
                # 狀態
                {
                    "type": "text",
                    "text": status,
                    "size": "sm",
                    "color": status_color,
                    "weight": "bold",
                    "align": "center",
                    "margin": "sm"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "8px",
            "contents": [
                {
                    "type": "button",
                    "style": "secondary",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "⭐ 收藏",
                        "data": pb_data,
                        "displayText": f"收藏 {flight_no}"
                    }
                }
            ]
        }
    }


def _empty_bubble(dep_name: str, arr_name: str, date_str: str) -> dict:
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "24px",
            "contents": [
                {"type": "text", "text": "查無可購票航班",
                 "weight": "bold", "size": "lg", "align": "center"},
                {"type": "text",
                 "text": f"{dep_name} → {arr_name}\n{date_str}",
                 "size": "sm", "color": "#888888", "align": "center",
                 "wrap": True, "margin": "md"}
            ]
        }
    }
