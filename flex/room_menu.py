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
                    "text": "點選下方按鈕開始預定房間 👇",
                    "size": "sm",
                    "color": "#666666",
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
                        "label": "📋 房間預定",
                        "text": "房間預定"
                    }
                }
            ]
        }
    }
