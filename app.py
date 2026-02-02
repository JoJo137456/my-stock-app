import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# 強制 CSS
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700;
        }
        canvas {
            border-radius: 0px !important;
        }
        div[data-testid="stAltairChart"] {
            margin-top: -10px;
        }
    </style>
""", unsafe_allow_html=True)

# === 2. 監控清單 ===
stock_map = {
    "1402 遠東新": "1402.TW",
    "1102 亞泥": "1102.TW",
    "2606 裕民": "2606.TW",
    "1460 宏遠": "1460.TW",
    "2903 遠百": "2903.TW",
    "4904 遠傳": "4904.TW",
    "1710 東聯": "1710.TW"
}

# === 3. 核心數據引擎 (嚴格過濾盤後) ===

@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 1. 抓日線 (5天)：設定 auto_adjust=False 以確保拿到「原始價格」(跟 Yahoo 網頁一致)
        df_daily = stock.history(period="5d", interval="1d", auto_adjust=False)
        
        # 2. 抓分鐘線 (1天)：設定 auto_adjust=False
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        
        # === 關鍵修正：時區轉換與盤後過濾 ===
        if not df_minute.empty:
            # 轉成台北時間
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            
            # 過濾：只保留 13:30 (含) 以前的數據
            # 這樣可以剔除 14:00 後的盤後定價交易，確保成交量跟 Yahoo 網頁一致
            market_close_time = time(13, 31) # 設定 13:31 是為了包含 13:30 整的那一筆
            df_minute = df_minute[df_minute.index.time < market_close_time]
            
        return df_daily, df_minute
    except:
        return pd.DataFrame(), pd.DataFrame()

def calculate_metrics_strict(df_daily, df_minute):
    """
    計算邏輯：完全依賴「過濾後的盤中數據」
    """
    if df_minute.empty: return None
    
    # === A. 鎖定「昨收價」 ===
    # 從日線抓，因為日線包含完整的歷史
    # 邏輯：找日期「嚴格小於」今天日期的最後一筆
    today_date = df_minute.index[-1].date()
    past_daily = df_daily[df_daily.index.date < today_date]
    
    if not past_daily.empty:
        prev_close = past_daily['Close'].iloc[-1]
    else:
        prev_close = df_minute['Open'].iloc[0] # 防呆

    # === B. 鎖定「目前股價」 ===
    # 拿過濾後分鐘線的最後一筆 (這就是 13:30 收盤價，不含盤後)
    current_price = df_minute['Close'].iloc[-1]
    
    # === C. 鎖定「成交量」 (Yahoo 網頁顯示的量) ===
    # 直接加總過濾後的分鐘線成交量
    # 這樣就排除了盤後定價的量
    total_volume = df_minute['Volume'].sum()
    
    # === D. 估算「成交金額」 (不含盤後) ===
    # 累加 (每分鐘收盤價 * 每分鐘成交量)
    turnover_est = (df_minute['Close'] * df_minute['Volume']).sum()

    # === E. 漲跌 ===
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change": change,
        "pct_change": pct_change,
        "high": df_minute['High'].max(),
        "low": df_minute['Low'].min(),
        "open": df_minute['Open'].iloc[0],
        "volume": total_volume,
        "amount_e": turnover_est / 100000000, # 換算億
    }

def draw_chart_combo(df, color, prev_close):
    """繪製圖表：價格 + 成交量"""
    if df.empty: return None
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    # Y 軸動態範圍 (強制放大波動)
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    diff = y_max - y_min
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]
    
    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))
    
    # 價格圖
    area = alt.Chart(df).mark_area(color=
