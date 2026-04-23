"""
行程主題清單 Flex Carousel（可左右滑）

每張卡片代表一種旅遊主題，點選「查看行程」觸發對應行程類型查詢。
"""

THEMES = [
    {
        "color":    "#4EADAC",
        "emoji":    "👨‍👩‍👧‍👦",
        "title":    "親子同遊",
        "desc":     "適合全家大小的輕鬆行程，\n包含老少咸宜的景點與活動。",
        "keyword":  "親子行程"
    },
    {
        "color":    "#E08840",
        "emoji":    "💑",
        "title":    "蜜月甜蜜遊",
        "desc":     "浪漫海島風情，夕陽、星空、\n私房景點，打造專屬二人世界。",
        "keyword":  "蜜月行程"
    },
    {
        "color":    "#7B68EE",
        "emoji":    "🏛️",
        "title":    "深度文化探索",
        "desc":     "走訪歷史聚落、廟宇與傳統漁村，\n認識澎湖豐富的人文底蘊。",
        "keyword":  "文化行程"
    },
    {
        "color":    "#3aab6a",
        "emoji":    "🌊",
        "title":    "海島休閒假期",
        "desc":     "浮潛、獨木舟、沙灘漫步，\n盡情享受澎湖純淨海洋。",
        "keyword":  "海島行程"
    },
    {
        "color":    "#CC5555",
        "emoji":    "🎒",
        "title":    "背包客輕旅行",
        "desc":     "彈性自由行，探索在地小路，\n用最低預算玩遍澎湖。",
        "keyword":  "背包客行程"
    },
]


def get_theme_trip_carousel() -> dict:
    """回傳行程主題 carousel dict"""
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
                        "label": "查看行程",
                        "text": theme["keyword"]
                    }
                }
            ]
        }
    }
