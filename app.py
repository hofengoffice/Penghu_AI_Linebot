"""
澎湖旅遊 AI LINE Bot 主程式

職責：
    - 接收 LINE Webhook 事件
    - 將訊息分派給對應的 handler 處理
"""

import os
import threading
from flask import Flask, request, abort, jsonify, render_template
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, PushMessageRequest,
    TextMessage as TextMsg,
    FlexMessage, FlexContainer,
    QuickReply, QuickReplyItem, PostbackAction
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent, PostbackEvent, FollowEvent
from dotenv import load_dotenv
import handlers.smart_query as smart_query_handler
import handlers.transport_query as transport_query_handler
import handlers.popular_trip as popular_trip_handler
import handlers.favorites as favorites_handler
import handlers.room_query as room_query_handler
import handlers.theme_browse as theme_browse_handler

load_dotenv()

app = Flask(__name__)
configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# 記錄每位使用者目前的對話步驟
# 格式：{ user_id: {"step": "smart_query_input"} }
user_states = {}


def reply(reply_token, text):
    """即時回覆使用者（reply token 有時效，只能用一次）"""
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMsg(type="text", text=text)]
            )
        )

def push(user_id, text):
    """主動推送訊息給使用者（無時效限制，適合背景作業完成後使用）"""
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMsg(type="text", text=text)]
            )
        )

def push_flex(user_id, flex_dict, alt_text="訊息"):
    """主動推送 Flex Message（無時效限制，適合背景作業完成後使用）"""
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).push_message(
            PushMessageRequest(
                to=user_id,
                messages=[
                    FlexMessage(
                        alt_text=alt_text,
                        contents=FlexContainer.from_dict(flex_dict)
                    )
                ]
            )
        )

def reply_flex(reply_token, flex_dict, alt_text="選單"):
    """即時回覆 Flex Message（bubble 或 carousel）"""
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    FlexMessage(
                        alt_text=alt_text,
                        contents=FlexContainer.from_dict(flex_dict)
                    )
                ]
            )
        )

def reply_quick_reply(reply_token, text, options):
    """回覆帶有 Quick Reply 按鈕的文字訊息。
    options: [(label, postback_data), ...]
    """
    with ApiClient(configuration) as api_client:
        MessagingApi(api_client).reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[
                    TextMsg(
                        type="text",
                        text=text,
                        quick_reply=QuickReply(items=[
                            QuickReplyItem(
                                action=PostbackAction(
                                    label=label,
                                    data=data,
                                    display_text=label
                                )
                            )
                            for label, data in options
                        ])
                    )
                ]
            )
        )


def handle_message(user_id, text, reply_token):
    """
    訊息分派中心。
    依序呼叫各 handler，由 handler 回傳 True/False 決定是否繼續往下判斷。
    """
    text = text.strip()

    # ── 真人客服模式 ──────────────────────────────────────
    if text == "真人":
        user_states[user_id] = {"step": "human_mode"}
        reply(reply_token, "已為您轉接真人客服 👨‍💼\n工作人員將盡快回覆您，感謝您的耐心等候。\n\n如需返回 AI 助理，請輸入「結束客服」")
        return

    if user_states.get(user_id, {}).get("step") == "human_mode":
        if text == "結束客服":
            user_states.pop(user_id, None)
            reply(reply_token, "已返回 AI 助理模式 🤖\n有任何問題歡迎繼續詢問！")
        # 真人模式中，其他訊息由後台客服人員回覆，Bot 不介入
        return

    # ── 說明 ──────────────────────────────────────────────
    if text in ("說明", "help", "Help", "HELP", "?", "？"):
        reply(reply_token,
              "📖 澎湖旅遊 AI 助理功能說明\n"
              "─────────────────\n"
              "🗺️ 行程主題　　→ 輸入「行程主題」\n"
              "🍽️ 美食主題　　→ 輸入「美食主題」\n"
              "🚌 交通主題　　→ 輸入「交通主題」\n"
              "✈️ 航班查詢　　→ 輸入「航班查詢」\n"
              "🏨 空房查詢　　→ 輸入「空房查詢」\n"
              "🤖 智慧行程規劃→ 輸入「亮亮排行程」\n"
              "❤️ 收藏清單　　→ 輸入「收藏清單」\n"
              "─────────────────\n"
              "👨‍💼 真人客服\n"
              "輸入「真人」　　→ 轉接真人客服\n"
              "輸入「結束客服」→ 返回 AI 助理\n"
              "─────────────────\n"
              "輸入「說明」可隨時查看此清單"
        )
        return

    # ── 主題清單（行程/美食/交通主題）────────────────────────
    if theme_browse_handler.handle(user_id, text, reply_token, user_states, reply, push, reply_flex):
        return

    # ── 熱門行程 ──────────────────────────────────────────
    if popular_trip_handler.handle(user_id, text, reply_token, user_states, reply, push, reply_flex):
        return

    # ── 收藏清單 ──────────────────────────────────────────
    if favorites_handler.handle(user_id, text, reply_token, user_states, reply, push, reply_flex):
        return

    # ── 空房查詢 ──────────────────────────────────────────
    if room_query_handler.handle(user_id, text, reply_token, user_states, reply, push, reply_flex, reply_quick_reply):
        return

    # ── 交通查詢 ──────────────────────────────────────────
    if transport_query_handler.handle(user_id, text, reply_token, user_states, reply, push, reply_flex):
        return

    # ── 智慧查詢 ──────────────────────────────────────────
    if smart_query_handler.handle(user_id, text, reply_token, user_states, reply, push, push_flex):
        return


@app.route("/callback", methods=["POST"])
def callback():
    """LINE Webhook 入口，驗證簽名後交給 handler 處理"""
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(FollowEvent)
def handle_follow(event):
    """用戶第一次加入官方帳號時，推送歡迎訊息"""
    user_id = event.source.user_id
    push(user_id,
         "🌊 歡迎來到澎湖旅遊 AI 助理！\n\n"
         "我可以幫你：\n"
         "✈️ 查詢航班　　→ 輸入「航班查詢」\n"
         "🤖 規劃行程　　→ 輸入「亮亮排行程」\n"
         "🏨 預定住宿　　→ 輸入「空房查詢」\n"
         "🗺️ 瀏覽主題　　→ 輸入「行程主題」\n"
         "❤️ 查看收藏　　→ 輸入「收藏清單」\n\n"
         "👨‍💼 需要真人服務？輸入「真人」即可轉接\n"
         "📖 想查看全部功能？輸入「說明」"
    )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_text(event):
    """接收文字訊息事件，取出 user_id、文字、reply_token 後傳入分派中心"""
    print(f"[Messaging API] user_id={event.source.user_id!r}")
    handle_message(event.source.user_id, event.message.text, event.reply_token)


@handler.add(PostbackEvent)
def handle_postback(event):
    """
    接收所有 postback 事件，依 action 前綴分派：
        flight_* → transport_query_handler（飛機表單互動）
        其他     → favorites_handler（收藏、刪除、詳情）
    """
    user_id     = event.source.user_id
    data        = event.postback.data
    reply_token = event.reply_token

    # datetimepicker 的日期回傳在 postback.params，其他 postback 為 None
    date_param = None
    if hasattr(event.postback, "params") and event.postback.params:
        date_param = event.postback.params.get("date")

    # 交通查詢 postback（飛機表單 + 其他交通加入清單）
    if transport_query_handler.handle_postback(
        user_id, data, date_param, reply_token, user_states,
        reply, push, reply_flex, reply_quick_reply
    ):
        return

    # 空房預定 postback
    if room_query_handler.handle_postback(
        user_id, data, date_param, reply_token, user_states,
        reply, reply_quick_reply, reply_flex
    ):
        return

    # 收藏相關 postback
    favorites_handler.handle_postback(user_id, data, reply_token, reply, reply_flex)


@app.route("/liff/flight")
def liff_flight():
    """提供 LIFF 飛機查詢頁面，將 URL 中的 token 注入模板"""
    from flask import make_response
    liff_id  = os.getenv("LIFF_ID", "")
    token    = request.args.get("token", "")
    resp = make_response(render_template("liff_flight.html", liff_id=liff_id, token=token))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"]        = "no-cache"
    resp.headers["Expires"]       = "0"
    return resp


@app.route("/api/flight-search", methods=["POST"])
def api_flight_search():
    """
    接收 LIFF 送出的查詢表單，在背景執行爬蟲後 push 結果給使用者。
    以 token 換回 user_id，不依賴 LIFF 的 userId。
    """
    from services.airline_service import search_flights, format_result
    from utils.liff_token import resolve as resolve_liff_token

    data    = request.get_json(force=True)
    token   = data.get("token", "")
    user_id = resolve_liff_token(token) if token else None
    departure    = data.get("departure")
    dep_name     = data.get("dep_name", "")
    destination  = data.get("destination", "MZG")
    dest_name    = data.get("dest_name", "澎湖")
    date_str     = data.get("date")
    ret_dep      = data.get("ret_dep", "")
    ret_dep_name = data.get("ret_dep_name", "")
    ret_arr      = data.get("ret_arr", "")
    ret_arr_name = data.get("ret_arr_name", "")
    ret_date     = data.get("ret_date", "")
    passengers   = int(data.get("passengers", 1))
    infants      = int(data.get("infants", 0))

    if not user_id:
        return jsonify({"error": "連結已過期，請關閉後重新點選飛機航班"}), 400
    if not departure or not destination or not date_str:
        return jsonify({"error": "缺少必要參數"}), 400

    print(f"[LIFF] user_id={user_id!r}  {departure}→{destination}  date={date_str}")

    def _search():
        from flex.flight_result import get_flight_result_flex
        try:
            # 去程
            flights_out = search_flights(departure, destination, date_str, passengers, infants)

            # 來回
            flights_ret = None
            if ret_date and ret_dep and ret_arr:
                flights_ret = search_flights(ret_dep, ret_arr, ret_date, passengers, infants)

            flex_dict = get_flight_result_flex(
                flights_out, dep_name, dest_name, date_str,
                flights_ret, ret_date or None
            )

            alt = f"✈️ {dep_name}→{dest_name} {date_str} 航班查詢結果"
            push_flex(user_id, flex_dict, alt)

            if infants:
                push(user_id, f"提醒：嬰兒 {infants} 名請至各航空官網另行加購嬰兒票")

        except Exception as e:
            push(user_id, f"⚠️ 查詢失敗，請稍後再試。\n（{e}）")

    threading.Thread(target=_search, daemon=True).start()
    return jsonify({"status": "queued"})


if __name__ == "__main__":
     app.run(port=5000, debug=True, use_reloader=False)
