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
        .status-badge { padding: 5px 10px; border-radius: 5px; font-weight: bold; font-size: 0.9rem; }
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
    market_close = dt_time(13, 35) # 多給5分鐘緩衝
    
    is_weekend = now.weekday() >= 5 # 5=週六, 6=週日
    
    if is_weekend:
        return "closed", "🌙 休市 (週末)"
    elif market_open <= current_time <= market_close:
        return "open", "🟢 盤中 (即時連線)"
    else:
        return "closed", "🌙 盤後 (日結資料)"

# === 3. 資料獲取策略 ===
def get_stock_data(code, status):
    try:
        stock = twstock.Stock(code)
        
        # --- 策略 A: 盤中模式 (抓 Realtime) ---
        if status == "open":
            real = twstock.realtime.get(code)
            if real['success']:
                info = real['realtime']
                
                # 價格清洗
                latest = float(info['latest_trade_price']) if info['latest_trade_price'] != '-' else 0.0
                # 如果剛開盤還沒成交價，抓開盤價或昨收
                if latest == 0.0:
                    latest = float(info['open']) if info['open'] != '-' else 0.0
                
                # 為了算漲跌，我們還是需要昨收價 (從歷史抓最準)
                hist = stock.fetch_31()
                prev_close = hist[-1].close if hist else latest
                
                return {
                    "current": latest,
                    "prev_close": prev_close,
                    "high": float(info['high']) if info['high'] != '-' else 0,
                    "low": float(info['low']) if info['low'] != '-' else 0,
                    "df": pd.DataFrame(hist), # 用歷史資料畫K線
                    "source": "Realtime API"
                }

        # --- 策略 B: 盤後/休市模式 (抓 fetch_31 歷史數據) ---
        # 這會穩定非常多，因為它讀取的是靜態資料庫，不會被鎖 IP
        hist = stock.fetch_31()
        
        if not hist:
            return None
            
        today_data = hist[-1]      # 最新一筆 (今天或週五)
        yesterday_data = hist[-2]  # 前一筆 (昨天或週四)
        
        return {
            "current": today_data.close,
            "prev_close": yesterday_data.close, # 用前一天的收盤當作基準
            "high": today_data.high,
            "low": today_data.low,
            "df": pd.DataFrame(hist),
            "source": "Historical DB"
        }

    except Exception as e:
        print(f"Error: {e}")
        return None

# === 4. 繪圖模組 ===
def plot_chart(df):
    if df.empty: return None
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
    
    # 狀態顯示燈
    if status_code == "open":
        st.success(f"系統狀態：{status_text}")
    else:
        st.info(f"系統狀態：{status_text}")
        
    if st.button("🔄 強制刷新"):
        st.cache_data.clear()
        st.rerun()

# === 6. 數據展示區 ===
data = get_stock_data(code, status_code)

if data:
    curr = data['current']
    prev = data['prev_close']
    change = curr - prev
    pct = (change / prev) * 100 if prev != 0 else 0
    
    # 根據狀態顯示不同顏色的卡片
    bg_color = "#e6fffa" if change >= 0 else "#fff5f5"
    
    st.markdown(f"""
    <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 1px solid #eee;">
        <h2 style="margin:0; color:#555;">{option}</h2>
        <div style="display: flex; align-items: baseline; gap: 15px;">
            <span style="font-size: 3.5rem; font-weight: bold; color: #333;">{curr}</span>
            <span style="font-size: 1.5rem; font-weight: bold; color: {'#d0021b' if change >= 0 else '#009944'};">
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
    
    st.plotly_chart(plot_chart(data['df']), use_container_width=True)

else:
    # 錯誤處理
    st.error(f"⚠️ 無法取得數據 ({code})")
    if status_code == "open":
        st.warning("盤中連線不穩定，請稍後刷新。")
    else:
        st.info("檢查 requirements.txt 是否包含 lxml，或是證交所網站維護中。")

# 頁腳
update_time = datetime.now(tw_tz).strftime('%Y-%m-%d %H:%M:%S')
st.markdown(f'<div class="footer">更新時間：{update_time}</div>', unsafe_allow_html=True)
