"""
美食主題清單 Flex Carousel（可左右滑）

每張卡片代表一種澎湖美食主題，點選「了解更多」顯示相關資訊。
"""

THEMES = [
    {
        "color":    "#E05C5C",
        "emoji":    "🦞",
        "title":    "現撈海鮮",
        "desc":     "龍蝦、石斑、九孔，\n澎湖海鮮直送餐桌，新鮮美味無與倫比。",
        "keyword":  "澎湖海鮮"
    },
    {
        "color":    "#E08840",
        "emoji":    "🥟",
        "title":    "道地小吃",
        "desc":     "鹹餅、花生酥、仙人掌冰，\n漫步馬公老街品嚐在地風味。",
        "keyword":  "澎湖小吃"
    },
    {
        "color":    "#4EADAC",
        "emoji":    "🛍️",
        "title":    "名產伴手禮",
        "desc":     "丁香魚、仙人掌果醬、黑糖糕，\n帶回滿滿澎湖風味與溫情。",
        "keyword":  "澎湖名產"
    },
    {
        "color":    "#7B68EE",
        "emoji":    "🍽️",
        "title":    "人氣餐廳",
        "desc":     "從海景餐廳到在地老店，\n精選評價最佳的用餐選擇。",
        "keyword":  "澎湖餐廳"
    },
    {
        "color":    "#3aab6a",
        "emoji":    "🌵",
        "title":    "仙人掌美食",
        "desc":     "澎湖獨有仙人掌果，\n製成冰品、果醬、飲料，酸甜消暑。",
        "keyword":  "仙人掌美食"
    },
]


def get_theme_food_carousel() -> dict:
    """回傳美食主題 carousel dict"""
    return {
        "type": "carousel",
        "contents": [_bubble(t) for t in THEMES]
    }


def _bubble(theme: dict) -> dict:
    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": theme["color"],
            "paddingAll": "18px",
            "contents": [
                {
                    "type": "text",
                    "text": theme["emoji"],
                    "size": "3xl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": theme["title"],
                    "weight": "bold",
                    "size": "md",
                    "color": "#FFFFFF",
                    "align": "center",
                    "margin": "sm"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "14px",
            "contents": [
                {
                    "type": "text",
                    "text": theme["desc"],
                    "size": "sm",
                    "color": "#555555",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "10px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": theme["color"],
                    "height": "sm",
                    "action": {
                        "type": "message",
                        "label": "了解更多",
                        "text": theme["keyword"]
                    }
                }
            ]
        }
    }
