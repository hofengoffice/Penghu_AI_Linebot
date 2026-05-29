# 澎湖旅遊 AI LINE Bot

澎湖在地旅遊助手，提供行程規劃、智慧查詢、航班查詢、主題瀏覽、心願清單詢價等旅遊服務。

---

## 系統功能

| 功能 | 說明 |
|------|------|
| 熱門行程 | 行程類型輪播卡片，點入可瀏覽詳細行程並收藏 |
| 行程主題 | 五種旅遊主題 carousel（親子 / 蜜月 / 文化 / 海島 / 背包客） |
| 美食主題 | 五種美食主題 carousel（海鮮 / 小吃 / 名產 / 餐廳 / 仙人掌） |
| 交通主題 | 五種交通主題 carousel（飛機 / 船班 / 租車 / 機車 / 自行車） |
| 智慧查詢 | 輸入需求，AI 結合 RAG 生成客製化澎湖行程建議，可收藏 |
| 收藏清單 | 顯示個人收藏（行程 / 交通 / 住宿），支援詳情、刪除、**確認詢價** |
| 空房查詢 | 查詢澎湖飯店空房資訊 |
| 飛機航班 | 透過 LIFF 網頁填寫出發城市、日期、旅客人數，查詢華信與立榮航班 |

---

## 技術架構

### 系統架構圖

```
LINE User
    │
    ▼
LINE Platform
    │  Webhook (HTTPS POST / Postback)
    │  LIFF (LINE Front-end Framework)
    ▼
┌─────────────────────────────────────────────────┐
│  app.py  ─  Flask Webhook 入口                  │
│  user_states{}  ─  對話狀態機                   │
│  /liff/flight    ─  LIFF 航班表單頁面            │
│  /api/flight-search  ─  LIFF 查詢 API           │
└────────────────┬────────────────────────────────┘
                 │ 依 text / postback 分派
        ┌────────┴────────┐
        ▼                 ▼
  handlers/           flex/
  對話流程控制器       LINE Flex Message 模板
        │
        ▼
  services/
  資料服務層
  ┌─────────────────────────────────┐
  │ airline_service  → 華信 + 立榮  │
  │ email_service    → SMTP 寄信    │
  │ weather_service  → 氣象署 API   │
  │ tide_service     → 澎管處爬蟲   │
  │ rag_service      → RAG 引擎     │
  └─────────────────────────────────┘
        │
        ▼
  rag/faiss_db/        data/
  FAISS 向量資料庫      靜態 JSON 資料
```

### 飛機航班查詢流程（LIFF）

```
使用者傳「飛機航班」
    │
    ▼
transport_query_handler
    │  create_liff_token(user_id) → 產生 session token（30 分鐘有效）
    ▼
回傳 LIFF 入口按鈕（URI action）
    │  使用者點開
    ▼
LIFF 網頁 /liff/flight?token=xxx
    │  填寫出發城市、日期、回程日期（可選）、旅客人數、嬰兒人數
    │  點「查詢航班」
    ▼
POST /api/flight-search  （帶 token）
    │  resolve_liff_token(token) → 取得 user_id
    │  背景 Thread 執行爬蟲
    ▼
airline_service.search_flights()
    │  ThreadPoolExecutor 同時查詢華信 + 立榮
    ▼
flex/flight_result.py → 航班結果 carousel
    │  push_flex(user_id, ...)
    ▼
使用者收到 Flex carousel，每張卡片含「⭐ 收藏」按鈕
```

### 熱門行程 × 收藏 × 詢價流程

```
熱門行程 → 行程詳細 carousel → 點「⭐ 收藏行程」
                                    │
                                    ▼
                           storage/favorites/{user_id}.json

收藏清單（輸入「收藏清單」）
    │
    ▼
bubble 分類顯示（🗺️ 行程 / ✈️ 交通 / 🏨 住宿）
    │  每筆：詳情按鈕 + 刪除按鈕
    │  底部：「📩 確認詢價，通知負責人」按鈕
    ▼
點「確認詢價」（postback: confirm_inquiry）
    │  reply → 告知使用者已收到
    │  背景 Thread 執行寄信
    ▼
email_service.send_inquiry_email()
    │  SMTP → 寄送心願清單明細給負責人
    ▼
負責人收到詢價 email（含用戶 LINE ID + 收藏清單）
```

### 智慧查詢 RAG 流程

```
使用者輸入需求
    │
    ▼
user_demand_analysis()       ← Mistral 分析需求
    │
    ▼
chat_with_schedule_rag()     ← FAISS 語意檢索 + Mistral 生成在地活動建議
    │  (EmbeddingGemma-300m 向量化，k=8 最相關文件)
    ▼
travel_planner()             ← Mistral 整合需求與 RAG 結果，生成行程
    │
    ▼
critical_reviewer()          ← Mistral 審查行程合理性
    │
    ▼
travel_replanner()           ← Mistral 依審查意見修正
    │
    ▼
push_message() → 回傳給使用者（含「⭐ 收藏此行程」按鈕）
```

> 因流程耗時約 30 秒，採用 `reply()` 先回「規劃中」，背景 thread 完成後再 `push()` 推送結果。

---

## 資料夾結構

```
Penghu_linebot/
│
├── app.py                      # Flask 主程式，Webhook 入口，LIFF 路由，對話狀態機
├── .env                        # 環境變數（API Keys，不進版控）
├── requirements.txt            # Python 套件清單
│
├── handlers/                   # 對話流程控制器
│   ├── theme_browse.py         # 主題清單：行程 / 美食 / 交通主題 carousel
│   ├── popular_trip.py         # 熱門行程：類型選單 → 行程詳細卡片
│   ├── favorites.py            # 收藏清單：顯示 / 刪除 / 詳情 / 確認詢價
│   ├── smart_query.py          # 智慧查詢流程（呼叫 rag_service）
│   ├── transport_query.py      # 交通查詢：LIFF 航班入口 + 島內交通
│   └── room_query.py           # 空房查詢流程（待開發）
│
├── services/                   # 資料服務層（純函式，只負責取資料）
│   ├── airline_service.py      # 華信 + 立榮航空爬蟲（Selenium + ThreadPoolExecutor）
│   ├── email_service.py        # SMTP 寄信服務（詢價通知）
│   ├── tide_service.py         # 澎管處潮汐爬蟲
│   ├── weather_service.py      # 中央氣象署天氣 API
│   └── rag_service.py          # RAG 智慧查詢核心（FAISS + Mistral pipeline）
│
├── utils/
│   └── liff_token.py           # LIFF session token 機制（create / resolve）
│
├── templates/
│   └── liff_flight.html        # LIFF 航班查詢表單頁面
│
├── rag/                        # RAG 相關資料
│   ├── faiss_db/               # FAISS 向量資料庫（已包含於版控）
│   │   ├── index.faiss
│   │   └── index.pkl
│   ├── source_docs/
│   │   └── Panghu_schedule_database.md   # 澎湖行程活動資料庫
│   └── build_faiss.py          # 向量資料庫重建腳本
│
├── flex/                       # LINE Flex Message 模板
│   ├── theme_trip.py           # 行程主題 carousel（5 種旅遊風格）
│   ├── theme_food.py           # 美食主題 carousel（5 種美食類型）
│   ├── theme_transport.py      # 交通主題 carousel（5 種交通方式）
│   ├── flight_liff_btn.py      # LIFF 入口按鈕 bubble
│   ├── flight_result.py        # 航班查詢結果 carousel（含收藏按鈕）
│   ├── trip_card.py            # 熱門行程類型輪播卡片
│   ├── trip_detail.py          # 行程詳細卡片（含收藏 / 取消收藏按鈕）
│   ├── smart_result.py         # 智慧查詢結果（含收藏 AI 行程按鈕）
│   ├── transport_menu.py       # 交通查詢選單
│   └── room_menu.py            # 空房查詢選單
│
├── data/                       # 靜態 JSON 資料檔
│   ├── popular_trips.json      # 熱門行程資料
│   └── hotels.json             # 飯店基本資訊（待填入）
│
└── storage/                    # 使用者持久化資料（不進版控）
    ├── favorites/              # 每位使用者的收藏清單
    │   └── {user_id}.json
    └── itineraries/            # AI 智慧查詢行程文字
        ├── {user_id}_latest.txt
        └── itinerary_{user_id}_{timestamp}.txt
```

---

## 技術選型

| 類別 | 技術 |
|------|------|
| Web 框架 | Flask |
| LINE Bot SDK | line-bot-sdk v3 (Python) |
| LINE 前端 | LIFF（LINE Front-end Framework） |
| 語言模型 | Mistral (`ministral-8b-latest`) |
| Embedding 模型 | `google/embeddinggemma-300m`（HuggingFace） |
| 向量資料庫 | FAISS |
| RAG 框架 | LangChain Community |
| 天氣資料 | 中央氣象署開放資料平台 API |
| 航班資料 | 華信 + 立榮航空官網爬蟲（Selenium headless Chrome） |
| 驗證碼辨識 | ddddocr（立榮航空） |
| 潮汐資料 | 澎管處潮汐頁面爬蟲（requests + BeautifulSoup） |
| Email | Python smtplib（STARTTLS，支援 Gmail） |
| 本機測試 | ngrok（HTTPS tunnel） |

---

## 環境設定

`.env` 需設定以下變數：

```env
# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret

# LIFF
LIFF_ID=your_liff_id

# AI / RAG
MISTRAL_API_KEY=your_mistral_key
HUGGINGFACE_HUB_TOKEN=your_hf_token   # 用於載入 EmbeddingGemma-300m Embedding 模型

# 氣象局
OPENDATA_CWA_API_KEY=your_cwa_key

# Email 通知（心願清單詢價）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_gmail@gmail.com
SMTP_PASS=your_app_password       # Gmail 請使用「應用程式密碼」
NOTIFY_EMAIL=responsible@example.com
```

### Gmail 應用程式密碼取得方式

1. Google 帳戶 → **安全性** → 開啟**兩步驟驗證**
2. 安全性 → **應用程式密碼** → 選「郵件」→ 產生
3. 將 16 位數密碼填入 `SMTP_PASS`

---

## LIFF 設定（LINE Login Channel）

> LINE 目前**不再支援**在 Messaging API Channel 內直接建立 LIFF，
> 必須另外建立 **LINE Login Channel**，再於該 Channel 下新增 LIFF App。

### Step 1：建立 LINE Login Channel

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 選擇與 Bot 相同的 **Provider**
3. 點擊「**Create a new channel**」→ 選擇 **LINE Login**
4. 填入以下資訊：
   - Channel name：任意名稱（例如 `澎湖Bot LIFF`）
   - Channel description：任意
   - App types：勾選 **Web app**
5. 同意條款 → **Create**

### Step 2：建立 LIFF App

1. 進入剛建立的 LINE Login Channel
2. 點選上方「**LIFF**」分頁 → 「**Add**」
3. 填入：
   | 欄位 | 值 |
   |------|----|
   | LIFF app name | `航班查詢` |
   | Size | **Full** |
   | Endpoint URL | `https://你的網域/liff/flight`（本機測試填 ngrok URL） |
   | Scope | 勾選 `openid`、`profile` |
   | Bot link feature | **On (Aggressive)** → 選擇你的 Messaging API Channel |
4. 點擊「**Add**」→ 複製顯示的 **LIFF ID**（格式：`1234567890-xxxxxxxx`）

### Step 3：連結 Messaging API Channel

1. 進入 LINE Login Channel → 「**Basic settings**」分頁
2. 找到「**Linked Messaging API channel**」→ 點「**Link**」
3. 選擇你的 Messaging API Channel → 確認連結

### Step 4：填入環境變數

```env
LIFF_ID=1234567890-xxxxxxxx   # 貼上 Step 2 複製的 LIFF ID
```

### 本機測試（ngrok）

每次重啟 ngrok 網址會改變，需同步更新兩處：

1. **LINE Developers Console** → LINE Login Channel → LIFF → 編輯 Endpoint URL
2. **LINE Developers Console** → Messaging API Channel → Webhook URL

---

## 本機啟動

```bash
# 安裝套件
pip install -r requirements.txt

# 啟動 Flask
python app.py

# 另開終端，啟動 ngrok
./ngrok http 5000
```

將 ngrok 產生的 HTTPS URL 填入 LINE Developers Console 的 Webhook URL：
```
https://xxxx.ngrok-free.app/callback
```

LIFF Endpoint URL 設定為：
```
https://xxxx.ngrok-free.app/liff/flight
```

---

## 向量資料庫更新

`rag/faiss_db/` 已包含在版控中，一般情況下不需要重建。

**僅在 `rag/source_docs/Panghu_schedule_database.md` 有更新時**，才需要重新執行：

1. 登入 HuggingFace 並取得 `google/embeddinggemma-300m` 存取權限
2. 登入 HuggingFace CLI
   ```bash
   python -c "from huggingface_hub import login; login(token='你的token')"
   ```
3. 重建向量庫（約 10–20 分鐘）
   ```bash
   python rag/build_faiss.py
   ```
4. 將 `rag/faiss_db/` 重新 commit 進版控

---

## 各模組分工說明

### app.py — Webhook 入口 + LIFF 路由

- `user_states` dict 儲存每位使用者目前的對話步驟
- `MessageEvent` → `handle_message()` 依序呼叫各 handler（先到先處理）
- `PostbackEvent` → `transport_query_handler` 處理航班 postback；`favorites_handler` 處理收藏 postback
- `/liff/flight` → 注入 LIFF ID 與 session token 後渲染 HTML 表單
- `/api/flight-search` → 以 token 換回 user_id，背景執行爬蟲，完成後 push Flex carousel

### handlers/ — 流程控制

負責「問什麼問題、等什麼輸入、何時呼叫 service / flex」，不處理資料取得邏輯。

| 檔案 | 負責內容 |
|------|----------|
| `theme_browse.py` | 行程 / 美食 / 交通主題 carousel |
| `popular_trip.py` | 熱門行程展示與收藏 |
| `favorites.py` | 收藏清單 CRUD + 確認詢價寄信 |
| `smart_query.py` | 智慧查詢多輪對話 + AI 行程收藏 |
| `transport_query.py` | LIFF 航班入口 + 島內交通文字說明 |

### services/ — 資料服務

純函式，輸入參數回傳結果，不依賴對話狀態。

| 檔案 | 負責內容 |
|------|----------|
| `airline_service.py` | 華信 + 立榮航空 Selenium 爬蟲，ThreadPoolExecutor 並行查詢 |
| `email_service.py` | smtplib SMTP 寄信，格式化心願清單內容 |
| `rag_service.py` | 4 步驟 RAG pipeline（需求分析 → 檢索 → 規劃 → 審查修正） |
| `weather_service.py` | 氣象署 API 天氣查詢 |
| `tide_service.py` | 澎管處潮汐爬蟲 |

### utils/liff_token.py — Session Token 機制

避免 LIFF `userId` 與 Messaging API `userId` 不一致的問題（不同 Provider 下會拿到不同值）。

- `create(user_id, ttl_minutes=30)` → bot 側產生隨機 token 注入 LIFF URL
- `resolve(token)` → LIFF 提交時帶 token 換回正確 user_id，一次性使用後自動刪除
