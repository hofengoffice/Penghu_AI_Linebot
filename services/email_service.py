"""
Email 通知服務

功能：
    - send_inquiry_email(user_id, favorites)
        當客人確認心願清單後，寄送詢價通知給負責人。

設定（.env）：
    SMTP_HOST     SMTP 伺服器，預設 smtp.gmail.com
    SMTP_PORT     SMTP 埠號，預設 587（STARTTLS）
    SMTP_USER     寄件人帳號（Gmail 即 xxx@gmail.com）
    SMTP_PASS     寄件人密碼（Gmail 請用「應用程式密碼」）
    NOTIFY_EMAIL  負責人收件信箱
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

ITINERARIES_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "itineraries")

# 分類名稱對照
_CAT_LABEL = {
    "trip":          "🗺️ 熱門行程",
    "itinerary":     "🗺️ AI 規劃行程",
    "transport":     "✈️ 交通",
    "accommodation": "🏨 住宿",
}


def _load_itinerary(item_id: str) -> str:
    """讀取 AI 行程文字內容，找不到回傳空字串"""
    path = os.path.join(ITINERARIES_DIR, f"{item_id}.txt")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def _build_email_body(order_no: str, favorites: list) -> str:
    """產生純文字 email 內容"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "【澎湖旅遊 LINE Bot】心願清單詢價通知",
        "=" * 40,
        f"收到時間：{now}",
        f"訂單編號：{order_no}",
        "",
        "── 心願清單內容 ──",
    ]

    if not favorites:
        lines.append("（清單為空）")
    else:
        # 依分類整理
        from_types = {}
        for item in favorites:
            t = item.get("type", "other")
            from_types.setdefault(t, []).append(item)

        for t, items in from_types.items():
            label = _CAT_LABEL.get(t, t)
            lines.append(f"\n{label}")
            for item in items:
                name = item.get("name", "（未命名）")
                lines.append(f"  • {name}")

                # 住宿：附上入住/退房/備註
                if t == "accommodation":
                    if item.get("checkin"):
                        lines.append(f"    入住：{item['checkin']}  退房：{item.get('checkout', '—')}")
                    if item.get("pax"):
                        lines.append(f"    人數：{item['pax']} 人")
                    if item.get("note") and item["note"] != "無備註":
                        lines.append(f"    備註：{item['note']}")

                # AI 行程：附上完整行程內容
                if t == "itinerary":
                    content = _load_itinerary(item.get("id", ""))
                    if content:
                        lines.append("")
                        lines.append("    ┌── AI 行程內容 ──────────────")
                        for row in content.splitlines():
                            lines.append(f"    │ {row}")
                        lines.append("    └─────────────────────────────")

    lines += [
        "",
        "=" * 40,
        "請儘速回覆客人，謝謝！",
        "（此信由系統自動發送，請勿直接回覆）",
    ]
    return "\n".join(lines)


def generate_order_no() -> str:
    """產生訂單編號，格式：PH-YYYYMMDD-HHMMSS"""
    return datetime.now().strftime("PH-%Y%m%d-%H%M%S")


def send_inquiry_email(order_no: str, favorites: list) -> None:
    """
    寄送詢價通知 email 給負責人。

    raises:
        ValueError  若 SMTP 設定不完整
        Exception   若 SMTP 連線或傳送失敗
    """
    smtp_host    = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port    = int(os.getenv("SMTP_PORT", "587"))
    smtp_user    = os.getenv("SMTP_USER", "").strip()
    smtp_pass    = os.getenv("SMTP_PASS", "").strip()
    notify_email = os.getenv("NOTIFY_EMAIL", "").strip()

    if not smtp_user or not smtp_pass or not notify_email:
        raise ValueError("SMTP 設定不完整，請在 .env 填寫 SMTP_USER / SMTP_PASS / NOTIFY_EMAIL")

    body = _build_email_body(order_no, favorites)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"【澎湖旅遊】心願清單詢價 {order_no}"
    msg["From"]    = smtp_user
    msg["To"]      = notify_email
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, notify_email, msg.as_string())
