import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime, time
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# 強制 CSS：微軟正黑體 + 數字放大 + 去除圖表留白
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

# === 3. 核心數據引擎 ===

@st.cache_data(ttl=5)
def get_stock_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 1. 取得官方資訊 (info)
        info = stock.info if stock.info else {}
        
        # 2. 取得 Fast Info (轉字典)
        fi = stock.fast_info
        fast_info_dict = {
            'last_price': fi.last_price,
            'previous_close': fi.previous_close,
            'last_volume': fi.last_volume,
            'day_high': fi.day_high,
            'day_low': fi.day_low
        }
        
        # 3. 抓分鐘線 (畫圖用) - 不含盤後定價
        df_minute = stock.history(period="1d", interval="1m", auto_adjust=False)
        
        if not df_minute.empty:
            df_minute.index = df_minute.index.tz_convert(tw_tz)
            market_close_time = time(13, 35) 
            df_minute = df_minute[df_minute.index.time < market_close_time]

        return info, fast_info_dict, df_minute
    except Exception:
        return {}, {}, pd.DataFrame()

def calculate_metrics_official(info, fast_info, df_minute):
    """
    計算邏輯：優先抓取 Yahoo 官方欄位，不自行計算
    """
    if df_minute.empty: return None

    # === A. 昨收價 (Previous Close) ===
    prev_close = info.get('previousClose')
    if prev_close is None: prev_close = fast_info.get('previous_close')

    # === B. 目前股價 (Current Price) ===
    current_price = info.get('currentPrice')
    if current_price is None: current_price = fast_info.get('last_price')
    if current_price is None: current_price = df_minute['Close'].iloc[-1]

    # === C. 總成交量 (Volume) ===
    # 策略：優先找 regularMarketVolume (常規交易量)，這通常跟網頁顯示的一致
    # 如果沒有，才用 volume (總量)
    total_volume_shares = info.get('regularMarketVolume')
    if total_volume_shares is None:
        total_volume_shares = info.get('volume')
    
    # 防呆回退
    if total_volume_shares is None or total_volume_shares == 0:
        total_volume_shares = df_minute['Volume'].sum()

    # === D. 漲跌 ===
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100

    # === E. 成交金額 (估算) ===
    day_high = fast_info.get('day_high', df_minute['High'].max())
    day_low = fast_info.get('day_low', df_minute['Low'].min())
    if pd.isna(day_high): day_high = df_minute['High'].max()
    if pd.isna(day_low): day_low = df_minute['Low'].min()

    avg_p = (day_high + day_low + current_price) / 3
    turnover_est = total_volume_shares * avg_p

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change": change,
        "pct_change": pct_change,
        "high": day_high,
        "low": day_low,
        "open": info.get('open', df_minute['Open'].iloc[0]),
        "volume_shares": total_volume_shares,
        "amount_e": turnover_est / 100000000, 
    }

def draw_chart_combo(df, color, prev_close):
    """繪製圖表：價格(上) + 成交量(下)"""
    if df.empty: return None
    
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    # 強制放大波動
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    diff = y_max - y_min
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]
    
    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))
    
    # === 上圖：價格走勢 ===
    area = alt.Chart(df).mark_area(color=color, opacity=0.1).encode(
        x=x_axis, 
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價', grid=True))
    )
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=x_axis, 
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain)),
        tooltip=['Time', 'Close', 'Volume']
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[4, 4], color='gray', opacity=0.8
    ).encode(y='y')
    
    price_chart = (area + line + rule).properties(height=300)
    
    # === 下圖：成交量柱狀圖 (加深顏色，增加高度) ===
    # 這裡確保 Volume 是數值型態
    vol_chart = alt.Chart(df).mark_bar(color=color, opacity=1.0).encode( # opacity 改成 1.0 (不透明)
        x=alt.X('Time:T', axis=None), 
        y=alt.Y('Volume:Q', axis=alt.Axis(title='量', tickCount=3)),
        tooltip=['Time', 'Volume']
    ).properties(height=100) # 高度增加到 100
    
    # 垂直組合
    return alt.vconcat(price_chart, vol_chart, spacing=0).resolve_scale(x='shared')

def draw_mini_chart(df, color, prev_close):
    """大盤迷你圖"""
    if df.empty: return None
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)
    
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    y_domain = [y_min, y_max]

    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=alt.X('Time:T', axis=None),
        y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain, zero=False), axis=None),
        tooltip=['Time', 'Close']
    )
    rule = alt.Chart(pd.DataFrame({'y': [prev_close]})).mark_rule(
        strokeDash=[2, 2], color='gray', opacity=0.5
    ).encode(y='y')
    
    return (line + rule).properties(height=60)

# === 4. 側邊欄 ===
st.sidebar.header("🎯 監控標的選擇")
selected_name = st.sidebar.radio("請選擇公司：", list(stock_map.keys()))
ticker = stock_map[selected_name]
st.sidebar.markdown("---")
st.sidebar.caption(f"✅ 系統連線正常 | 開發者：李宗念")

# === 5. 戰情儀表板 ===
with st.container(border=True):
    col_head, col_idx_text, col_idx_chart = st.columns([2, 0.8, 1.2])
