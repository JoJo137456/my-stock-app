import streamlit as st
import twstock
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import time

# === 1. 系統設定 ===
st.set_page_config(page_title="遠東集團_戰情室", layout="wide")

# CSS 美化 (保持戰情室風格)
st.markdown("""
    <style>
        html, body, [class*="css"]  { font-family: 'Microsoft JhengHei', sans-serif !important; }
        .main-title {
            font-size: 3rem; font-weight: 700; color: #1d1d1f; text-align: center;
            margin-top: 2rem; margin-bottom: 2rem;
        }
        .metric-card {
            background: #ffffff; padding: 20px; border-radius: 15px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.05); text-align: center;
        }
        .stMetric { text-align: center; }
        .footer { text-align: center; color: #888; font-size: 0.8rem; margin-top: 5rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">遠東集團<br>聯合稽核總部 一處戰情室</div>', unsafe_allow_html=True)

# === 2. 核心情報函數 (改用 twstock) ===
def get_stock_data(code):
    try:
        # A. 獲取即時報價 (Realtime)
        # twstock 直接抓證交所，速度快且準
        real = twstock.realtime.get(code)
        
        if not real['success']:
            return None
            
        info = real['realtime']
        
        # 資料清洗：證交所給的都是字串，要轉成數字
        # 如果是 '-' 代表還沒成交 (例如剛開盤)，改抓最佳買入價
        def safe_float(val, fallback):
            try:
                return float(val)
            except:
                return fallback

        # 嘗試取得當前價格
        latest_price_str = info['latest_trade_price']
        best_bid_str = info['best_bid_price'][0]
        
        if latest_price_str != '-' and latest_price_str != '':
             current_price = float(latest_price_str)
        elif best_bid_str != '-' and best_bid_str != '':
             current_price = float(best_bid_str)
        else:
             # 如果真的什麼都抓不到，用昨收暫代
             current_price = 0.0

        open_price = safe_float(info['open'], current_price)
        high_price = safe_float(info['high'], current_price)
        low_price = safe_float(info['low'], current_price)
        
        # B. 抓取歷史資料 (用來算昨收和畫圖)
        stock = twstock.Stock(code)
        # 抓近 31 天歷史資料
        history = stock.fetch_31()
        
        # 取得昨收 (歷史資料的最後一筆)
        if len(history) > 0:
            prev_close = history[-1].close
            # 如果 current_price 還是 0 (例如盤前)，就用昨收
            if current_price == 0.0:
                current_price = prev_close
        else:
            prev_close = current_price # 防呆

        # C. 整理 K 線資料 (歷史日線)
        df = pd.DataFrame(history)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['date'])
            df.set_index('Date', inplace=True)
        
        return {
            "current": current_price,
            "prev_close": prev_close,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "df": df, # 這是日線資料
            "update_time": info['latest_trade_price'] # 最後成交時間
        }

    except Exception as e:
        print(f"Error: {e}")
        return None

# === 3. 繪圖模組 ===
def plot_chart(data):
    df = data['df']
    if df.empty:
        return None
        
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        increasing_line_color='#ef4444', increasing_fillcolor='#ef4444', # 台股紅漲
        decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e'  # 台股綠跌
    )])
    
    fig.update_layout(
        title="近 31 日走勢圖 (日線)",
        xaxis_rangeslider_visible=False,
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig

# === 4. 戰情室控制台 ===
# 股票清單 (左邊是顯示名稱，右邊是代碼)
stock_map = {
    "1402 遠東新": "1402", 
    "1102 亞泥": "1102", 
    "2606 裕民": "2606",
    "1460 宏遠": "1460", 
    "2903 遠百": "2903", 
    "4904 遠傳": "4904", 
    "1710 東聯": "1710"
}

with st.sidebar:
    st.header("🎯 監控目標")
    option = st.radio("選擇公司", list(stock_map.keys()))
    code = stock_map[option]
    
    st.markdown("---")
    if st.button("🔄 刷新情報"):
        st.cache_data.clear()
        st.rerun()
    st.caption("資料來源：台灣證券交易所 (Twstock)")

# === 5. 顯示數據 ===
data = get_stock_data(code)

if data:
    # 計算漲跌
    change = data['current'] - data['prev_close']
    # 防呆：如果昨收是 0，避免除以零錯誤
    if data['prev_close'] != 0:
        pct = (change / data['prev_close']) * 100
    else:
        pct = 0.0
    
    # 顏色邏輯 (Streamlit 原生支援)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("最新股價", f"{data['current']}", f"{change:.2f} ({pct:.2f}%)")
    with col2:
        st.metric("開盤 / 昨收", f"{data['open']} / {data['prev_close']}")
    with col3:
        st.metric("最高 / 最低", f"{data['high']} / {data['low']}")
    
    st.divider()
    
    # 畫圖
    st.plotly_chart(plot_chart(data), use_container_width=True)
    
else:
    st.error(f"⚠️ 無法連線至證交所 ({code})，請稍後再試。")
    st.info("提示：如果是盤中時間，資料應該會正常顯示；若是深夜維護時段可能會抓不到。")

# 頁腳
st.markdown('<div class="footer">遠東集團 聯合稽核總部 一處戰情室｜系統運作中 🟢</div>', unsafe_allow_html=True)
