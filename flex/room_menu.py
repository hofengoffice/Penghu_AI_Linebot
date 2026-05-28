"""
空房查詢主選單 Flex Message 模板
"""


def get_room_menu():
    """回傳空房查詢選單 bubble dict"""
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "20px",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "歡迎使用空房查詢功能",
                    "weight": "bold",
                    "size": "lg",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": "你可以快速查看 🔎 👇",
                    "size": "sm",
                    "color": "#666666",
                    "wrap": True
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "margin": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📅 查詢入住日期 → 看有沒有空房",
                            "size": "sm",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "💰 價格與優惠 → 找最划算方案",
                            "size": "sm",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "📷 房間照片 → 先看再決定方案",
                            "size": "sm",
                            "wrap": True
                        },
                        {
                            "type": "text",
                            "text": "📋 房間預定 → 填入日期、人數、備註",
                            "size": "sm",
                            "wrap": True
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": "👉 直接點選下方功能開始查詢！",
                    "size": "sm",
                    "color": "#4EADAC",
                    "weight": "bold",
                    "margin": "md",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#4EADAC",
                    "action": {
                        "type": "message",
                        "label": "📅 立即查詢住宿日期",
                        "text": "立即查詢住宿日期"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "💰 價格與優惠",
                        "text": "價格與優惠"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "📷 房間照片",
                        "text": "房間照片"
                    }
                },
                {
                    "type": "button",
                    "style": "secondary",
                    "action": {
                        "type": "message",
                        "label": "📋 房間預定",
                        "text": "房間預定"
                    }
                }
            ]
        }
    }
