import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time as dt_time
import pytz
import requests
import urllib3
import json

# === 0. 關鍵修復 A: SSL 憑證補丁 ===
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
original_request = requests.Session.request
def patched_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    return original_request(self, method, url, *args, **kwargs)
requests.Session.request = patched_request

# === 0. 關鍵修復 B: 手動抓取歷史資料 (繞過 twstock 的 Bug) ===
def fetch_twse_history_proxy(stock_code):
    try:
        # 建立證交所 API 網址 (抓取本月資料)
        month_str = datetime.now().strftime('%Y%m01')
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={month_str}&stockNo={stock_code}"
        
        # 直接請求 (已包含 SSL patch)
        r = requests.get(url)
        data = r.json()
        
        if data['stat'] != 'OK':
            return None
            
        # 手動清洗資料 (完全不理會 twstock 的 Data 結構)
        # 證交所格式: [日期, 成交股數, 成交金額, 開盤, 最高, 最低, 收盤, 漲跌, 筆數]
        # 我們自己解析，這樣就算它多欄位也不會報錯
        clean_data = []
        for row in data['data']:
            # 處理民國年: 112/01/01 -> 2023-01-01
            date_parts = row[0].split('/')
            ad_year = int(date_parts[0]) + 1911
            date_str = f"{ad_year}-{date_parts[1]}-{date_parts[2]}"
            
            # 處理數字 (移除逗號)
            def to_float(s):
                try:
                    return float(s.replace(',', ''))
                except:
                    return 0.0
            
            clean_data.append({
                'date': date_str,
                'open': to_float(row[3]),
                'high': to_float(row[4]),
                'low': to_float(row[5]),
                'close': to_float(row[6]),
            })
            
        return clean_data
    except Exception as e:
        st.write(f"Proxy fetch error: {e}")
        return None

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="遠東集團_戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') 

# CSS
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 3rem; font-weight: 700; color: #1d1d1f; text-align: center; margin: 2rem 0; }
        .footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 5rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 核心邏輯 ===
def check_market_status():
    now = datetime.now(tw_tz)
    current_time = now.time()
    market_open = dt_time(9, 0)
    market_close = dt_time(13, 35) 
    is_weekend = now.weekday() >= 5
    
    if is_weekend:
        return "closed", "🌙 休市 (週末)"
    elif market_open <= current_time <= market_close:
        return "open", "🟢 盤中 (即時連線)"
    else:
        return "closed", "🌙 盤後 (日結資料)"

# === 3. 資料獲取策略 (混合模式) ===
def get_stock_data(code, status):
    try:
        # --- A. 嘗試抓即時資料 (盤中優先) ---
        latest_price = 0.0
        realtime_success = False
        
        if status == "open":
            try:
                real = twstock.realtime.get(code)
                if real['success']:
                    info = real['realtime']
                    latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else 0.0
                    if latest == 0.0:
                        latest = float(info['open']) if info['open'] != '-' else 0.0
                    
                    if latest > 0:
                        latest_price = latest
                        realtime_success = True
                        
                    high = float(info['high']) if info['high'] != '-' else 0
                    low = float(info['low']) if info['low'] != '-' else 0
            except:
                pass

        # --- B. 抓歷史資料 (改用我們自己寫的 fetch_twse_history_proxy) ---
        # 這裡不再呼叫 stock.fetch_31()，避開那個 Bug
        hist_data = fetch_twse_history_proxy(code)
        
        if not hist_data:
            return {"error": "無法獲取歷史資料 (證交所連線失敗)"}
            
        # 整理數據
        df = pd.DataFrame(hist_data)
        today_data = hist_data[-1]
        yesterday_data = hist_data[-2] if len(hist_data) > 1 else today_data
        
        # 決定顯示價格
        if realtime_success:
            current = latest_price
            # 如果是盤中，今天的高低要用即時的
            disp_high = max(high, today_data['high'])
            disp_low = min(low if low > 0 else 99999, today_data['low'])
        else:
            current = today_data['close']
            disp_high = today_data['high']
            disp_low = today_data['low']
            
        prev_close = yesterday_data['close']
        
        return {
            "current": current,
            "prev_close": prev_close,
            "high": disp_high,
            "low": disp_low,
            "df": df,
            "source": "Realtime API" if realtime_success else "Historical DB (Proxy)",
            "error": None
        }

    except Exception as e:
        return {"error": str(e)}

# === 4. 繪圖 ===
def plot_chart(df):
    if df.empty: return None
    try:
        df['Date'] = pd.to_datetime(df['date'])
        df.set_index('Date', inplace=True)
        
        fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
            decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e'
        )])
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10), title="本月日線走勢")
        return fig
    except:
        return None

# === 5. UI ===
stock_map = {
    "1402 遠東新": "1402", "1102 亞泥": "1102", "2606 裕民": "2606",
    "1460 宏遠": "1460", "2903 遠百": "2903", "4904 遠傳": "4904", "1710 東聯": "1710"
}

with st.sidebar:
    st.header("🎯 監控目標")
    option = st.radio("選擇公司", list(stock_map.keys()))
    code = stock_map[option]
    
    st.divider()
    status_code, status_text = check_market_status()
    st.info(f"系統狀態：{status_text}")
        
    if st.button("🔄 強制刷新"):
        st.cache_data.clear()
        st.rerun()

data = get_stock_data(code, status_code)

if data and data.get("error"):
    st.error(f"❌ 發生錯誤: {data['error']}")
    st.caption("SSL 錯誤與資料格式錯誤已透過程式碼修復。")
    
elif data:
    curr = data['current']
    prev = data['prev_close']
    change = curr - prev
    pct = (change / prev) * 100 if prev != 0 else 0
    
    bg_color = "#e6fffa" if change >= 0 else "#fff5f5"
    font_color = "#d0021b" if change >= 0 else "#009944"
    
    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #eee;">
        <h2 style="margin:0; color:#555;">{option}</h2>
        <div style="display: flex; align-items: baseline; gap: 15px;">
            <span style="font-size: 3.5rem; font-weight: bold; color: #333;">{curr}</span>
            <span style="font-size: 1.5rem; font-weight: bold; color: {font_color};">
                {change:+.2f} ({pct:+.2f}%)
            </span>
        </div>
        <div style="margin-top: 10px; color: #666; font-size: 0.9rem;">
            資料來源: {data['source']} | 狀態: {status_text}
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("最高價", f"{data['high']}")
    c2.metric("最低價", f"{data['low']}")
    c3.metric("參考昨收", f"{prev}")
    
    if not data['df'].empty:
        st.plotly_chart(plot_chart(data['df']), use_container_width=True)
else:
    st.error("⚠️ 未知錯誤，請檢查網路連線。")

update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">更新時間：{update_time}</div>', unsafe_allow_html=True)
