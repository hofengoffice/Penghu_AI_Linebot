#%%
import time
import concurrent.futures
import cv2
import numpy as np
import ddddocr
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# 機場代碼對照表（華信航空用）
AIRPORTS = {
    "1": ("TSA", "松山"),
    "2": ("KHH", "高雄"),
    "3": ("RMQ", "台中"),
    "4": ("HUN", "花蓮"),
    "5": ("TTT", "台東"),
    "6": ("MZG", "澎湖"),
    "7": ("KNH", "金門"),
    "8": ("LZN", "南竿")
}

AIRPORTS_INV = {v[0]: v[1] for k, v in AIRPORTS.items()}

# 機場代碼 → 立榮航空城市名稱對照
CODE_TO_UNIAIR_NAME = {
    "TSA": "松山",
    "RMQ": "台中",
    "CYI": "嘉義",
    "TNN": "台南",
    "KHH": "高雄",
    "HUN": "花蓮",
    "TTT": "台東",
    "KNH": "金門",
    "MZG": "澎湖",
    "LZN": "南竿",
    "MFK": "北竿",
}


# ══════════════════════════════════════════════════════
# 華信航空（Mandarin Airlines）
# ══════════════════════════════════════════════════════

def get_flight_info(driver, direction_text):
    print(f"\n--- {direction_text} 航班資訊 ---")
    tickets = driver.find_elements(By.CLASS_NAME, "ticket-list")
    if not tickets:
        print("查無此區間航班資訊，或是該日期尚未開放訂位。")
        return []

    # 定義表格標頭與分隔線
    print(f"| {'航班':<10} | {'起飛時間':<12} | {'抵達時間':<12} | {'狀態':<8} |")
    print("|" + "-"*12 + "|" + "-"*14 + "|" + "-"*14 + "|" + "-"*10 + "|")

    available_flights = []
    for ticket in tickets:
        try:
            air_type = ticket.find_element(By.CLASS_NAME, "air-type").text
            flight_times = ticket.find_elements(By.CLASS_NAME, "flight-time")
            dep_time = flight_times[0].text.replace("\n", " ")
            arr_time = flight_times[1].text.replace("\n", " ")

            # 判斷是購票還是候補
            is_waitlist = False
            try:
                ticket.find_element(By.CLASS_NAME, "buybt01")
                is_waitlist = True
            except:
                pass

            status = "候補" if is_waitlist else "可購票"

            # 格式化表格列輸出
            # 由於終端機對中文字寬度處理不同，這裡使用較寬的間距確保對齊
            print(f"| {air_type:<10} | {dep_time:<12} | {arr_time:<12} | {status:<8} |")

            if not is_waitlist:
                available_flights.append({
                    "air_type": air_type,
                    "dep_time": dep_time,
                    "arr_time": arr_time
                })
        except:
            continue
    return available_flights


def run_search_mandarin(driver, wait, dep_code, arr_code, date_str, adult_count):
    driver.get("https://www.mandarin-airlines.com/")

    # 選擇單程模式進行查詢 (較為穩定)
    itin_type_label = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "label[for='itinType1']")))
    driver.execute_script("arguments[0].click();", itin_type_label)

    # 出發地
    Select(driver.find_element(By.ID, "depstn")).select_by_value(dep_code)
    time.sleep(1)
    # 目的地
    Select(driver.find_element(By.ID, "arrstn")).select_by_value(arr_code)
    # 日期
    dep_date_inputs = driver.find_elements(By.NAME, "departureDate")
    driver.execute_script(f"arguments[0].value = '{date_str}';", dep_date_inputs[0])
    # 成人
    Select(driver.find_element(By.NAME, "adult")).select_by_value(str(adult_count))
    # 搜尋
    search_btn = driver.find_element(By.XPATH, "//button[contains(text(), '搜 尋') and contains(@onclick, 'beforeSub')]")
    driver.execute_script("arguments[0].click();", search_btn)

    wait.until(lambda d: d.find_elements(By.CLASS_NAME, "ticket-list") or "目前無此航班資訊" in d.page_source)
    return get_flight_info(driver, f"{date_str} {AIRPORTS_INV.get(dep_code, dep_code)} -> {AIRPORTS_INV.get(arr_code, arr_code)}")


def search_mandarin_flights(dep_code, arr_code, date_str, passengers=1):
    """查詢華信航空單程航班，回傳含「航空公司」欄位的 list"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15)

    try:
        raw = run_search_mandarin(driver, wait, dep_code, arr_code, date_str, passengers)
    finally:
        driver.quit()

    return [
        {
            "航空公司": "華信航空",
            "航班": f["air_type"],
            "起飛": f["dep_time"],
            "抵達": f["arr_time"],
            "狀態": "✅ 有位"
        }
        for f in raw
    ]


# ══════════════════════════════════════════════════════
# 立榮航空（Uni Air）
# ══════════════════════════════════════════════════════

def _uniair_fill_form(driver, dep_name, arr_name, date_str, adult_count, infant_count=0):
    """填寫立榮訂位表單"""
    try:
        wait = WebDriverWait(driver, 20)

        driver.execute_script("document.getElementById('CPH_Body_rb_TripType_OW').click();")
        time.sleep(0.5)

        # 1. 地點選擇
        def select_location(select_id, city_name):
            el = wait.until(EC.presence_of_element_located((By.ID, select_id)))
            sel = Select(el)
            match = next((o.text for o in sel.options if city_name in o.text), None)
            if match:
                sel.select_by_visible_text(match)

        select_location("ddl_DEP", dep_name)
        select_location("ddl_ARR", arr_name)

        # 2. 格式化資料
        pax_str = f"{adult_count} 旅客 , {infant_count} 嬰兒"

        # 3. 強力同步 JS
        js_optimized = """
        function syncByMap(id, hiddenId, val) {
            var el = document.getElementById(id);
            var hiEl = document.getElementById(hiddenId);
            if (el) {
                el.removeAttribute('readonly');
                el.value = val;
                if (hiEl) hiEl.value = val;
                ['input', 'change', 'blur'].forEach(name => {
                    el.dispatchEvent(new Event(name, { bubbles: true }));
                });
            }
        }
        // 同步日期
        syncByMap('CPH_Body_tb_TRIP_DATE', 'CPH_Body_hi_TRIP_DATE', arguments[0]);
        // 同步人數 (包含成人與嬰兒)
        syncByMap('CPH_Body_tb_PaxNum', 'CPH_Body_hi_PaxNum', arguments[1]);
        syncByMap('CPH_Body_tb_PaxNumAdult', 'CPH_Body_tb_PaxNumAdult', arguments[2]);
        syncByMap('CPH_Body_tb_PaxNumInf', 'CPH_Body_hi_PaxNumInf', arguments[3]);

        // 點擊完成
        var doneBtn = document.querySelector('.done-select');
        if (doneBtn) doneBtn.click();
        """
        driver.execute_script(js_optimized, date_str, pax_str,
                              str(adult_count), str(infant_count))

        time.sleep(2)
        print("🖱️ 提交表單，準備進入航班頁面...")
        driver.execute_script("document.getElementById('CPH_Body_btn_SelectFlight').click();")

        return True
    except Exception as e:
        print(f"❌ 填表失敗: {e}")
        return False


def _uniair_solve_captcha(driver, max_retries=3):
    """
    1. 定位驗證碼圖片並截圖
    2. 使用 OpenCV 放大 2 倍提高 AI 辨識率
    3. 辨識並填入，最後點擊搜尋
    4. 若驗證碼錯誤（頁面未跳轉），自動刷新驗證碼重試，最多 max_retries 次
    """
    wait = WebDriverWait(driver, 15)
    ocr = ddddocr.DdddOcr(show_ad=False)

    target_xpath = "/html/body/form/div[2]/div[2]/div/div[2]/div[2]/div[4]/div/div/div/div[1]/img"
    btn_xpath    = "/html/body/form/div[2]/div[2]/div/div[2]/div[3]/div/div/a"
    refresh_xpath = "//a[contains(@id,'RefreshCode') or contains(@onclick,'RefreshCode') or contains(@class,'refresh')]"

    for attempt in range(1, max_retries + 1):
        print(f"🕵️ 正在定位驗證碼圖片... (第 {attempt}/{max_retries} 次)")
        try:
            # 1. 截圖驗證碼
            captcha_el = wait.until(EC.visibility_of_element_located((By.XPATH, target_xpath)))
            img_bytes  = captcha_el.screenshot_as_png

            # 2. 影像處理：放大 2 倍
            nparr      = np.frombuffer(img_bytes, np.uint8)
            img        = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            img_resized = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # 3. AI 辨識
            pil_img = Image.fromarray(cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB))
            code    = ocr.classification(pil_img).strip().upper()
            print(f"🤖 AI 辨識結果：{code}")

            # 4. 填入驗證碼
            input_box = driver.find_element(By.CSS_SELECTOR, "input[id*='CaptchaCode']")
            input_box.clear()
            input_box.send_keys(code)

            # 5. 點擊搜尋按鈕
            print("🖱️ 正在點擊搜尋按鈕，前往航班頁面...")
            try:
                submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, btn_xpath)))
                driver.execute_script("arguments[0].click();", submit_btn)
            except:
                backup_btn = driver.find_element(By.ID, "CPH_Body_btn_SelectFlight")
                driver.execute_script("arguments[0].click();", backup_btn)
            print("🚀 搜尋按鈕已觸發！")

            # 6. 等待跳轉
            print("⏳ 等待網頁跳轉中...")
            time.sleep(6)

            current_url = driver.current_url.lower()
            if "select" in current_url and ".aspx" in current_url:
                print("✨ 網址已跳轉，準備擷取資料！")
                return True

            print(f"⚠️ 驗證碼錯誤或未跳轉，目前網址: {driver.current_url}")

            # 7. 刷新驗證碼，準備重試
            if attempt < max_retries:
                try:
                    refresh_btn = driver.find_element(By.XPATH, refresh_xpath)
                    driver.execute_script("arguments[0].click();", refresh_btn)
                    print("🔄 已刷新驗證碼，準備重試...")
                    time.sleep(1)
                except:
                    # 找不到刷新按鈕，直接清空輸入框等頁面自動刷新
                    print("🔄 找不到刷新按鈕，等待頁面重置...")
                    time.sleep(2)

        except Exception as e:
            print(f"❌ 第 {attempt} 次執行出錯：{e}")
            if attempt == max_retries:
                driver.save_screenshot('error_captcha_locator.png')

    print("❌ 驗證碼重試次數已達上限，放棄查詢")
    return False


def _uniair_capture_flights(driver, label="去程"):
    """擷取立榮航班清單並回傳資料"""
    captured_data = []
    try:
        wait = WebDriverWait(driver, 25)
        print(f"📡 [偵測] 正在掃描 {label} 航班內容...")

        # 1. HTML 顯示大盒子 ID 包含 pnl_Item
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "span[id*='pnl_Item']")))

        # 2. 關鍵修正：直接抓取帶有 pnl_Item 的大盒子清單
        flight_items = driver.find_elements(By.CSS_SELECTOR, "span[id*='pnl_Item']")

        print(f"💡 [偵測] 成功！在網頁發現了 {len(flight_items)} 個航班區塊")

        for item in flight_items:
            try:
                # 使用 innerText 確保抓到顯示的文字，並過濾掉隱藏標籤
                # 每個欄位都使用「ID 包含」的方式在「目前這個 item」裡面找
                f_no = item.find_element(By.CSS_SELECTOR, "span[id*='lb_FlightNumber']").get_attribute("innerText").strip()
                dep_tm = item.find_element(By.CSS_SELECTOR, "span[id*='lb_DepTime']").get_attribute("innerText").strip()
                arr_tm = item.find_element(By.CSS_SELECTOR, "span[id*='lb_ArrTime']").get_attribute("innerText").strip()

                # 抓取按鈕判斷狀態
                btn = item.find_element(By.CSS_SELECTOR, "a[id*='btn_SelectFlight']")
                btn_class = btn.get_attribute("class")

                # 狀態判斷：如果按鈕或大盒子包含 -disabled
                if "-disabled" in btn_class or "-disabled" in item.get_attribute("class"):
                    try:
                        # 嘗試抓取「無可售機位」文字
                        status = item.find_element(By.CSS_SELECTOR, "span[id*='lb_SubInfo']").get_attribute("innerText").strip()
                    except:
                        status = "❌ 售完"
                else:
                    status = "✅ 有位"

                if f_no:
                    captured_data.append({
                        "行程": label,
                        "班次": f_no,
                        "時間": f"{dep_tm} ➔ {arr_tm}",
                        "狀態": status
                    })
                    print(f"   📦 [裝箱成功] {f_no} | {status}")
            except Exception:
                # 某一班抓失敗不影響整組，繼續下一班
                continue

    except Exception as e:
        print(f"⚠️ {label} 擷取失敗：{e}")
        driver.save_screenshot(f"debug_{label}_error.png")

    return captured_data


def search_uniair_flights(dep_code, arr_code, date_str, passengers=1, infants=0):
    """
    查詢立榮航空單程航班，回傳含「航空公司」欄位的 list。

    參數：
        dep_code  : 出發機場代碼（如 "TSA"）
        arr_code  : 抵達機場代碼（如 "MZG"）
        date_str  : 出發日期（格式 "YYYY/MM/DD"）
        passengers: 成人（旅客）人數（預設 1）
        infants   : 嬰兒人數（預設 0）
    """
    dep_name = CODE_TO_UNIAIR_NAME.get(dep_code, dep_code)
    arr_name = CODE_TO_UNIAIR_NAME.get(arr_code, arr_code)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        driver.get("https://www.uniair.com.tw/rwd/B2C/booking/ubk_search.aspx")
        if not _uniair_fill_form(driver, dep_name, arr_name, date_str, passengers, infants):
            return []
        if not _uniair_solve_captcha(driver):
            return []
        raw = _uniair_capture_flights(driver, "去程")
    finally:
        driver.quit()

    return [
        {
            "航空公司": "立榮航空",
            "航班": f["班次"],
            "起飛": f["時間"].split(" ➔ ")[0],
            "抵達": f["時間"].split(" ➔ ")[1] if " ➔ " in f["時間"] else "",
            "狀態": f["狀態"]
        }
        for f in raw
    ]


# ══════════════════════════════════════════════════════
# 統一查詢入口（同時查兩家航空）
# ══════════════════════════════════════════════════════

def search_flights(dep_code, arr_code, date_str, passengers=1, infants=0):
    """
    同時查詢華信航空與立榮航空，合併回傳含「航空公司」欄位的 list。

    參數：
        dep_code  : 出發機場代碼（如 "TSA"）
        arr_code  : 抵達機場代碼（如 "MZG"）
        date_str  : 出發日期（格式 "YYYY/MM/DD"）
        passengers: 旅客（2歲以上）人數（預設 1）
        infants   : 嬰兒（未滿2歲）人數（預設 0）

    回傳：
        list[dict]，每筆格式：
        {"航空公司": ..., "航班": ..., "起飛": ..., "抵達": ..., "狀態": ...}
    """
    results = []

    def _mandarin():
        try:
            return search_mandarin_flights(dep_code, arr_code, date_str, passengers)
        except Exception as e:
            print(f"[華信] 查詢失敗: {e}")
            return []

    def _uniair():
        try:
            return search_uniair_flights(dep_code, arr_code, date_str, passengers, infants)
        except Exception as e:
            print(f"[立榮] 查詢失敗: {e}")
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_mandarin = executor.submit(_mandarin)
        future_uniair   = executor.submit(_uniair)
        results.extend(future_mandarin.result())
        results.extend(future_uniair.result())

    return results


def format_result(dep_name, arr_name, date, flights, passengers):
    """將航班 list 格式化為 LINE 訊息文字，分組顯示華信與立榮"""
    lines = [
        f"✈️ {dep_name} → {arr_name}",
        f"📅 {date}　👤 {passengers} 人",
        "─" * 20
    ]

    mandarin_flights = [f for f in flights if f.get("航空公司") == "華信航空"]
    uniair_flights   = [f for f in flights if f.get("航空公司") == "立榮航空"]

    # 華信航空區塊
    lines.append("🟡 華信航空")
    if not mandarin_flights:
        lines.append("   查無可購票航班")
    for f in mandarin_flights:
        lines.append(f"   🛫 {f['航班']}　{f['起飛']} → {f['抵達']}")
        lines.append(f"      {f['狀態']}")

    lines.append("─" * 20)

    # 立榮航空區塊
    lines.append("🔵 立榮航空")
    if not uniair_flights:
        lines.append("   查無可購票航班")
    for f in uniair_flights:
        lines.append(f"   🛫 {f['航班']}　{f['起飛']} → {f['抵達']}")
        lines.append(f"      {f['狀態']}")

    return "\n".join(lines)


def main():
    print("=== 華信 + 立榮航空自動查詢系統 ===")

    # 選單顯示
    for k, v in AIRPORTS.items():
        print(f"{k}. {v[1]} ({v[0]})")

    dep_idx = input("\n請選擇出發地序號: ")
    arr_idx = input("請選擇目的地序號: ")

    dep_code = AIRPORTS.get(dep_idx, ("TSA", ""))[0]
    arr_code = AIRPORTS.get(arr_idx, ("MZG", ""))[0]

    dep_date    = input("請輸入去程日期 (格式: YYYY/MM/DD, 例如 2026/05/01): ")
    adult_count = int(input("請輸入旅客人數 (1-5): ") or 1)
    infant_count = int(input("請輸入嬰兒人數 (0-3): ") or 0)

    print("\n系統準備中，請稍候...")

    flights = search_flights(dep_code, arr_code, dep_date, adult_count, infant_count)
    dep_name = AIRPORTS_INV.get(dep_code, dep_code)
    arr_name = AIRPORTS_INV.get(arr_code, arr_code)
    print(format_result(dep_name, arr_name, dep_date, flights, adult_count))


if __name__ == "__main__":
    main()
