"""
RAG 智慧行程服務

整合 Panghu_AI_Leader 的完整 AI pipeline：
    1. parameter_extractor   — 從對話提取人數與日期
    2. user_demand_analysis  — CoT 需求分析
    3. find_available_dates  — 查詢華信機票是否有位（可選）
    4. get_weather_info      — 取得 CWA 天氣預報（可選）
    5. chat_with_penghu_rag  — 行程 + 景點雙 FAISS 檢索
    6. travel_planner        — 生成行程
    7. critical_reviewer     — 審查
    8. travel_replanner      — 修正
    9. get_souvenir_recommendations — 伴手禮推薦（souvenir FAISS）

環境變數：
    MISTRAL_API_KEY     — 必要
    OPENDATA_CWA_API_KEY — 選用，無則跳過天氣檢查
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta, date
from dotenv import load_dotenv
from mistralai import Mistral
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()

# ── 路徑設定 ──────────────────────────────────────────────────
_LINEBOT_ROOT  = Path(__file__).parent.parent
_AI_LEADER_DIR = _LINEBOT_ROOT / "Panghu_AI_Leader"
_CRAWLER_DIR   = _AI_LEADER_DIR / "Penghu_web_crawler"

if str(_CRAWLER_DIR) not in sys.path:
    sys.path.insert(0, str(_CRAWLER_DIR))

# 選用模組：天氣 / 機票（無法匯入時靜默跳過）
try:
    from weather import get_weather_by_range, format_by_range
    _WEATHER_OK = True
except Exception:
    _WEATHER_OK = False

try:
    from mandarin_airline import check_availability
    _FLIGHT_OK = True
except Exception:
    _FLIGHT_OK = False

# ── Mistral 設定 ─────────────────────────────────────────────
api_key = os.getenv("MISTRAL_API_KEY")
if api_key is None:
    raise ValueError("MISTRAL_API_KEY environment variable is not set.")

model = "ministral-8b-latest"
_mistral_client = Mistral(api_key=api_key)

# ── Embedding 模型 ────────────────────────────────────────────
class EmbeddingGemmaEmbeddings(HuggingFaceEmbeddings):
    def __init__(self, **kwargs):
        super().__init__(
            model_name="google/embeddinggemma-300m",
            encode_kwargs={"normalize_embeddings": True},
            **kwargs
        )
    def embed_documents(self, texts):
        texts = [f'title: none | text: {t}' for t in texts]
        return super().embed_documents(texts)
    def embed_query(self, text):
        return super().embed_query(f'task: search result | query: {text}')


# ── FAISS 三庫（延遲載入，第一次使用智慧查詢時才初始化）──────
_embedding_model      = None
_vectorstore_schedule = None
_vectorstore_scenery  = None
_vectorstore_souvenir = None

def _get_vectorstores():
    global _embedding_model, _vectorstore_schedule, _vectorstore_scenery, _vectorstore_souvenir
    if _vectorstore_schedule is None:
        _embedding_model = EmbeddingGemmaEmbeddings()
        _vectorstore_schedule = FAISS.load_local(
            str(_AI_LEADER_DIR / "faiss_schedule_db"),
            embeddings=_embedding_model,
            allow_dangerous_deserialization=True
        )
        _vectorstore_scenery = FAISS.load_local(
            str(_AI_LEADER_DIR / "faiss_scenery_db"),
            embeddings=_embedding_model,
            allow_dangerous_deserialization=True
        )
        _vectorstore_souvenir = FAISS.load_local(
            str(_AI_LEADER_DIR / "faiss_souvenir_db"),
            embeddings=_embedding_model,
            allow_dangerous_deserialization=True
        )
    return _vectorstore_schedule, _vectorstore_scenery, _vectorstore_souvenir


# ── CoT Pipeline 函式 ─────────────────────────────────────────

def user_demand_analysis(prompt):
    system = """你是一位專業的旅遊行程顧問。請分析使用者的輸入，並將其需求分類為以下類別：
1. 核心活動（如：浮潛、釣小管）
2. 飲食偏好（如：仙人掌冰、海鮮）
3. 景點類型（如：歷史古蹟、自然景觀）
4. 旅行風格（如：悠閒、冒險、家庭友善）
5. 潛在需求（根據已知需求推測的合理配套）
請以條列式呈現，確保不遺漏任何使用者提到的細節，且不要自行過度想像。"""
    response = _mistral_client.chat.complete(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": prompt}]
    )
    return response.choices[0].message.content


def travel_planner(prompt):
    system = """你是一位精通澎湖地理與文化的在地導遊。請根據提供的需求、天氣與日期資訊，規劃一個深度且流暢的旅遊行程。

規劃原則：
1. 邏輯性：行程需考慮地理位置（北環、南環、東海、南海），避免在不同區域間來回奔波。
2. 在地化：使用在地地名，避免「套裝行程」、「業者名稱」、「定價/售價」等商業字眼。
3. 節奏感：合理安排休息與用餐時間，澎湖夏季炎熱，中午應安排室內或輕鬆活動。
4. 天氣適應性：根據天氣預報微調（下雨則加強室內景點）。
5. 時間排程限制：抵達當天與離開當天，絕對不可安排搭船前往離島或任何玩水活動。

輸出格式：
用純文字加表情符號呈現，不使用任何 markdown 語法（不用 ##、**、--- 等）。
行程每天條列簡短。最後加上 [NOTES] 標記，後面接注意事項與住宿建議。"""
    response = _mistral_client.chat.complete(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": prompt}]
    )
    return response.choices[0].message.content


def critical_reviewer(prompt):
    system = """你是一位極其挑剔的資深旅遊評論家，專門審查澎湖行程的合理性。
請針對提供的行程進行「壓力測試」，並列出至少三個具體的改進建議：

審查重點：
1. 物流可行性：交通時間是否預留不足？景點順序是否繞路？
2. 使用者滿足度：是否完整覆蓋了使用者的所有核心需求？
3. 商業感過濾：是否隱藏了商業宣傳術語或特定業者名稱？
4. 環境因素：是否考慮了潮汐（若涉及摩西分海或潮間帶）與天氣風險？

請條列式指出缺點並說明原因，口吻應嚴謹且專業。"""
    response = _mistral_client.chat.complete(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": prompt}]
    )
    return response.choices[0].message.content


def travel_replanner(prompt):
    system = """你是一位追求完美的首席旅遊設計師。你的任務是參考「評論家的意見」來修正「原有的行程規劃」。

執行指令：
1. 完整保留原有規劃中的優點。
2. 針對評論家指出的每一個問題進行針對性修復。
3. 確保最終輸出是一個完整的、可直接執行的行程方案。
4. 禁止在回覆中包含任何評論家或你的自我介紹，直接輸出最終行程。
5. 再次確認已移除所有商業字眼與不合理的物流安排。
用純文字加表情符號，不使用 markdown。行程結束後加上 [NOTES] 標記，後面接注意事項與住宿建議。"""
    response = _mistral_client.chat.complete(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": prompt}]
    )
    return response.choices[0].message.content


# ── 參數提取 ──────────────────────────────────────────────────

def parameter_extractor(prompt):
    """從使用者的 prompt 中提取總人數與日期區間"""
    system = f"""你是一個精準的參數提取助手。你的任務是從使用者的輸入中提取旅遊人數與日期。
現在日期是：{date.today().strftime("%Y-%m-%d")} (星期{["一","二","三","四","五","六","日"][date.today().weekday()]})

請遵循以下精確規則：
1. 人數提取 (total_people)：
   - 若使用者提到「我」，且沒有提到其他人，人數為 1。
   - 若提到「我們」，人數至少為 2（若無具體數字，預設為 2）。
   - 若提到「大/小」、「位」、「人」，請加總。
   - 若完全未提及任何暗示，預設為 2。
2. 日期提取：
   - 格式必須為 YYYY-MM-DD。
   - start_date 為出發日，end_date 為回程日。
   - 若使用者只提到一個日期，end_date 請設為 null。
   - 若完全未提到日期，start_date 與 end_date 皆設為 null。

請嚴格以 JSON 格式回傳，不要有任何額外文字：
{{
    "total_people": integer,
    "start_date": "YYYY-MM-DD" or null,
    "end_date": "YYYY-MM-DD" or null
}}"""
    try:
        response = ai.Client().chat.completions.create(
            model=f"{provider}:{model}",
            messages=[{"role": "system", "content": system},
                      {"role": "user",   "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()
        start = raw.find('{')
        end   = raw.rfind('}')
        data  = json.loads(raw[start:end+1])

        s_date = None
        if data.get("start_date"):
            try: s_date = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
            except: pass
        e_date = None
        if data.get("end_date"):
            try: e_date = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
            except: pass

        return data.get("total_people", 2), s_date, e_date
    except Exception:
        return 2, None, None


# ── 天氣與機票（選用）────────────────────────────────────────

def _get_next_weekend(start):
    days = (5 - start.weekday() + 7) % 7
    sat  = start + timedelta(days=days)
    return sat, sat + timedelta(days=1)


def _is_weather_bad(kind, data, check_date=None):
    if check_date and (check_date.month >= 10 or check_date.month <= 4):
        return True
    if kind == "helper":
        for p in data.get("預報", []):
            if any(w in p.get("內容", "") for w in ["雨", "雷", "強風", "浪大", "不穩定"]):
                return True
    elif kind in ["3day", "7day"]:
        for f in data:
            pop = str(f.get("降雨機率", "0")).replace("%", "")
            if pop.isdigit() and int(pop) > 50:
                return True
            wind = str(f.get("風速", "0"))
            if "級" in wind:
                try:
                    val = wind.split("至")[-1].replace("級", "").strip()
                    if val.isdigit() and int(val) >= 6:
                        return True
                except: pass
            if any(w in f.get("天氣", "") for w in ["雨", "雷"]):
                return True
    return False


def _find_available_dates(adults, start_date, end_date):
    """回傳 (dep_date, ret_date, flight_result_dict | None)"""
    if not _FLIGHT_OK:
        return start_date, end_date, None

    if start_date:
        dep_str = start_date.strftime("%Y/%m/%d")
        final_end = end_date if end_date else start_date + timedelta(days=1)
        ret_str = final_end.strftime("%Y/%m/%d")
        result = check_availability(dep_date=dep_str, ret_date=ret_str, adults=adults, silent=True)
        return start_date, final_end, result

    # 未指定日期 → 自動搜尋最近有位的週末
    target = date.today()
    for _ in range(8):
        sat, sun = _get_next_weekend(target)
        result = check_availability(
            dep_date=sat.strftime("%Y/%m/%d"),
            ret_date=sun.strftime("%Y/%m/%d"),
            adults=adults, silent=True
        )
        if result.get("success"):
            return sat, sun, result
        target = sat + timedelta(days=7)
    return None, None, None


def _get_weather_text(start_date, end_date):
    if not _WEATHER_OK or not start_date:
        return None, False
    try:
        kind, data = get_weather_by_range(start_date, end_date)
        is_bad = _is_weather_bad(kind, data, start_date)
        return format_by_range(kind, data, start_date, end_date), is_bad
    except Exception:
        return None, False


# ── 伴手禮推薦 ────────────────────────────────────────────────

def _get_souvenir_recommendations(user_demand, top_n=2):
    try:
        _, _, vectorstore_souvenir = _get_vectorstores()
        results = vectorstore_souvenir.similarity_search_with_relevance_scores(user_demand, k=top_n * 2)
        top_results = results[:top_n]
        if not top_results:
            return ""

        candidates_info = ""
        for doc, _ in top_results:
            m = doc.metadata
            candidates_info += f"""
店名：{m.get('store_name', '未知')}
標籤：{m.get('tag', '')}
地址：{m.get('address', '未知')}
營業時間：{m.get('hours', '未提供')}
導航連結：{m.get('nav_link', '未提供')}
介紹：{m.get('intro', '')}
---"""

        prompt = f"""你是一位經驗豐富的澎湖在地導遊，使用者即將結束澎湖旅程。
請從以下候選伴手禮店家中，挑選最值得推薦的 {top_n} 家，為使用者撰寫伴手禮推薦。

【使用者旅遊偏好】
{user_demand}

【候選店家資料】
{candidates_info}

【輸出規則】
1. 每家店格式：
店名 | 地址 | 營業時間 | 地圖：連結
導遊推薦：1～2 句推薦理由

2. 在所有店家推薦之後，加上一段溫馨提醒：建議在最後一天離開前再購買黑糖糕等保存期限較短的伴手禮。
3. 不要加入任何你自己編造的店家，只能從候選名單中挑選。
4. 語氣親切自然，像朋友在聊天。
5. 不使用任何 markdown 語法（不用 **、## 等）。"""

        response = ai.Client().chat.completions.create(
            model=f"{provider}:{model}",
            messages=[
                {"role": "system", "content": "你是一位熱愛澎湖的在地伴手禮達人。"},
                {"role": "user",   "content": prompt}
            ]
        )
        rec = response.choices[0].message.content
        return f"\n\n🎁 伴手禮推薦\n\n{rec}\n"
    except Exception as e:
        print(f"[RAG] 伴手禮推薦失敗：{e}")
        return ""


# ── RAG 行程檢索 ──────────────────────────────────────────────

def _chat_with_penghu_rag(user_input, threshold=0.25):
    vectorstore_schedule, vectorstore_scenery, _ = _get_vectorstores()
    results_schedule = vectorstore_schedule.similarity_search_with_relevance_scores(user_input, k=50)
    results_scenery  = vectorstore_scenery.similarity_search_with_relevance_scores(user_input, k=50)

    filtered_schedule = [doc for doc, s in results_schedule if s >= threshold]
    filtered_scenery  = [doc for doc, s in results_scenery  if s >= threshold]

    docs_schedule = filtered_schedule if filtered_schedule else [doc for doc, _ in results_schedule[:5]]
    docs_scenery  = filtered_scenery  if filtered_scenery  else [doc for doc, _ in results_scenery[:5]]

    retrieved_schedule = "\n\n".join([doc.page_content for doc in docs_schedule])
    retrieved_scenery  = "\n\n".join([doc.page_content for doc in docs_scenery])

    final_prompt = f"""你是一位在地的澎湖生活專家，請根據下列提供的資訊：

### 在地適合的套裝活動建議：
{retrieved_schedule}

### 相關景點詳細資訊：
{retrieved_scenery}

針對使用者的需求「{user_input}」，提供最適合的在地行程建議。"""

    response = _mistral_client.chat.complete(
        model=model,
        messages=[
            {"role": "system", "content": "你是一位熱愛澎湖的在地領路人。"},
            {"role": "user",   "content": final_prompt}
        ]
    )
    return response.choices[0].message.content


# ── 對外入口 ──────────────────────────────────────────────────

def rag_smart_reply(user_text: str) -> str:
    """
    完整 AI 行程規劃 pipeline：
        1. 提取人數 + 日期
        2. 需求分析
        3. 查機票（可選）
        4. 查天氣（可選）
        5. RAG 行程 + 景點檢索
        6. 生成 → 審查 → 修正行程
        7. 伴手禮推薦
    """
    # 1. 參數提取
    adults, start_date, end_date = parameter_extractor(user_text)

    # 2. 需求分析
    user_demand = user_demand_analysis(prompt=user_text)

    # 3. 查詢機票
    dep_date, ret_date, flight_result = _find_available_dates(adults, start_date, end_date)

    if _FLIGHT_OK and dep_date is None:
        return "抱歉，目前查詢不到近期有位的機票，建議先確認航班後再規劃行程。"

    if _FLIGHT_OK and flight_result and isinstance(flight_result, dict) and "error" in flight_result:
        return f"機票查詢提醒：{flight_result['error']}"

    # 4. 查詢天氣
    info_header = ""
    weather_text, is_bad = _get_weather_text(dep_date, ret_date)

    if is_bad and _WEATHER_OK:
        info_header = "⚠️ 天氣提醒：預定期間天氣可能不佳，以下行程已調整為以本島陸上景點為主。\n\n"

    if dep_date and ret_date and _FLIGHT_OK and flight_result and flight_result.get("success"):
        info_header += (
            f"✈️ 機票資訊\n"
            f"旅遊日期：{dep_date.strftime('%Y/%m/%d')} ～ {ret_date.strftime('%Y/%m/%d')}\n"
            f"台北(TSA) ↔ 澎湖(MZG) {adults} 人來回皆有位\n\n"
        )
        if weather_text:
            info_header += f"{weather_text}\n\n"

    # 5. RAG 行程 + 景點
    rag_result = _chat_with_penghu_rag(user_input="以下是我的需求：" + user_demand)

    # 6. 生成 → 審查 → 修正
    date_info = f"已確認旅遊日期為 {dep_date} 至 {ret_date}。\n" if dep_date else ""
    weather_info = f"天氣預報資訊如下：\n{weather_text}\n\n" if weather_text else ""

    planner_prompt = (
        f"使用者需求：{user_demand}\n\n"
        f"{date_info}"
        f"{weather_info}"
        f"在地好友也給了一些活動建議，請將這些活動自然地規劃進行程中：\n{rag_result}"
    )

    planner  = travel_planner(prompt=planner_prompt)
    reviewer = critical_reviewer(prompt=planner)
    final    = travel_replanner(prompt=reviewer)

    # 移除 LLM 可能生成的 markdown code block 標籤
    final = final.replace("```markdown\n", "").replace("```markdown", "").replace("```", "").strip()

    # 7. 伴手禮推薦
    souvenir_section = _get_souvenir_recommendations(user_demand, top_n=2)

    return info_header + final + souvenir_section
