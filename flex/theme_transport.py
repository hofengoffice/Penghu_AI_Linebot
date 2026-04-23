"""
交通主題清單 Flex Carousel（可左右滑）

每張卡片代表一種交通方式，點選按鈕觸發對應功能。
"""

THEMES = [
    {
        "color":    "#4EADAC",
        "emoji":    "✈️",
        "title":    "飛機航班",
        "desc":     "查詢台北、台中、嘉義、高雄\n往返澎湖的最新班次與票價。",
        "keyword":  "飛機航班"
    },
    {
        "color":    "#3a7abf",
        "emoji":    "⛴️",
        "title":    "船班資訊",
        "desc":     "台華輪、台馬輪定期航班，\n適合攜帶大件行李或寵物旅遊。",
        "keyword":  "船班資訊"
    },
    {
        "color":    "#E08840",
        "emoji":    "🚗",
        "title":    "租車服務",
        "desc":     "自駕暢遊澎湖各島，\n馬公市區及機場均有租車點。",
        "keyword":  "租車服務"
    },
    {
        "color":    "#E05C5C",
        "emoji":    "🛵",
        "title":    "機車租借",
        "desc":     "澎湖最靈活的島內交通，\n輕鬆穿梭各景點，感受海風。",
        "keyword":  "機車租借"
    },
    {
        "color":    "#3aab6a",
        "emoji":    "🚲",
        "title":    "自行車漫遊",
        "desc":     "沿著海岸線慢騎，\n觀音亭、馬公老街悠然慢遊。",
        "keyword":  "自行車漫遊"
    },
]


def get_theme_transport_carousel() -> dict:
    """回傳交通主題 carousel dict"""
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
                        "label": "前往查詢",
                        "text": theme["keyword"]
                    }
                }
            ]
        }
    }
