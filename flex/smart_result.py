"""
智慧查詢結果 Flex Message 模板

顯示 AI 規劃的行程文字，footer 附收藏按鈕。
"""


def get_smart_result_bubble(result_text, user_id):
    """
    參數：
        result_text : RAG 生成的行程文字
        user_id     : LINE user_id（用於 postback 識別要收藏哪位用戶的最新結果）
    """
    return {
        "type": "bubble",
        "size": "giga",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "🤖 AI 行程規劃",
                    "weight": "bold",
                    "size": "lg"
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": result_text,
                    "wrap": True,
                    "size": "sm",
                    "margin": "md",
                    "color": "#333333"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#4EADAC",
                    "action": {
                        "type": "postback",
                        "label": "⭐ 收藏此行程",
                        "data": f"action=favorite_itinerary&user_id={user_id}",
                        "displayText": "已收藏 AI 行程"
                    }
                }
            ]
        }
    }
