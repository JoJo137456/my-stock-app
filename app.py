import streamlit as st
import yfinance as yf
import pandas as pd
import altair as alt
from datetime import datetime
import pytz

# === 1. 系統初始化 ===
st.set_page_config(page_title="遠東集團戰情中心", layout="wide")
tw_tz = pytz.timezone('Asia/Taipei')

# 強制 CSS：微軟正黑體 + 數字放大 + 移除圖表留白
st.markdown("""
    <style>
        html, body, [class*="css"] {
            font-family: 'Microsoft JhengHei', '微軟正黑體', sans-serif !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700;
        }
        /* 讓圖表更緊湊，移除圓角 */
        canvas {
            border-radius: 0px !important;
        }
        /* 調整一下大盤小圖的邊距 */
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

# === 3. 核心數據引擎 (雙軌制 + 日期嚴格比對) ===

@st.cache_data(ttl=10) # 10秒快取
def get_clean_data(symbol):
    try:
        stock = yf.Ticker(symbol)
        
        # 軌道一：抓「日線」 (5天) -> 找昨收、總量
        df_daily = stock.history(period="5d", interval="1d")
        
        # 軌道二：抓「分鐘線」 (1天) -> 畫圖、找現價
        df_minute = stock.history(period="1d", interval="1m")
        
        return df_daily, df_minute
    except:
        return pd.DataFrame(), pd.DataFrame()

def calculate_precise_metrics(df_daily, df_minute):
    """
    數據清洗與計算中心 (移除均價，修正昨收邏輯)
    """
    if df_minute.empty: return None

    # --- 1. 鎖定「今日」與「昨日」 ---
    # 取得分鐘線最後一筆的時間 (這是當下的時間)
    last_quote_time = df_minute.index[-1]
    today_date = last_quote_time.date()

    # --- 2. 抓取最準確的「昨收價」 (關鍵修正) ---
    # 邏輯：在日線資料中，篩選出所有「日期小於今天」的資料，取最後一筆
    # 這比 iloc[-2] 更安全，因為不會受到今天日線是否已經產生的影響
    past_data = df_daily[df_daily.index.date < today_date]
    
    if not past_data.empty:
        prev_close = past_data['Close'].iloc[-1]
    else:
        # 如果真的抓不到 (例如週一剛開盤)，用今日開盤價暫代
        prev_close = df_minute['Open'].iloc[0]

    # --- 3. 抓取「目前股價」 ---
    # 優先用分鐘線最後一筆，這比日線即時
    current_price = df_minute['Close'].iloc[-1]

    # --- 4. 漲跌計算 ---
    change = current_price - prev_close
    pct_change = (change / prev_close) * 100

    # --- 5. 成交量與金額 ---
    # 嘗試從日線抓今日成交量 (比較準)
    # 先看日線有沒有今天的資料
    today_daily_data = df_daily[df_daily.index.date == today_date]
    
    if not today_daily_data.empty:
        total_volume = today_daily_data['Volume'].iloc[-1]
    else:
        # 如果日線還沒更新，用分鐘線加總
        total_volume = df_minute['Volume'].sum()

    # 如果抓出來是 0 (盤中常見問題)，強制回退用分鐘線加總
    if total_volume == 0:
        total_volume = df_minute['Volume'].sum()

    # 成交金額估算 (Turnover) = 總量 * (分鐘線總額 / 分鐘線總量)
    vwap_num = (df_minute['Close'] * df_minute['Volume']).sum()
    vwap_den = df_minute['Volume'].sum()
    real_avg_price = vwap_num / vwap_den if vwap_den > 0 else current_price
    
    turnover_est = total_volume * real_avg_price

    return {
        "current": current_price,
        "prev_close": prev_close,
        "change": change,
        "pct_change": pct_change,
        "high": df_minute['High'].max(),
        "low": df_minute['Low'].min(),
        "open": df_minute['Open'].iloc[0],
        "volume": total_volume,
        "amount_e": turnover_est / 100000000, # 億
    }

def draw_combo_chart(df, color, prev_close):
    """
    個股走勢圖：價格(上) + 成交量(下)
    """
    df = df.reset_index()
    col_name = "Date" if "Date" in df.columns else "Datetime"
    df.rename(columns={col_name: "Time"}, inplace=True)

    # Y 軸動態範圍
    y_min = df['Close'].min()
    y_max = df['Close'].max()
    diff = y_max - y_min
    buffer = 0.05 if diff < 0.1 else diff * 0.1
    y_domain = [y_min - buffer, y_max + buffer]

    x_axis = alt.X('Time:T', axis=alt.Axis(title='', format='%H:%M', grid=False))

    # 上圖：價格
    area = alt.Chart(df).mark_area(color=color, opacity=0.1).encode(
        x=x_axis, y=alt.Y('Close:Q', scale=alt.Scale(domain=y_domain), axis=alt.Axis(title='股價', grid=True))
    )
    line = alt.Chart(df).mark_line(color=color, strokeWidth=2).encode(
        x=x_axis, y
