"""
飛機航班查詢 LIFF 入口按鈕 Flex Message

點選按鈕後在 LINE 內開啟 LIFF 網頁，使用者可即時互動（顏色高亮、數字更新）。
填完送出後 LIFF 自動關閉，bot 在背景執行查詢並推送結果。
"""


def get_flight_liff_btn(liff_url: str) -> dict:
    """
    回傳含 LIFF 入口按鈕的 bubble dict。

    參數：
        liff_url: LIFF 完整網址，格式 https://liff.line.me/{LIFF_ID}
    """
    return {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "🛫 飛機航班查詢",
                    "weight": "bold",
                    "size": "xl"
                },
                {
                    "type": "text",
                    "text": "請點選下方按鈕開啟查詢表單，\n選擇出發城市、日期及人數後送出，\n結果將自動推送至此對話。",
                    "size": "sm",
                    "color": "#888888",
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
                    "action": {
                        "type": "uri",
                        "label": "開啟查詢表單",
                        "uri": liff_url
                    }
                }
            ]
        }
    }
