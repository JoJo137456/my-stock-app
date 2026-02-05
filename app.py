import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, time as dt_time
import pytz

# === 1. 戰情室初始化 ===
st.set_page_config(page_title="遠東集團_戰情室", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei') # 設定台灣時區

# CSS 美化
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', sans-serif !important; }
        .main-title { font-size: 3rem; font-weight: 700; color: #1d1d1f; text-align: center; margin: 2rem 0; }
        .footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 5rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 核心邏輯：判斷盤中/盤後 ===
def check_market_status():
    now = datetime.now(tw_tz)
    current_time = now.time()
    
    # 定義開盤時間 (09:00 ~ 13:30)
    market_open = dt_time(9, 0)
    market_close = dt_time(13, 35) 
    
    is_weekend = now.weekday() >= 5 # 5=週六, 6=週日
    
    if is_weekend:
        return "closed", "🌙 休市 (週末)"
    elif market_open <= current_time <= market_close:
        return "open", "🟢 盤中 (即時連線)"
    else:
        return "closed", "🌙 盤後 (日結資料)"

# === 3. 資料獲取策略 (含錯誤追蹤) ===
def get_stock_data(code, status):
    try:
        stock = twstock.Stock(code)
        
        # --- 策略 A: 盤中模式 (抓 Realtime) ---
        if status == "open":
            real = twstock.realtime.get(code)
            if real['success']:
                info = real['realtime']
                
                latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else 0.0
                if latest == 0.0:
                    latest = float(info['open']) if info['open'] != '-' else 0.0
                
                # 嘗試抓歷史資料 (若失敗則忽略)
                try:
                    hist = stock.fetch_31()
                    prev_close = hist[-1].close if hist else latest
                    df = pd.DataFrame(hist)
                except Exception as e:
                    # 如果盤中抓不到歷史，就只顯示當前價格，不讓程式崩潰
                    prev_close = latest
                    df = pd.DataFrame()
                
                return {
                    "current": latest,
                    "prev_close": prev_close,
                    "high": float(info['high']) if info['high'] != '-' else 0,
                    "low": float(info['low']) if info['low'] != '-' else 0,
                    "df": df,
                    "source": "Realtime API",
                    "error": None
                }

        # --- 策略 B: 盤後/休市模式 (抓 fetch_31 歷史數據) ---
        hist = stock.fetch_31() # 這一步如果沒有 lxml 會直接報錯
        
        if not hist:
            return {"error": "無法獲取歷史資料 (可能是證交所連線問題)"}
            
        today_data = hist[-1]      
        yesterday_data = hist[-2] if len(hist) > 1 else today_data
        
        return {
            "current": today_data.close,
            "prev_close": yesterday_data.close,
            "high": today_data.high,
            "low": today_data.low,
            "df": pd.DataFrame(hist),
            "source": "Historical DB",
            "error": None
        }

    except Exception as e:
        # 捕捉所有錯誤並回傳，顯示在畫面上
        return {"error": str(e)}

# === 4. 繪圖模組 ===
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
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=30, b=10), title="近月日線走勢")
        return fig
    except:
        return None

# === 5. 主控台 ===
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
    
    if status_code == "open":
        st.success(f"系統狀態：{status_text}")
    else:
        st.info(f"系統狀態：{status_text}")
        
    if st.button("🔄 強制刷新"):
        st.cache_data.clear()
        st.rerun()

# === 6. 數據展示區 ===
data = get_stock_data(code, status_code)

# 檢查是否有錯誤回傳
if data and data.get("error"):
    st.error(f"❌ 發生錯誤: {data['error']}")
    st.warning("建議檢查：GitHub 的 requirements.txt 是否已加入 'lxml'？")
    
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

# 頁腳
update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">更新時間：{update_time}</div>', unsafe_allow_html=True)
